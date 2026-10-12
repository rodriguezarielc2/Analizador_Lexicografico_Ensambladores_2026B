"""Launch the local Tkinter app."""

import tkinter as tk

from gui import AssemblerApp


def main() -> None:
    root = tk.Tk()
    AssemblerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
