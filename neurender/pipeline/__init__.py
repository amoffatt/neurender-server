import os
import shutil
from typing import List, Literal
from pathlib import Path
from pydantic import BaseModel, root_validator
from abc import ABCMeta, abstractmethod
from am_imaging.video.frame_selection import export_sharpest_frames
from ..utils import path_str
from ..utils.subprocess import run_command

from neurender.paths import GAUSSIAN_SPLATTING_ROOT


SRC_MEDIA_PATH = 'src-media'
STAGED_MEDIA_PATH = 'staged-media'
REGISTERED_MEDIA_PATH = 'registered-media'
REGISTERED_MEDIA_GS_PATH = 'registered-media-gaussian-splatting'


class PipelineStep(BaseModel):
     
    @abstractmethod
    def run(self, project_path:Path, working_path:Path):
        pass

    def __str__(self):
        return f"{self.__class__.__name__}({super().__str__()})"


class ImportImageBatch(PipelineStep):
    input_path:str = SRC_MEDIA_PATH
    output_path:str = STAGED_MEDIA_PATH

    # Scale long edge of frame to dimension
    # 0 indicates no rescaling
    scale_to_max:float = 0
    scaling:float = 1

    def run(self, project:Path, working_path:Path):
        input_path = project / self.input_path
        output_path = working_path / self.output_path
        if self.scale_to_max == 0 and self.scaling == 1:
            shutil.copytree(input_path, output_path, dirs_exist_ok=True)
        else:
            for fn in os.listdir(input_path):
                print(f"Rescaling image {fn}")
                image = Image.open(input_path / fn)

                scaling = self.scaling
                if self.scale_to_max != 0:
                    max_dimension = max(image.width, image.height)
                    scaling = scale_to_max_dimension / max_dimension

                new_size = (int(image.width * scaling), int(image.height * scaling))
                image.thumbnail(new_size, Image.ANTIALIAS)

                # Save the resized image.
                image.save(output_path / fn)


class ImportVideoFile(PipelineStep):
    input_path:str
    output_path:str = STAGED_MEDIA_PATH
    extraction_interval:int = 1
    downscale:float = 1

    def run(self, project_path:Path, working_path:Path):
        todo()
        export_sharpest_frames()
        
    

class RegisterImages(PipelineStep):
    input_path:str = STAGED_MEDIA_PATH
    output_path:str = REGISTERED_MEDIA_PATH

    def run(self, project:Path, working_path:Path):
        run_command([
            'ns-process-data',
            'images',
            '--data', self.input_path,
            '--output-dir', self.output_path,
        ], cwd=path_str(working_path))


class SetupGaussianSplattingData(PipelineStep):

    def run(self, project:Path, working_path:Path):
        input_path = working_path / REGISTERED_MEDIA_PATH
        output_path = working_path / REGISTERED_MEDIA_GS_PATH
        shutil.copytree(input_path / 'colmap', output_path / 'distorted', dirs_exist_ok=True)
        shutil.copytree(input_path / 'images', output_path / 'input', dirs_exist_ok=True)
    def run(self, project:Path):
        input_path = project / REGISTERED_MEDIA_PATH
        output_path = project / REGISTERED_MEDIA_GS_PATH
        shutil.copytree(input_path / 'colmap', output_path / 'distorted')
        shutil.copytree(input_path / 'images', output_path / 'input')
        
    
class TrainingStep(PipelineStep):
        pass

class TrainGaussianSplattingModel(TrainingStep):
    resolution:int = 1920
    iterations:int = 30_000
    save_iterations:List[int] = [7000, 30_000]

    def run(self, project:Path, working_path:Path):
        source_path = working_path / REGISTERED_MEDIA_GS_PATH

        run_command([
            "python3", "train.py",
             "--source_path", source_path,
             "--iterations", self.iterations,
             "--resolution", self.resolution,
             "--save_iterations", *self.save_iterations,
        ], cwd=GAUSSIAN_SPLATTING_ROOT)

        
    
        