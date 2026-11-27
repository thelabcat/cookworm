"""Smoke test the built Cookworm EXE. Fails loudly if anything is off.

Usage: python .github/scripts/smoke_test_exe.py dist-exe/cookworm-win-x86_64.exe

1. Runs the EXE in command line mode on a tiny fake game folder, with no
   internet and with no NLTK data folder anywhere but inside the EXE, and checks
   that it wrote the right definitions. This proves wordnet and the word
   frequency list were bundled and are found at run time.
   (The EXE is windowed, so it has no console output. We check the files.)
2. On Windows, starts the EXE as a GUI and checks that the Cookworm window
   really opens.

S.D.G.
"""

import os
import subprocess
import sys
import tempfile
import time

CR_LF = "\r\n"


def fresh_env(home: str) -> dict:
    """An environment with no internet, and no NLTK data outside the EXE"""
    env = dict(os.environ)
    env.pop("NLTK_DATA", None)
    for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"):
        env[key] = home
    # Downloads go through a proxy that is not there, so they fail fast
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env[key] = "http://127.0.0.1:9"
    env.pop("NO_PROXY", None)
    env.pop("no_proxy", None)
    return env


def read(path: str) -> str:
    with open(path, encoding="iso 8859-15") as f:
        return f.read()


def cli_test(exe: str, home: str) -> None:
    game = os.path.join(home, "game")
    os.makedirs(game)
    # "aardvark" is rare and has a wordnet definition. "house" is very common.
    # If the frequency list was missing, every word would count as rare and
    # house would get defined too.
    with open(os.path.join(game, "wordlist.txt"), "w", encoding="iso 8859-15", newline="") as f:
        f.write("aardvark" + CR_LF + "house" + CR_LF)
    with open(os.path.join(game, "popdefs.txt"), "w", encoding="iso 8859-15", newline="") as f:
        f.write(CR_LF)

    result = subprocess.run(
        [exe, "-P", game, "-D"],
        env=fresh_env(home),
        capture_output=True,
        timeout=180,
    )
    print("auto-define exit code:", result.returncode)
    popdefs = read(os.path.join(game, "popdefs.txt"))
    print("popdefs.txt now holds:", repr(popdefs))

    assert result.returncode == 0, "The EXE exited with an error"
    assert popdefs.startswith("AARDVARK\t("), "aardvark was not auto-defined: wordnet is missing or broken"
    assert "termites" in popdefs, "aardvark's definition is not the wordnet one"
    assert "HOUSE" not in popdefs, "house was defined: the word frequency list is missing or broken"
    assert not os.path.exists(os.path.join(home, "nltk_data")), "The EXE downloaded wordnet instead of using its own copy"
    print("CLI test passed: wordnet and word frequencies both work offline.")


def window_titles() -> list:
    """Titles of all visible top level windows (Windows only)"""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    titles = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def collect(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                titles.append(buf.value)
        return True

    user32.EnumWindows(collect, 0)
    return titles


def gui_test(exe: str, home: str) -> None:
    game = os.path.join(home, "game")
    proc = subprocess.Popen([exe, "-P", game], env=fresh_env(home))
    try:
        deadline = time.time() + 60
        seen = []
        while time.time() < deadline:
            time.sleep(2)
            seen = window_titles()
            if any(t in ("Cookworm", "*Cookworm") for t in seen):
                print("GUI test passed: the Cookworm window opened.")
                return
            assert proc.poll() is None, "The EXE exited before its window opened"
        raise AssertionError("No Cookworm window after 60 s. Visible windows: " + repr(seen))
    finally:
        # Kill the whole tree: onefile EXEs start a child process
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            proc.kill()


def main(exe: str) -> None:
    exe = os.path.abspath(exe)
    assert os.path.exists(exe), "No EXE at " + exe
    print("Testing", exe, os.path.getsize(exe), "bytes")
    with tempfile.TemporaryDirectory() as home:
        cli_test(exe, home)
        if os.name == "nt":
            gui_test(exe, home)
        else:
            print("Not Windows: skipping the GUI test.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
