#!/usr/bin/env python3
"""
Build script for the Rust core using maturin.
"""

import subprocess
import sys
import os

def main():
    """Build the Rust extension module."""
    print("Building Rust core with maturin...")
    
    # Ensure maturin is installed
    print("Installing maturin...")
    subprocess.run(["uv", "pip", "install", "maturin"], check=True)
    
    # Build the extension
    env = os.environ.copy()
    # Tell maturin to build in-place for development
    result = subprocess.run(
        ["uv", "run", "maturin", "develop", "--release"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )
    
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)
    
    print("Build successful!")

if __name__ == "__main__":
    main()