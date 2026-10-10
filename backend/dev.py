#!/usr/bin/env python3
"""One-command dev script for LAYOVER backend."""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and exit if it fails."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        sys.exit(result.returncode)

def main():
    """Main development script."""
    backend_dir = Path(__file__).parent
    
    # Check if virtual environment exists
    venv_dir = backend_dir / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment...")
        run_command("python -m venv .venv", cwd=backend_dir)
    
    # Determine activate script path
    if os.name == 'nt':  # Windows
        activate_script = venv_dir / "Scripts" / "activate.bat"
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:  # Unix-like
        activate_script = venv_dir / "bin" / "activate"  
        python_exe = venv_dir / "bin" / "python"
    
    # Install dependencies
    print("Installing dependencies...")
    run_command(f'"{python_exe}" -m pip install --upgrade pip', cwd=backend_dir)
    run_command(f'"{python_exe}" -m pip install -r requirements.txt', cwd=backend_dir)
    
    # Check for .env file
    env_file = backend_dir / ".env"
    if not env_file.exists():
        print("Creating .env file from example...")
        example_file = backend_dir / ".env.example"
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("Please edit .env file with your API keys!")
    
    # Run the server
    print("Starting development server...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)
    
    cmd = f'"{python_exe}" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
    subprocess.run(cmd, shell=True, cwd=backend_dir, env=env)

if __name__ == "__main__":
    main()