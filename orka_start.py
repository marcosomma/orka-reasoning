import subprocess
import sys
import time
import webbrowser
import os
import shutil


def start_redis():
    # Try to start Redis server (assumes docker-compose is in PATH)
    try:
        subprocess.run(['docker-compose', 'down', '--remove-orphans'], check=True)
        subprocess.run(['docker-compose', 'pull'], check=True)  # Optional: always pull latest images
        proc = subprocess.Popen(['docker-compose', 'up', '--build'])
        print("Redis started.")
        return proc
    except FileNotFoundError:
        print("docker-compose not found. Please install Docker and ensure it's in your PATH.")
        sys.exit(1)

def start_backend():
    # Start the Orka backend (adjust path/module as needed)
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