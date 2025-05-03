import subprocess
import sys
import time
import os
import platform


def check_docker():
    """Check if Docker is installed and running."""
    try:
        # Check if docker command exists and get version
        result = subprocess.run(['docker', '--version'], check=True, capture_output=True, text=True)
        print(f"Docker version: {result.stdout.strip()}")
        
        # Check if docker daemon is running
        result = subprocess.run(['docker', 'info'], check=True, capture_output=True, text=True)
        print("Docker daemon is running")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error checking Docker: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Docker command not found in PATH")
        return False

def check_docker_compose():
    """Check if docker-compose is available (either as a standalone command or as a plugin)."""
    try:
        # Try the new docker compose plugin first
        result = subprocess.run(['docker', 'compose', '--version'], check=True, capture_output=True, text=True)
        print(f"Docker Compose plugin version: {result.stdout.strip()}")
        return 'docker compose'
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print("Docker Compose plugin not found, trying legacy docker-compose...")
        try:
            # Try the old docker-compose command
            result = subprocess.run(['docker-compose', '--version'], check=True, capture_output=True, text=True)
            print(f"Legacy docker-compose version: {result.stdout.strip()}")
            return 'docker-compose'
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print("Legacy docker-compose not found")
            return None

def start_redis():
    """Start Redis using Docker Compose."""
    if not check_docker():
        print("Docker is not properly installed or running.")
        print("Please ensure Docker Desktop is running and try again.")
        sys.exit(1)

    docker_compose_cmd = check_docker_compose()
    if not docker_compose_cmd:
        print("Docker Compose not found. Please ensure Docker is properly installed.")
        print("If you're using Docker Desktop, you might need to enable the Docker Compose plugin.")
        print("You can enable it in Docker Desktop settings under 'Features in development'.")
        sys.exit(1)

    try:
        # The docker directory is inside the orka package
        docker_dir = os.path.join(os.path.dirname(__file__), 'docker')
        if not os.path.exists(docker_dir):
            print(f"Docker directory not found at: {docker_dir}")
            sys.exit(1)
            
        print(f"Using Docker directory: {docker_dir}")
        os.chdir(docker_dir)
        
        # Split the command into a list for subprocess
        compose_cmd = docker_compose_cmd.split()
        
        # Run the commands with the appropriate compose command
        print("Stopping any existing containers...")
        subprocess.run(compose_cmd + ['down', '--remove-orphans'], check=True)
        
        print("Pulling latest images...")
        subprocess.run(compose_cmd + ['pull'], check=True)
        
        print("Starting containers...")
        proc = subprocess.Popen(compose_cmd + ['up', '--build'])
        print("Redis started.")
        return proc
    except FileNotFoundError:
        print("Docker command not found. Please ensure Docker is installed and in your PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error starting Redis: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Error output: {e.stderr}")
        print("Please make sure Docker is running and try again.")
        sys.exit(1)

def start_backend():
    """Start the Orka backend."""
    backend_proc = subprocess.Popen([sys.executable, '-m', 'orka.server'])
    print("Orka backend started.")
    return backend_proc

def main():
    print("Starting Redis...")
    start_redis()
    time.sleep(2)  # Give Redis time to start

    print("Starting Orka backend...")
    backend_proc = start_backend()
    time.sleep(2)  # Give backend time to start

    print("All services started. Press Ctrl+C to stop.")
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == '__main__':
    main()