#!/usr/bin/env python3
"""Double-click entry point on Windows; also used by the Linux shortcut."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
from editor_runtime import prefer_system_tk
prefer_system_tk()
from launcher import main
main()
