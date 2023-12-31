from argparse import ArgumentParser, Namespace
from pathlib import Path

from . import NeurenderProject
from .utils import print_err
from .utils.subprocess import run_command
from . import config, storage

def _add_project_arg(parser:ArgumentParser):
    parser.add_argument("project", type=str, help="Path or S3 bucket url to a project directory")
    parser.add_argument("-l", "--local-path", type=str, default='', help="If project is remote, specifies a local path to download project files")

def _add_run_args(parser:ArgumentParser):
    _add_project_arg(parser)
    parser.add_argument("-p", "--pipeline", type=str, default="", help="Pipeline filename to run. Defaults to the first pipeline found in the {project}/pipelines folder")
    parser.add_argument("-n", "--no-skip", nargs='+', help="Define steps which must not be skipped, even if their output paths already exist")
    parser.add_argument("-o", "--output", type=str, default="", help="Output path for pipeline execution artifacts. Defaults to {project}/output/{pipeline_filename}")
    parser.add_argument("-u", "--upload-url", type=str, default="", help="Specify and S3 url other than the project URL to upload pipeline output artifacts (specified within the pipeline)")
    parser.add_argument("--on-finished", type=str, default="", help="Run command when pipeline is finished")
    
# The `run` subcommand
def _run_command(args:Namespace):
    project = NeurenderProject.load(args.project, args.local_path)
    pipeline = project.get_pipeline(args.pipeline)

    if not pipeline:
        print_err(f"Pipeline {args.pipeline} not found")
        return


    working_path = args.output
    working_path = pipeline.run(working_path=working_path, no_skip_steps=args.no_skip)

    upload_url = args.upload_url or project.url
    print("Upload url:", upload_url)
    if upload_url:
        pipeline.upload_output_artifacts(Path(working_path), upload_url)

    if args.on_finished:
        run_command([args.on_finished])

def _add_download_args(parser:ArgumentParser):
    parser.add_argument('src', type=str, help="Source directory")
    parser.add_argument('dst', type=str, default='', nargs='?', help="Destination directory")
    parser.add_argument('-s', '--select', type=str, default='', help="Select specific files by glob pattern. **/* selects all subdirectories and files")

# The `download` subcommand
def _download_command(args:Namespace):
    print(f"Downloading {args.src} => {args.dst}")  
    project = NeurenderProject.load(args.src, args.dst, select=args.select)
    print("Done.")

# The `upload` subcommand
def _upload_command(args:Namespace):
    print(f"Uploading {args.src} => {args.dst}")  
    storage.S3().sync_to_remote(args.src, args.dst, select=args.select)
    print("Done.")
    

def _add_config_args(parser:ArgumentParser):
    parser.add_argument('--set-all', type=str, default='', help='Provide full YAML config file contents as an argument string')

# The `config` subcommand
def _config_command(args:Namespace):
    c = config.load()

    if args.set_all:
        c = config.load_str(args.set_all)

    config.write(c)


def main():
    parser = ArgumentParser(description="Interface to control Neurender pipelines and configuration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_run_args(subparsers.add_parser("run", help="Run a Neurender project pipeline"))
    _add_config_args(subparsers.add_parser("config", help="Set Neurender configuration options"))

    _add_download_args(subparsers.add_parser("download", help="Download a Neurender project from an S3 bucket"))
    _add_download_args(subparsers.add_parser("upload", help="Upload a Neurender project to an S3 bucket"))  # same args as download

    args = parser.parse_args()

    command = args.command

    if command == "run":
        _run_command(args)
    if command == "config":
        _config_command(args)
    if command == "download":
        _download_command(args)
    if command == "upload":
        _upload_command(args)



    
if __name__ == '__main__':
    main()

    