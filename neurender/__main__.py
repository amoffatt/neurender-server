import argparse
from pathlib import Path
from . import NeurenderProject
from .utils.subprocess import run_command

def main():
    parser = argparse.ArgumentParser(description="Run a Neurender project pipeline")
    parser.add_argument("project", type=str, help="path to a project directory")
    parser.add_argument("--pipeline", type=str, default="", help="Specify a specific pipeline to run. Defaults to the pipeline found in the project/pipelines folder")
    parser.add_argument("--output", type=str, default="", help="Specify an output path for pipeline execution artifacts")
    parser.add_argument("--on-finished", type=str, default="", help="Run command when pipeline is finished")

    args = parser.parse_args()

    project = NeurenderProject(args.project)
    pipeline = project.get_pipeline(args.pipeline)
    pipeline.run(working_path=args.output)

    if args.on_finished:
        run_command([args.on_finished])

    
if __name__ == '__main__':
    main()