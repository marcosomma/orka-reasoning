#!/usr/bin/env python
"""
Script to build the OrKa documentation.
"""

import os
import shutil
import subprocess
import sys


def main():
    """Run the main documentation build process."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Path to the source code
    orka_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "orka"))

    # Create directories if they don't exist
    os.makedirs(os.path.join(script_dir, "_build"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "_static"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "_templates"), exist_ok=True)

    # Get the current Python executable
    python_exe = sys.executable

    # Try to find sphinx executables
    sphinx_apidoc = shutil.which("sphinx-apidoc")
    sphinx_build = shutil.which("sphinx-build")

    print("Generating module documentation...")
    try:
        if sphinx_apidoc:
            # Use direct command if available
            subprocess.run(
                [
                    sphinx_apidoc,
                    "-f",
                    "-o",
                    script_dir,
                    orka_dir,
                    "--separate",
                    "--module-first",
                ],
                check=True,
            )
        else:
            # Fall back to module approach
            subprocess.run(
                [
                    python_exe,
                    "-m",
                    "sphinx.ext.apidoc",
                    "-f",
                    "-o",
                    script_dir,
                    orka_dir,
                    "--separate",
                    "--module-first",
                ],
                check=True,
            )
    except subprocess.CalledProcessError:
        # If both methods fail, try with pip install first
        print("Installing sphinx and dependencies...")
        subprocess.run(
            [python_exe, "-m", "pip", "install", "sphinx", "sphinx-rtd-theme"],
            check=True,
        )

        # Try again with the module
        print("Retrying documentation generation...")
        subprocess.run(
            [
                python_exe,
                "-c",
                "from sphinx.ext import apidoc; apidoc.main(['-f', '-o', r'"
                + script_dir
                + "', r'"
                + orka_dir
                + "', '--separate', '--module-first'])",
            ],
            check=True,
        )

    print("Building HTML documentation...")
    html_dir = os.path.join(script_dir, "_build", "html")

    try:
        if sphinx_build:
            # Use direct command if available
            subprocess.run(
                [sphinx_build, "-b", "html", script_dir, html_dir], check=True
            )
        else:
            # Fall back to module approach
            subprocess.run(
                [
                    python_exe,
                    "-c",
                    "import sphinx.cmd.build; sphinx.cmd.build.main(['-b', 'html', r'"
                    + script_dir
                    + "', r'"
                    + html_dir
                    + "'])",
                ],
                check=True,
            )
    except subprocess.CalledProcessError:
        print("Retrying HTML build with direct import...")
        subprocess.run(
            [
                python_exe,
                "-c",
                "import sphinx; sphinx.build_main(['-b', 'html', r'"
                + script_dir
                + "', r'"
                + html_dir
                + "'])",
            ],
            check=True,
        )

    print(f"Documentation built successfully in {html_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
