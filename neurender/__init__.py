import sys, os
import traceback
import pydantic
import asyncio
from pathlib import Path
from typing import List

from .pipeline import PipelineStep, RunContext
from .utils import path_str, unique_subpath
from .utils.pydantic import pydantic_subclassof, read_yaml_file
from . import storage

PIPELINE_FILE_SUFFIX = '.nrp'

PIPELINES_PATH = "pipelines"

DEFAULT_PIPELINE = "default"



class NeurenderPipeline(pydantic.BaseModel):
    @staticmethod
    def load(path:Path):
        pipeline = read_yaml_file(NeurenderPipeline, path)
        pipeline.path = path
        return pipeline
    
    pipeline:List[pydantic_subclassof(PipelineStep, "step")]

    # List of paths within the upload folder to upload. Supports glob syntax
    upload_artifacts:List[str]
    
    name:str
    path:Path = None
    project_path:Path = None

    @property
    def default_output_subpath(self):
        return Path('output') / self.path.stem  # Pipeline name without extension

    def run(self, working_path='', no_skip_steps=[]):
        print(f"Running Neurender pipeline '{self.name}' ({path_str(self.path)})")

        if not working_path:
            working_path = self.project_path / self.default_output_subpath
        else:
            working_path = Path(working_path)

        working_path.mkdir(parents=True, exist_ok=True)

        print("  => Processing outputs in:", path_str(working_path))

        context = RunContext(self.project_path, working_path, no_skip_steps=no_skip_steps)

        for step in self.pipeline:
            print("  =>", step)
            try:
                step.run(context)
            except Exception as e:
                print("Pipeline error:", file=sys.stderr)
                traceback.print_exception(e)
                print("Exiting...")
                break

        print("Done.")
        return working_path

    def upload_output_artifacts(self, working_path:Path, project_url:str):
        if not self.upload_artifacts:
            print("No artifacts to upload")
            return

        s3 = storage.S3()

        # Note: Using os.path.join() because (Path(project_url) / subpath) will mangle the URL
        dst_url = os.path.join(project_url, self.default_output_subpath)

        for artifact in self.upload_artifacts:
            print(f"Checking upload path for artifacts: {working_path}/{artifact}")
            s3.sync_to_remote(working_path, dst_url, select=artifact)

        

class NeurenderProject:
    @staticmethod
    def load(src_url:str, local_path:str='', select='') -> "NeurenderProject":
        if src_url.startswith('s3://'):

            # If local_path is not specified, save the project to a local folder based on the last
            # element of the projects path url (same as git's behavior)
            project_path = local_path if local_path else Path(src_url).name
            project_path = Path(project_path).absolute()


            print(f"Downloading project {src_url} => {project_path} (select: {select or storage.SELECT_ALL_FILES})")
            storage.S3().sync_to_local(src_url, project_path, select=select)

            return NeurenderProject(project_path, src_url)
        else:
            return NeurenderProject(src_url)
        

        
    def __init__(self, path:str, url:str=None):
        self.url = url
        self.path = Path(path).expanduser()
        self.pipelines_path = self.path / PIPELINES_PATH

    def get_pipeline_paths(self):
        return [p for p in self.pipelines_path.iterdir() if p.suffix.lower() == PIPELINE_FILE_SUFFIX]


    def get_pipeline(self, name:str) -> NeurenderPipeline:
        for path in self.get_pipeline_paths():
            # If name is not specified, return the first available pipeline
            filename = path.stem
            if filename == name or filename == DEFAULT_PIPELINE:
                return self._get_pipeline_by_path(path)

        return None


    def _get_pipeline_by_path(self, path:Path) -> NeurenderPipeline:
        pipeline = NeurenderPipeline.load(path)
        pipeline.path = path
        pipeline.project_path = self.path
        return pipeline
        

