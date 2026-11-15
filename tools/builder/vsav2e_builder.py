#!/usr/bin/env python3
"""vsav2e builder: a window that makes vsav2e.zip (Darkstalkers 3, the full-roster English
Vampire Savior 2) from your own MAME sets.

You choose the folder with vsav2.zip, vsav.zip and vhunt2.zip (MAME's), and the folder for the
result; the pictures, texts and tools the build needs are inside this program. Nothing is
sent anywhere. When the build ends, the checksums of the chips are compared with the ones of the
release this builder comes from.

Without a window (for tests and scripts):  vsav2e_builder.py --cli ROM_FOLDER OUTPUT_FOLDER
"""
import contextlib
import os
import queue
import sys
import threading
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
# from a checkout: the repository's root is two folders up (frozen, make_vsav2e is inside the bundle)
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from tools_path import setup  # noqa: E402  (makes `build`, `cps2` and the texts importable)
setup()
import make_vsav2e  # noqa: E402
from build import paths  # noqa: E402

REQUIRED_SETS = ['vsav2.zip', 'vsav.zip', 'vhunt2.zip']
REFERENCE = os.path.join(paths.resource_root(), 'tools', 'builder', 'reference_checksums.txt')


def missing_sets(rom_folder):
    """the names of the sets not in the folder"""
    return [name for name in REQUIRED_SETS if not os.path.isfile(os.path.join(rom_folder, name))]


def compare_with_reference(lines):
    """(True/False/None, text): do the chips' checksums match the release's? None: no reference"""
    if not os.path.isfile(REFERENCE):
        return None, 'No reference checksums in this builder.'
    reference = [line.strip() for line in open(REFERENCE) if line.strip()]
    built = [line.strip() for line in lines]
    if built == reference:
        return True, 'The chips match the release exactly.'
    different = [line.split()[0] for line, expected in zip(built, reference) if line != expected]
    return False, 'Different from the release: %s (other MAME sets than the ones it was made with?)' % \
        (', '.join(different) or 'the list of chips')


def run_build(rom_folder, output_folder, log):
    """the whole job; returns (zip path, reference verdict, text)"""
    absent = missing_sets(rom_folder)
    if absent:
        raise RuntimeError('Not in %s: %s' % (rom_folder, ', '.join(absent)))
    path, lines = make_vsav2e.build_set(rom_folder, output_folder, log)
    verdict, text = compare_with_reference(lines)
    log(text)
    return path, verdict, text


class LogWriter:
    """a file-like object whose lines go to the window's log (the build prints as it goes)"""

    def __init__(self, lines):
        self.lines = lines

    def write(self, text):
        if text:
            self.lines.put(text)
        return len(text)

    def flush(self):
        pass


def window():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    root = tk.Tk()
    root.title('vsav2e builder - Darkstalkers 3')
    root.minsize(640, 460)
    rom_folder, output_folder = tk.StringVar(), tk.StringVar()
    lines = queue.Queue()
    state = {'running': False}

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill='both', expand=True)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(4, weight=1)

    ttk.Label(frame, text='Folder with vsav2.zip, vsav.zip and vhunt2.zip (your MAME ROM sets):').grid(
        row=0, column=0, columnspan=3, sticky='w')
    ttk.Entry(frame, textvariable=rom_folder).grid(row=1, column=0, columnspan=2, sticky='ew', padx=(0, 6))
    ttk.Button(frame, text='Browse...', command=lambda: choose(rom_folder, True)).grid(row=1, column=2)
    ttk.Label(frame, text='Where to put vsav2e.zip:').grid(row=2, column=0, columnspan=3, sticky='w', pady=(10, 0))
    ttk.Entry(frame, textvariable=output_folder).grid(row=3, column=0, columnspan=2, sticky='ew', padx=(0, 6))
    ttk.Button(frame, text='Browse...', command=lambda: choose(output_folder, False)).grid(row=3, column=2)
    log = scrolledtext.ScrolledText(frame, height=14, state='disabled', font=('Consolas', 9), wrap='none')
    log.grid(row=4, column=0, columnspan=3, sticky='nsew', pady=10)
    progress = ttk.Progressbar(frame, mode='determinate')
    progress.grid(row=5, column=0, columnspan=2, sticky='ew', padx=(0, 6))
    button = ttk.Button(frame, text='Build vsav2e.zip', command=lambda: start())
    button.grid(row=5, column=2)
    status = ttk.Label(frame, text='Choose the folders, then build. It takes about a minute.')
    status.grid(row=6, column=0, columnspan=3, sticky='w', pady=(8, 0))

    def choose(variable, is_rom_folder):
        folder = filedialog.askdirectory(title='Choose a folder')
        if folder:
            variable.set(folder)
            if is_rom_folder and not output_folder.get():
                output_folder.set(folder)

    def append(text):
        log.configure(state='normal')
        log.insert('end', text)
        log.see('end')
        log.configure(state='disabled')

    def start():
        if state['running']:
            return
        rom, out = rom_folder.get().strip(), output_folder.get().strip()
        if not rom or not out:
            messagebox.showwarning('vsav2e builder', 'Choose both folders.')
            return
        absent = missing_sets(rom)
        if absent:
            messagebox.showerror('vsav2e builder', 'Not in that folder: %s' % ', '.join(absent))
            return
        state['running'] = True
        button.state(['disabled'])
        progress.configure(mode='indeterminate')
        progress.start(12)
        status.configure(text='Building...')
        append('Building from %s\n' % rom)
        threading.Thread(target=work, args=(rom, out), daemon=True).start()

    def work(rom, out):
        writer = LogWriter(lines)
        try:
            with contextlib.redirect_stdout(writer):
                path, verdict, text = run_build(rom, out, print)
            lines.put(('done', path, verdict, text))
        except Exception as error:                      # shown in the window, not lost
            lines.put(traceback.format_exc())
            lines.put(('failed', str(error)))

    def poll():
        while True:
            try:
                item = lines.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, str):
                append(item)
            elif item[0] == 'done':
                finish('Done: %s. %s' % (item[1], item[3]), True)
            else:
                finish('Failed: %s' % item[1], False)
        root.after(100, poll)

    def finish(text, ok):
        state['running'] = False
        progress.stop()
        progress.configure(mode='determinate', value=0)
        button.state(['!disabled'])
        status.configure(text=text)
        if autotest:                                    # a test run: report and close
            print('AUTOTEST', 'ok' if ok else 'failed', text)
            root.after(int(os.environ.get('VSAV2E_BUILDER_AUTOTEST_HOLD', '300')), root.destroy)
            return
        (messagebox.showinfo if ok else messagebox.showerror)('vsav2e builder', text)

    root.after(100, poll)
    # VSAV2E_BUILDER_AUTOTEST="ROM_FOLDER|OUTPUT_FOLDER": fills the folders and builds by itself
    autotest = os.environ.get('VSAV2E_BUILDER_AUTOTEST')
    if autotest:
        rom_folder.set(autotest.split('|')[0])
        output_folder.set(autotest.split('|')[1])
        root.after(500, start)
    root.mainloop()


def main():
    if '--cli' in sys.argv:
        arguments = [argument for argument in sys.argv[1:] if argument != '--cli']
        if len(arguments) != 2:
            sys.exit(__doc__)
        run_build(arguments[0], arguments[1], print)
        return
    window()


if __name__ == '__main__':
    main()
