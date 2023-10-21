import sys, os
import argparse
import dotenv
import subprocess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--publish', action='store_true', help='Publish the built container to Docker Hub.')
    parser.add_argument('-t', '--tag', type=str, required=True, help='Version tag name for the built docker image')
    args = parser.parse_args()

    os.environ['IMAGE_TAG'] = args.tag
    status = subprocess.call(['docker-compose', '-f', 'docker-compose.yml', 'build'])

    if status != 0:
        sys.exit("Error building container.")


    # Check if the user wants to publish the container.
    if args.publish:
        dotenv.load_dotenv()
        docker_repo = os.environ['DOCKER_REPOSITORY']
        image = f'{docker_repo}/neurender:{args.tag}'
        print("Publishing", image)
        status = subprocess.call(['docker', 'push', image])
        sys.exit(status)
    else:
        print('To publish the built container to Docker Hub, invoke this script with argument \'publish\'.')

if __name__ == '__main__':
    main()
