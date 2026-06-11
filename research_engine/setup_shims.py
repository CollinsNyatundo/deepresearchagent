"""Setup shims/wrappers for GitNexus and ast-grep.

Creates Windows .cmd shims (delegating to WSL) or WSL bash wrappers (delegating to Windows)
to enable seamless cross-environment tool invocation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_wsl() -> bool:
    """Detect if the current environment is running inside Windows Subsystem for Linux (WSL)."""
    if sys.platform != "linux":
        return False
    try:
        proc_version = Path("/proc/version")
        if proc_version.exists():
            return "microsoft" in proc_version.read_text(encoding="utf-8").lower()
    except Exception:
        pass
    return False


def setup_shims() -> tuple[list[Path], str]:
    """Generate path shims/wrappers depending on host platform.

    Returns:
        A tuple of (list of created/updated files, message description).
    """
    created_files: list[Path] = []

    if sys.platform == "win32":
        # On Windows host, write shims that call WSL
        bin_dir = Path(os.path.expandvars(r"%USERPROFILE%\.bin"))
        bin_dir.mkdir(parents=True, exist_ok=True)

        shims = {
            "gitnexus.cmd": "@echo off\nwsl bash -l -c \"gitnexus \\\"$@\\\"\" -- %*\n",
            "ast-grep.cmd": "@echo off\nwsl bash -l -c \"ast-grep \\\"$@\\\"\" -- %*\n",
            "sg.cmd": "@echo off\nwsl bash -l -c \"sg \\\"$@\\\"\" -- %*\n",
        }

        for name, content in shims.items():
            shim_path = bin_dir / name
            shim_path.write_text(content, encoding="utf-8")
            created_files.append(shim_path)

        message = (
            f"Created Windows .cmd shims in {bin_dir}.\n"
            "Please ensure this directory is added to your Windows PATH environment variable."
        )

    elif is_wsl():
        # On WSL guest, write bash wrappers that delegate to Windows executables
        bin_dir = Path(os.path.expanduser("~/.local/bin"))
        bin_dir.mkdir(parents=True, exist_ok=True)

        # We invoke via cmd.exe /c. For npx-based packages (like gitnexus),
        # npx.cmd is preferred on Windows.
        # For ast-grep, we can check if ast-grep.cmd or sg.cmd works on Windows,
        # or just run it via cmd.exe /c.
        # Note: we need to translate the arguments if they contain WSL paths,
        # but for standard CLI args passing "$@" to cmd.exe works directly.
        wrappers = {
            "gitnexus": (
                "#!/bin/bash\n"
                'cmd.exe /c npx.cmd gitnexus "$@"\n'
            ),
            "ast-grep": (
                "#!/bin/bash\n"
                'cmd.exe /c ast-grep "$@"\n'
            ),
            "sg": (
                "#!/bin/bash\n"
                'cmd.exe /c sg "$@"\n'
            ),
        }

        for name, content in wrappers.items():
            wrapper_path = bin_dir / name
            wrapper_path.write_text(content, encoding="utf-8")
            # Make executable (chmod +x)
            try:
                wrapper_path.chmod(wrapper_path.stat().st_mode | 0o111)
            except Exception:
                pass
            created_files.append(wrapper_path)

        message = (
            f"Created WSL bash wrappers in {bin_dir}.\n"
            "Please ensure this directory is added to your WSL PATH if it is not already."
        )

    else:
        # Unsupported/unneeded platform
        message = f"Shim setup not required for platform: {sys.platform} (non-WSL Linux or macOS)"

    return created_files, message
