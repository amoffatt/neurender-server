import sys, os
import traceback
import pydantic
import asyncio
from pydantic_yaml import parse_yaml_raw_as
from pathlib import Path
from typing import List, Optional

from .pipeline import PipelineStep, ImportImageBatch
from .utils import path_str, unique_subpath
from .utils.pydantic import pydantic_subclassof
from . import config

PIPELINE_FILE_SUFFIX = '.nrp'

PIPELINES_PATH = "pipelines"


# print("Type value of ImageBatch step:", ImportImageBatch.__type)

class NeurenderProject:
    @staticmethod
    async def load(src_url:str):
        if src_url.startswith('s3://'):
            projects_dir = Path('.')
            project_path = projects_dir / src_url[5:]

            await storage.copy_s3(src_url, project_path)

            return NeurenderProject(project_path, src_url)
        else:
            return NeurenderProject(src_url)
        

        
    def __init__(self, path:str, url:str=None):
        self.url = url
        self.path = Path(path).expanduser()
        self.pipelines_path = self.path / PIPELINES_PATH

    def get_pipeline_paths(self):
        return [p for p in self.pipelines_path.iterdir() if p.suffix.lower() == PIPELINE_FILE_SUFFIX]

    def get_pipeline(self, name):
        for path in self.get_pipeline_paths():
            # If name is not specified, return the first available pipeline
            if not name or path.name == Path(name).name:
                return self._get_pipeline_by_path(path)

        return None


    def _get_pipeline_by_path(self, path):
        pipeline = NeurenderPipeline.load_from_yaml(path)
        pipeline.path = path
        pipeline.project_path = self.path
        return pipeline
        

class NeurenderPipeline(pydantic.BaseModel):
    @staticmethod
    def load_from_yaml(path):

        with open(str(path), 'r') as f:
            contents = f.read()

        pipeline = parse_yaml_raw_as(NeurenderPipeline, contents)
        return pipeline
    
    name:str
    pipeline:List[pydantic_subclassof(PipelineStep, "step")]
    
    path:Path = None
    project_path:Path = None

    def run(self, working_path=''):
        print(f"Running Neurender pipeline '{self.name}' ({path_str(self.path)})")

        if not working_path:
            working_path = unique_subpath(self.project_path / 'output')
        else:
            working_path = Path(working_path)

        working_path.mkdir(parents=True, exist_ok=True)

        print("  => Processing outputs in:", path_str(working_path))


        for step in self.pipeline:
            print("  =>", step)
            try:
                step.run(self.project_path, working_path)
            except Exception as e:
                print("Pipeline error:", file=sys.stderr)
                traceback.print_exception(e)
                print("Exiting...")
                break

        print("Done.")

