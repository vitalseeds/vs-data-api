"""
Cross-platform build script for VS Data API executable.

Usage:
    python deploy/build.py          # Build executable
    python deploy/build.py --clean  # Clean build artifacts first
    python deploy/build.py --test   # Run executable after build to test

Requirements:
    pip install pyinstaller>=6.0
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


def clean_build():
    """Remove previous build artifacts."""
    paths_to_clean = ["build", "dist"]

    for path_name in paths_to_clean:
        path = PROJECT_ROOT / path_name
        if path.exists():
            shutil.rmtree(path)
            print(f"Cleaned: {path}")

    # Clean __pycache__ directories (but not in .venv)
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        if ".venv" not in str(pycache):
            shutil.rmtree(pycache)
            print(f"Cleaned: {pycache}")


def build():
    """Run PyInstaller build."""
    spec_file = PROJECT_ROOT / "vsdata-server.spec"

    if not spec_file.exists():
        print(f"Error: Spec file not found at {spec_file}")
        sys.exit(1)

    # Use uv run to ensure correct environment
    uv_path = shutil.which("uv")
    if uv_path:
        cmd = ["uv", "run", "pyinstaller", str(spec_file)]
    else:
        cmd = [sys.executable, "-m", "PyInstaller", str(spec_file)]

    print(f"Building with: {' '.join(cmd)}")
    print(f"Working directory: {PROJECT_ROOT}")
    print()

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        output_dir = PROJECT_ROOT / "dist" / "vsdata-server"
        print()
        print("=" * 60)
        print("Build successful!")
        print("=" * 60)
        print(f"Output directory: {output_dir}")

        # List output files
        if output_dir.exists():
            exe_name = "vsdata-server.exe" if sys.platform == "win32" else "vsdata-server"
            exe_path = output_dir / exe_name
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"Executable: {exe_path} ({size_mb:.1f} MB)")

        print()
        print("To test the build:")
        if sys.platform == "win32":
            print(f"  .\\dist\\vsdata-server\\vsdata-server.exe")
        else:
            print(f"  ./dist/vsdata-server/vsdata-server")
    else:
        print()
        print("Build failed!")
        sys.exit(1)


def test_executable():
    """Run the built executable to test it."""
    output_dir = PROJECT_ROOT / "dist" / "vsdata-server"
    exe_name = "vsdata-server.exe" if sys.platform == "win32" else "vsdata-server"
    exe_path = output_dir / exe_name

    if not exe_path.exists():
        print(f"Error: Executable not found at {exe_path}")
        print("Run build first: python deploy/build.py")
        sys.exit(1)

    print(f"Running: {exe_path}")
    print("Press Ctrl+C to stop")
    print()

    try:
        subprocess.run([str(exe_path)])
    except KeyboardInterrupt:
        print("\nStopped")


def main():
    parser = argparse.ArgumentParser(
        description="Build VS Data API executable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy/build.py          # Build executable
  python deploy/build.py --clean  # Clean and build
  python deploy/build.py --test   # Run built executable
        """,
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts before building",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the built executable after building",
    )
    args = parser.parse_args()

    if args.clean:
        clean_build()

    if args.test and not args.clean:
        # Just test, don't build
        test_executable()
    else:
        build()
        if args.test:
            print()
            test_executable()


if __name__ == "__main__":
    main()
