#!/usr/bin/env python3
"""Root-level CLI wrapper for hackathon submission reproduction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from rank import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
