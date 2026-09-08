"""Make the in-repo nepkit importable without installing it.

Each demo script imports this before importing nepkit, so the demo runs
straight from a checkout with no packaging or install step. Python always
puts the executed script's own directory at sys.path[0], so this works
whether a script is run as `python demo/01_basic_conversion.py` from the
repo root or `python 01_basic_conversion.py` from inside demo/.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
