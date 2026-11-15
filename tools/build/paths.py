"""Where the build's own files are (assets, texts): the repository's root, or, in the Windows
builder (a PyInstaller bundle), the folder the bundle unpacks to."""
import os
import sys


def resource_root():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
