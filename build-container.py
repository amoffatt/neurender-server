import os
import argparse
import dotenv
import subprocess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true', help='Publish the built container to Docker Hub.')
    args = parser.parse_args()

    subprocess.run(['docker-compose', '-f', 'docker-compose.yml', 'build'])


    # Check if the user wants to publish the container.
    if args.publish:
        dotenv.load_dotenv()
        docker_repo = os.environ['DOCKER_REPOSITORY']
        subprocess.run(['docker', 'push', f'{docker_repo}/neurender'])
    else:
        print('To publish the built container to Docker Hub, invoke this script with argument \'publish\'.')

if __name__ == '__main__':
    main()
