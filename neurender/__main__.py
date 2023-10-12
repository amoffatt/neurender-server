import argparse
from . import load_from_yaml
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Run a Neurender project pipeline")
    parser.add_argument("project", type=str, help="path to a project directory")
    parser.add_argument("--config", type=str, default="neurender-project", help="Specify a specific configuration to run")

    args = parser.parse_args()

    file_path = Path(args.project) / args.config
    project = load_from_yaml(file_path)
    project.run_pipeline()


    
if __name__ == '__main__':
    main()