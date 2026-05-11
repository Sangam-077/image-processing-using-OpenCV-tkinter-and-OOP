"""
main.py
-------
Entry point for the Spot-the-Difference desktop application.

Run with:
    python main.py
"""

import tkinter as tk
from game_ui import GameUI


def main() -> None:
    root = tk.Tk()
    app = GameUI(root)   # noqa: F841  (kept alive by the event loop)
    root.mainloop()


if __name__ == "__main__":
    main()
