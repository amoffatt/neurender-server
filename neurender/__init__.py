import pydantic
from pydantic_yaml import parse_yaml_raw_as
from pathlib import Path
from typing import List, Optional

from .pipeline import PipelineStep, ImportImageBatch
from .utils import path_str
from .utils.pydantic import pydantic_subclassof

PROJECT_FILE_SUFFIX = '.nrp'


# print("Type value of ImageBatch step:", ImportImageBatch.__type)

class NeurenderPipelineConfig(pydantic.BaseModel):
    name:str
    pipeline:List[pydantic_subclassof(PipelineStep, "step")]
    
    path:Path = None

    def run_pipeline(self):
        print(f"Running Neurender pipeline '{self.name}'")
        for step in self.pipeline:
            print("  =>", step)
            try:
                step.run(self.path)
            except Exception as e:
                print("Pipeline error:", e)
                print("Exiting...")
                break

        print("Done.")


def load_from_yaml(project_path):
    project_path = Path(project_path).expanduser().with_suffix(PROJECT_FILE_SUFFIX)
    

    with open(str(project_path), 'r') as f:
        contents = f.read()

    project = parse_yaml_raw_as(NeurenderPipelineConfig, contents)
    project.path = project_path.parent
    return project
    