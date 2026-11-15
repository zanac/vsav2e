# PyInstaller spec of the vsav2e builder: one windowed program with the build's pictures
# and checksums inside. Run from the repository's root:  pyinstaller tools/builder/vsav2e_builder.spec
import os

root = os.path.abspath(os.getcwd())

analysis = Analysis(
    [os.path.join(root, 'tools', 'builder', 'vsav2e_builder.py')],
    pathex=[root, os.path.join(root, 'tools'), os.path.join(root, 'text'),
            os.path.join(root, 'tools', 'builder')],
    datas=[(os.path.join(root, 'assets'), 'assets'),
           (os.path.join(root, 'tools', 'builder', 'reference_checksums.txt'), 'tools/builder')],
    hiddenimports=['make_vsav2e', 'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext', 'tkinter.filedialog',
                   'tkinter.messagebox'],
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, analysis.binaries, analysis.datas, [],
    name='vsav2e-builder',
    console=False,          # a window, no black console behind it
    upx=False,
)
