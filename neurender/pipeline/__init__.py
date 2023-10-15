import os
import shutil
from typing import List, Literal, Tuple
from pathlib import Path
from pydantic import BaseModel, root_validator
from abc import ABCMeta, abstractmethod
from PIL import Image
from am_imaging.video.frame_selection import export_sharpest_frames
from ..utils import path_str
from ..utils.subprocess import run_command

from neurender.paths import GAUSSIAN_SPLATTING_ROOT, NERFSTUDIO_GAUSSIAN_SPLATTING_ROOT


SRC_MEDIA_PATH = 'media'
STAGED_MEDIA_PATH = 'media-staged'
REGISTERED_MEDIA_PATH = 'media-registered'
REGISTERED_MEDIA_GS_PATH = 'media-registered-gaussian-splatting'

NERF_MODEL_PATH = 'model-nerf'
GS_MODEL_PATH = 'model-gaussian-splatting'

class RunContext:
    def __init__(self, project_path:Path, working_path:Path, no_skip_steps=[]):
        self.project_path = project_path
        self.working_path = working_path
        self.no_skip_steps = no_skip_steps or []

    def can_skip_step(self, step:"PipelineStep"):
        name = step.name
        return name not in self.no_skip_steps

    @property
    def src_media_path(self) -> Path:
        return self.project_path / SRC_MEDIA_PATH

    @property
    def staged_media_path(self) -> Path:
        return self.working_path / STAGED_MEDIA_PATH


class PipelineStep(BaseModel):
     
    @abstractmethod
    def run(self, ctx:RunContext):
        pass

    def _skip_step(self, ctx:RunContext, output_path:Path, substep='main'):
        result = output_path.exists() and ctx.can_skip_step(self)
        if result:
            print(f" ==> Skipping step {self.name}:{substep}")

        return result

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return f"{self.name}({super().__str__()})"


class _BaseImportStep(PipelineStep):
    # Scale long edge of frame to dimension
    # 0 indicates no rescaling
    scale_to_max:float = 0

    # Alternatively, downscale frames by a factor
    downscale:float = 1

    def _get_scaling(self, frame_size:Tuple[int, int]) -> float:
        if self.scale_to_max != 0:
            max_dimension = max(frame_size[0], frame_size[1])
            return min(1, self.scale_to_max / max_dimension)
        return 1 / self.downscale

    def _get_scaled_frame(self, frame_size:Tuple[int, int]) -> Tuple[int, int]:
        scaling = self._get_scaling(frame_size)
        return (int(frame_size[0] * scaling), int(frame_size[1] * scaling))

    @property
    def is_rescaling_set(self):
        return self.scale_to_max != 0 or self.downscale != 1


    def _get_stage_file_path(self, ctx:RunContext, src_file_path:Path):
        # Destination path, flattening directory structure for SFM scripts
        subpath = src_file_path.relative_to(ctx.src_media_path)
        flat_filename = str(subpath).replace('/', '_')
        stage_file_path = ctx.staged_media_path / flat_filename
        stage_file_path.parent.mkdir(parents=True, exist_ok=True)
        return stage_file_path



class ImportImageBatch(_BaseImportStep):
    select:str = "**/*"

    def run(self, ctx:RunContext):
        src_path = ctx.src_media_path

        print("Collecting images in", src_path)
        for src_file_path in Path(src_path).glob(self.select):
            if not src_file_path.is_file():
                continue

            stage_file_path = self._get_stage_file_path(ctx, src_file_path)

            if self._skip_step(ctx, stage_file_path, substep=str(src_file_path)):
                continue

            if self.is_rescaling_set:
                print(f"Rescaling image {src_file_path}")
                image = Image.open(src_file_path)

                new_size = self._get_scaled_frame(image.size)
                image.thumbnail(new_size, Image.ANTIALIAS)

                image.save(stage_file_path)
            else:
                shutil.copy(src_file_path, stage_file_path)


