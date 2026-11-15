"""Makes the build's modules importable: from a checkout they are in tools/ and text/ of the
repository; in the Windows builder PyInstaller has already collected them."""
import os
import sys


def setup():
    if getattr(sys, 'frozen', False):
        return
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for folder in ('tools', 'text'):
        sys.path.insert(0, os.path.join(root, folder))
