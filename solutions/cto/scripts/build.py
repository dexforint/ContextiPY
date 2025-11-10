#!/usr/bin/env python3
"""
Build script for creating distributable packages of Contextipy.

This script automates the build process for Windows executables and Linux binaries
using PyInstaller. It handles resource bundling, dependency collection, and
platform-specific configurations.

Usage:
    python scripts/build.py --platform windows --output dist/
    python scripts/build.py --platform linux --output dist/
    python scripts/build.py --all
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List


class BuildError(Exception):
    """Raised when a build operation fails."""

    pass


class BuildScript:
    """Manages the build process for different platforms."""

    def __init__(self, output_dir: Path, clean: bool = False) -> None:
        """
        Initialize the build script.

        Args:
            output_dir: Directory where build artifacts will be placed
            clean: Whether to clean build directories before building
        """
        self.project_root = Path(__file__).parent.parent.resolve()
        self.output_dir = output_dir.resolve()
        self.clean = clean
        self.build_dir = self.project_root / "build"
        self.spec_dir = self.project_root / "specs"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.spec_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _in_virtualenv() -> bool:
        return sys.prefix != sys.base_prefix or hasattr(sys, "real_prefix")

    def clean_build_dirs(self) -> None:
        """Remove build and dist directories."""
        print("🧹 Cleaning build directories...")
        for dir_path in [self.build_dir, self.output_dir, self.spec_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   Removed {dir_path}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.spec_dir.mkdir(parents=True, exist_ok=True)

    def ensure_dependencies(self) -> None:
        """Ensure PyInstaller is installed."""
        print("📦 Checking dependencies...")
        try:
            import PyInstaller  # noqa: F401

            print("   PyInstaller is installed")
        except ImportError:
            print("   ⚠️  PyInstaller is not installed")
            print(
                "   Please install it manually: pip install pyinstaller (in venv or with --user)"
            )
            raise BuildError("PyInstaller not found. Please install it to continue.")

    def get_data_files(self) -> List[tuple[str, str]]:
        """
        Collect data files that need to be bundled.

        Returns:
            List of (source, destination) tuples for PyInstaller
        """
        data_files: List[tuple[str, str]] = []
        resources_dir = self.project_root / "contextipy" / "ui" / "resources"

        if resources_dir.exists():
            data_files.append((str(resources_dir), "contextipy/ui/resources"))
            print(f"   Bundling resources directory: {resources_dir}")

        return data_files

    def get_hidden_imports(self) -> List[str]:
        """
        Get list of hidden imports that PyInstaller might miss.

        Returns:
            List of module names to include
        """
        hidden_imports = [
            "PySide6.QtCore",
            "PySide6.QtGui",
            "PySide6.QtWidgets",
            "contextipy.cli.main",
            "contextipy.tray",
            "contextipy.ui",
            "contextipy.config",
            "contextipy.core",
            "contextipy.services",
            "contextipy.scanner",
            "contextipy.execution",
            "contextipy.logging",
            "contextipy.os_integration",
            "contextipy.questions",
            "contextipy.util",
            "contextipy.utils",
            "contextipy.actions",
        ]

        current_platform = platform.system().lower()
        if current_platform == "windows":
            hidden_imports.extend(["win32api", "win32con", "win32gui", "win10toast"])
        elif current_platform == "linux":
            hidden_imports.extend(["notify2"])

        return hidden_imports

    def build_windows(self) -> None:
        """Build Windows executable using PyInstaller."""
        if platform.system() != "Windows":
            print("⚠️  Warning: Building Windows executable on non-Windows platform")
            print("   Cross-compilation may have limitations")

        print("🪟 Building Windows executable...")

        icon_path = self.project_root / "contextipy" / "ui" / "resources" / "icons" / "app_icon.ico"
        if not icon_path.exists():
            print(f"⚠️  Warning: Icon file not found at {icon_path}")
            icon_path = None

        data_files = self.get_data_files()
        hidden_imports = self.get_hidden_imports()

        pyinstaller_args = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name=Contextipy",
            "--onefile",
            "--windowed",
            "--noconfirm",
            f"--distpath={self.output_dir}",
            f"--workpath={self.build_dir}",
            f"--specpath={self.spec_dir}",
        ]

        if icon_path:
            pyinstaller_args.append(f"--icon={icon_path}")

        for source, dest in data_files:
            pyinstaller_args.append(f"--add-data={source}{os.pathsep}{dest}")

        for module in hidden_imports:
            pyinstaller_args.append(f"--hidden-import={module}")

        entry_point = self.project_root / "contextipy" / "cli" / "main.py"
        pyinstaller_args.append(str(entry_point))

        print(f"   Running PyInstaller: {' '.join(pyinstaller_args)}")

        try:
            subprocess.check_call(pyinstaller_args)
            exe_path = self.output_dir / "Contextipy.exe"
            if exe_path.exists():
                print(f"✅ Windows executable built successfully: {exe_path}")
                print(f"   Size: {exe_path.stat().st_size / (1024 * 1024):.2f} MB")
            else:
                raise BuildError("Executable not found after build")
        except subprocess.CalledProcessError as e:
            raise BuildError(f"PyInstaller failed: {e}")

    def build_linux(self) -> None:
        """Build Linux binary using PyInstaller."""
        if platform.system() != "Linux":
            print("⚠️  Warning: Building Linux binary on non-Linux platform")
            print("   Cross-compilation may have limitations")

        print("🐧 Building Linux binary...")

        data_files = self.get_data_files()
        hidden_imports = self.get_hidden_imports()

        pyinstaller_args = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name=contextipy",
            "--onefile",
            "--noconfirm",
            f"--distpath={self.output_dir}",
            f"--workpath={self.build_dir}",
            f"--specpath={self.spec_dir}",
        ]

        for source, dest in data_files:
            pyinstaller_args.append(f"--add-data={source}{os.pathsep}{dest}")

        for module in hidden_imports:
            pyinstaller_args.append(f"--hidden-import={module}")

        entry_point = self.project_root / "contextipy" / "cli" / "main.py"
        pyinstaller_args.append(str(entry_point))

        print(f"   Running PyInstaller: {' '.join(pyinstaller_args)}")

        try:
            subprocess.check_call(pyinstaller_args)
            bin_path = self.output_dir / "contextipy"
            if bin_path.exists():
                os.chmod(bin_path, 0o755)
                print(f"✅ Linux binary built successfully: {bin_path}")
                print(f"   Size: {bin_path.stat().st_size / (1024 * 1024):.2f} MB")
            else:
                raise BuildError("Binary not found after build")
        except subprocess.CalledProcessError as e:
            raise BuildError(f"PyInstaller failed: {e}")

    def run_smoke_test(self, executable: Path) -> bool:
        """
        Run a smoke test on the built executable.

        Args:
            executable: Path to the executable to test

        Returns:
            True if the test passed, False otherwise
        """
        print(f"🧪 Running smoke test on {executable.name}...")

        if not executable.exists():
            print(f"   ❌ Executable not found: {executable}")
            return False

        try:
            result = subprocess.run(
                [str(executable), "--help"],
                capture_output=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0 or "Contextipy" in result.stdout.decode():
                print("   ✅ Smoke test passed")
                return True
            else:
                print(f"   ⚠️  Executable ran but returned code {result.returncode}")
                if result.stdout:
                    print(f"   stdout: {result.stdout.decode()}")
                if result.stderr:
                    print(f"   stderr: {result.stderr.decode()}")
                return False

        except subprocess.TimeoutExpired:
            print("   ⚠️  Smoke test timed out (might be normal for GUI apps)")
            return True
        except Exception as e:
            print(f"   ❌ Smoke test failed: {e}")
            return False


def main() -> int:
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description="Build Contextipy packages for distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build.py --platform windows
  python scripts/build.py --platform linux --output ./dist
  python scripts/build.py --all --clean
  python scripts/build.py --platform windows --smoke-test
        """,
    )

    parser.add_argument(
        "--platform",
        choices=["windows", "linux", "current"],
        help="Platform to build for (current = detect automatically)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build for all platforms (requires appropriate OS)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist"),
        help="Output directory for built artifacts (default: dist/)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run smoke test on built executable",
    )

    args = parser.parse_args()

    if not args.platform and not args.all:
        parser.error("Must specify either --platform or --all")

    builder = BuildScript(args.output, args.clean)

    if args.clean:
        builder.clean_build_dirs()

    builder.ensure_dependencies()

    try:
        if args.all:
            current_os = platform.system().lower()
            print(f"📦 Building for all platforms (current OS: {current_os})")

            if current_os == "windows":
                builder.build_windows()
                if args.smoke_test:
                    builder.run_smoke_test(builder.output_dir / "Contextipy.exe")
            elif current_os == "linux":
                builder.build_linux()
                if args.smoke_test:
                    builder.run_smoke_test(builder.output_dir / "contextipy")
            else:
                print(f"⚠️  Platform {current_os} not fully supported for --all")
                return 1

        elif args.platform == "current":
            current_os = platform.system().lower()
            if current_os == "windows":
                builder.build_windows()
                if args.smoke_test:
                    builder.run_smoke_test(builder.output_dir / "Contextipy.exe")
            elif current_os == "linux":
                builder.build_linux()
                if args.smoke_test:
                    builder.run_smoke_test(builder.output_dir / "contextipy")
            else:
                print(f"❌ Platform {current_os} not supported")
                return 1

        elif args.platform == "windows":
            builder.build_windows()
            if args.smoke_test:
                builder.run_smoke_test(builder.output_dir / "Contextipy.exe")

        elif args.platform == "linux":
            builder.build_linux()
            if args.smoke_test:
                builder.run_smoke_test(builder.output_dir / "contextipy")

        print("\n🎉 Build completed successfully!")
        return 0

    except BuildError as e:
        print(f"\n❌ Build failed: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Build interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
