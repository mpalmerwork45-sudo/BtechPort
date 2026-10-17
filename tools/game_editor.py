#!/usr/bin/env python3
"""Launch the shared project, roster, map and event editor."""
from editor_runtime import prefer_system_tk
prefer_system_tk()
from roster_editor import main
if __name__ == "__main__":
    main()
