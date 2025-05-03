import os
import sys
import subprocess
import asyncio
from pathlib import Path

def get_docker_dir():
    # Try to find the docker directory in the installed package
    try:
        import orka
        package_path = Path(orka.__file__).parent
        docker_dir = package_path / 'docker'
        if docker_dir.exists():
            return str(docker_dir)
    except ImportError:
        pass

    # Fall back to local project structure
    current_dir = Path(__file__).parent
    docker_dir = current_dir / 'docker'
    if docker_dir.exists():
        return str(docker_dir)

    raise FileNotFoundError("Could not find docker directory")

def start_redis():
    docker_dir = get_docker_dir()
    print(f"Using Docker directory: {docker_dir}")
    
    # Stop any existing containers
    print("Stopping any existing containers...")
    subprocess.run(["docker", "compose", "-f", os.path.join(docker_dir, "docker-compose.yml"), "down"], check=False)
    
    # Pull latest images
    print("Pulling latest images...")
    subprocess.run(["docker", "compose", "-f", os.path.join(docker_dir, "docker-compose.yml"), "pull"], check=True)
    
    # Start Redis
    print("Starting containers...")
    subprocess.run(["docker", "compose", "-f", os.path.join(docker_dir, "docker-compose.yml"), "up", "-d", "redis"], check=True)
    print("Redis started.")

def start_backend():
    print("Starting Orka backend...")
    try:
        # Start the backend server
        backend_proc = subprocess.Popen([sys.executable, "-m", "orka.server"])
        print("Orka backend started.")
        return backend_proc
    except Exception as e:
        print(f"Error starting Orka backend: {e}")
        raise

async def main():
    start_redis()
    backend_proc = start_backend()
    print("All services started. Press Ctrl+C to stop.")
    
    try:
        while True:
            await asyncio.sleep(1)
            # Check if backend process is still running
            if backend_proc.poll() is not None:
                print("Orka backend stopped unexpectedly!")
                break
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        backend_proc.wait()
        subprocess.run(["docker", "compose", "-f", os.path.join(get_docker_dir(), "docker-compose.yml"), "down"], check=False)
        print("Services stopped.")

if __name__ == "__main__":
    asyncio.run(main())