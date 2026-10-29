"""Compatibility entrypoint for the original project.

Original code preserved verbatim in legacy/original_main.py.
Run: python main-2.py run --config configs/demo.json
     python main-2.py serve
"""

from canon.cli import main

if __name__ == "__main__":
    main()
