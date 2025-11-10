#!/usr/bin/env python3
"""
Alternative build script using Nuitka for Windows.

Nuitka compiles Python code to C and produces native executables, often with
better performance and smaller size compared to PyInstaller.

Usage:
    python scripts/build_nuitka.py --output dist/
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Build Windows executable using Nuitka."""
    if platform.system() != "Windows":
        print("⚠️  This script is designed for Windows builds")
        return 1

    parser = argparse.ArgumentParser(description="Build Contextipy with Nuitka")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist"),
        help="Output directory (default: dist/)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.resolve()
    output_dir = args.output.resolve()

    if args.clean:
        print("🧹 Cleaning build directories...")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        build_dir = project_root / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("📦 Installing Nuitka...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka", "ordered-set"])
    except subprocess.CalledProcessError:
        print("❌ Failed to install Nuitka")
        return 1

    icon_path = project_root / "contextipy" / "ui" / "resources" / "icons" / "app_icon.ico"
    resources_dir = project_root / "contextipy" / "ui" / "resources"
    entry_point = project_root / "contextipy" / "cli" / "main.py"

    print("🔨 Building with Nuitka...")

    nuitka_args = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--windows-disable-console",
        f"--output-dir={output_dir}",
        "--enable-plugin=pyside6",
        "--include-package=contextipy",
    ]

    if icon_path.exists():
        nuitka_args.append(f"--windows-icon-from-ico={icon_path}")

    if resources_dir.exists():
        nuitka_args.append(f"--include-data-dir={resources_dir}=contextipy/ui/resources")

    nuitka_args.append(str(entry_point))

    print(f"   Running: {' '.join(nuitka_args)}")

    try:
        subprocess.check_call(nuitka_args)
        print("✅ Nuitka build completed")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Nuitka build failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