class ImportVideo(_BaseImportStep):
    # Relative to {project}/media path
    file_path:str
    extraction_interval:int = 1
    downscale:float = 1

    def run(self, ctx:RunContext):
        input_path = ctx.src_media_path / self.file_path
        output_frame_prefix = path_str(self.get_stage_file_path(ctx, input_path)) + '_'
        export_sharpest_frames(input_path,
                               ctx.staged_media_path,
                               output_frame_prefix,
                               downscale=self.downscale,
                               interval=self.extraction_interval)
        
    
MatchingMethodID = Literal['exhaustive', 'sequential', 'vocab_tree']
MatcherTypeID = Literal['any', 'NN', 'superglue', 'superglue-fast', 'NN-superpoint', 'NN-ratio', 'NN-mutual', 'adalam']
FeatureTypeID = Literal['any', 'sift', 'superpoint', 'superpoint_aachen', 'superpoint_max', 'superpoint_inloc', 'r2d2', 'd2net-ss', 'sosnet', 'disk']

class RegisterImages(PipelineStep):
    # Relative to media-staged/
    input_path:str = '.'

    # Relative to working path
    output_path:str = REGISTERED_MEDIA_PATH

    matching_method:MatchingMethodID = 'exhaustive'
    matcher_type:MatcherTypeID = 'any'
    feature_type:FeatureTypeID = 'any'

    def run(self, ctx:RunContext):
        print("Processing data at path:", ctx.staged_media_path)

        output_path = ctx.working_path / self.output_path

        # Skip registration if output dir already exists
        if self._skip_step(ctx, output_path):
            return

        run_command([
            'ns-process-data',
            'images',
            '--data', ctx.staged_media_path / self.input_path,
            '--output-dir', self.output_path,
            '--matching-method', self.matching_method,
            '--matcher-type', self.matcher_type,
            '--feature-type', self.feature_type,
        ])


class SetupGaussianSplattingData(PipelineStep):

    def run(self, ctx:RunContext):
        input_path = ctx.working_path / REGISTERED_MEDIA_PATH
        output_path = ctx.working_path / REGISTERED_MEDIA_GS_PATH

        if self._skip_step(ctx, output_path):
            return

        shutil.copytree(input_path / 'colmap', output_path / 'distorted', dirs_exist_ok=True)
        shutil.copytree(input_path / 'images', output_path / 'input', dirs_exist_ok=True)

        # Undistort aligned images
        run_command([
            "python3", "convert.py",
             "--source_path", output_path,
             "--skip_matching",
        ], cwd=GAUSSIAN_SPLATTING_ROOT)
        
    
class TrainingStep(PipelineStep):
        pass

class TrainGaussianSplattingModel(TrainingStep):
    resolution:int = 1920
    iterations:int = 30_000
    save_iterations:List[int] = []
    # Number of iterations between model saves and checkpoints
    save_frequency:int = 0

    def run(self, ctx:RunContext):

        model_path = ctx.working_path / GS_MODEL_PATH

        # Prevent skipping training step for now
        # if self._skip_step(ctx, model_path):
        #     return

        save_iterations = self.save_iterations
        if self.save_frequency > 0:
            save_iterations += list(range(0, self.iterations, self.save_frequency))
        save_iterations += [self.iterations]
        save_iterations = sorted(set(save_iterations))

        run_command([
            "python3", "train.py",
             "--source_path", ctx.working_path / REGISTERED_MEDIA_GS_PATH,
             "--model_path", model_path,
             "--iterations", self.iterations,
             "--resolution", self.resolution,
             "--save_iterations", *save_iterations,
             "--checkpoint_iterations", *save_iterations,
        ], cwd=GAUSSIAN_SPLATTING_ROOT)

        
class RunNerfStudioGaussianSplattingViewer(PipelineStep):
    def run(self, ctx:RunContext):
        run_command([
            "python3",
            "nerfstudio/scripts/gaussian_splatting/run_viewer.py",
             "--model-path", ctx.working_path / GS_MODEL_PATH,
        ], cwd=NERFSTUDIO_GAUSSIAN_SPLATTING_ROOT)


    
    
    
        