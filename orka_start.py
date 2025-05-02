import subprocess
import sys
import time
import webbrowser
import os

def start_redis():
    # Try to start Redis server (assumes redis-server is in PATH)
    try:
        subprocess.run(['docker-compose', 'up'])
        print("Redis started.")
    except FileNotFoundError:
        print("redis-server not found. Please install Redis and ensure it's in your PATH.")
        sys.exit(1)

def start_backend():
    # Start the Orka backend (adjust path/module as needed)
    backend_proc = subprocess.Popen([sys.executable, 'orka/server.py'])
    print("Orka backend started.")
    return backend_proc

def open_ui():
    # Open the UI in the default browser
    url = "http://localhost:8000"
    print(f"Opening UI at {url}")
    webbrowser.open(url)

def build_ui():
    print("Building UI...")
    try:
        # Check if npm is installed
        subprocess.run(['npm', '--version'], check=True, capture_output=True)
        
        # Run npm install
        print("Installing UI dependencies...")
        subprocess.run(['npm', 'install'], cwd='UI', check=True)
        
        # Run npm build
        print("Building UI...")
        subprocess.run(['npm', 'run', 'build'], cwd='UI', check=True)
    except FileNotFoundError:
        print("Error: npm is not installed. Please install Node.js from https://nodejs.org/")
        print("After installation, restart your terminal and try again.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error building UI: {e}")
        print(f"Output: {e.output.decode() if e.output else 'No output'}")
        sys.exit(1)

def main():
    print("Starting Redis...")
    start_redis()
    time.sleep(2)  # Give Redis time to start

    build_ui()

    print("Starting Orka backend and UI server...")
    backend_proc = start_backend()
    time.sleep(2)  # Give backend time to start

    open_ui()

    print("All services started. Press Ctrl+C to stop.")
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == '__main__':
    main()