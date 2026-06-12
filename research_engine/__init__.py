"""Deep Research Agent — a general-purpose deep research engine."""

import sys

# OS-agnostic stdout/stderr UTF-8 reconfiguration to prevent UnicodeEncodeErrors on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

__version__ = "0.1.0"

