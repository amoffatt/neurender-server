from argparse import ArgumentParser, Namespace
from pathlib import Path
import asyncio

from . import NeurenderProject
from .utils.subprocess import run_command
from .utils import read_yaml_file
from . import config

#WIP
# s3 = boto3.client('s3', endpoint_url='https://s3.us-west-1.wasabisys.com', aws_access_key_id='DTB5BEMDNKX4GYNJU58M', aws_secret_access_key='akjA8lTJJMgpJbpuKVDukO9SdyAJcpOQyVcmIUu8')
# src_files = s3.list_objects(Bucket='neurender-src-footage')['Content']

def _add_run_args(parser:ArgumentParser):
    parser.add_argument("--pipeline", type=str, default="", help="Specify a specific pipeline to run. Defaults to the pipeline found in the project/pipelines folder")
    parser.add_argument("--output", type=str, default="", help="Specify an output path for pipeline execution artifacts")
    parser.add_argument("--on-finished", type=str, default="", help="Run command when pipeline is finished")
    
async def _run_command(args:Namespace):
    project = await NeurenderProject.load(args.project)
    pipeline = project.get_pipeline(args.pipeline)
    pipeline.run(working_path=args.output)

    if args.on_finished:
        run_command([args.on_finished])



def _add_config_args(parser:ArgumentParser):
    parser.add_argument('--set-all', type=str, default='', help='Provide full YAML config file contents as an argument string')

def _config_command(args:Namespace):
    c = config.load()

    if args.set_all:
        c = config.load_str(args.set_all)

    config.write(c)


def main():
    parser = ArgumentParser(description="Interface to control Neurender pipelines and configuration")
    subparsers = parser.add_subparsers(dest="command")

    _add_run_args(subparsers.add_parser("run", help="Run a Neurender project pipeline"))
    _add_config_args(subparsers.add_parser("config", help="Set Neurender configuration options"))

    parser.add_argument("project", type=str, help="Path to a project directory")

    args = parser.parse_args()

    command = args.command

    if command == "run":
        _run_command(args)
    if command == "config":
        _config_command(args)


    
if __name__ == '__main__':
    main()