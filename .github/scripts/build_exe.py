"""Build the Cookworm Windows EXE with PyInstaller.

Usage (from the repo root, with the app, PyInstaller and the NLTK wordnet
dictionary already installed):

    python .github/scripts/build_exe.py cookworm-win-x86_64

The EXE lands in dist-exe/. Everything the app needs is bundled so it runs
with no internet: the window icon, the English word frequency list, and the
NLTK wordnet dictionary.

S.D.G.
"""

import os
import sys

import nltk
import PyInstaller.__main__
import wordfreq

REPO = os.getcwd()
SEP = os.pathsep  # PyInstaller wants SRC<SEP>DEST, and the separator is ; on Windows


def main(name: str) -> None:
    # The NLTK hook in pyinstaller-hooks-contrib copies every existing NLTK data
    # folder into the EXE, so make sure wordnet is really in one of them.
    found = ""
    for folder in nltk.data.path:
        corpora = os.path.join(folder, "corpora")
        if os.path.exists(os.path.join(corpora, "wordnet.zip")) or os.path.isdir(os.path.join(corpora, "wordnet")):
            found = folder
            break
    if not found:
        sys.exit("The NLTK wordnet dictionary was not found in any NLTK data folder: " + repr(nltk.data.path))
    print("NLTK wordnet found in", found)

    args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", name,
        "--icon", os.path.join(REPO, "src", "cookworm", "cookworm.ico"),
        # The window icon, loaded next to info.py
        "--add-data", os.path.join(REPO, "src", "cookworm", "cookworm.png") + SEP + "cookworm",
        "--hidden-import", "cookworm.__main__",
        "--paths", os.path.join(REPO, "src"),
        "--distpath", os.path.join(REPO, "dist-exe"),
        "--workpath", os.path.join(REPO, "build-exe"),
        "--specpath", os.path.join(REPO, "build-exe"),
    ]

    # Only the English word frequency lists. The whole wordfreq data folder is
    # about 60 MB of other languages that this app never reads.
    data_dir = str(wordfreq.DATA_PATH)
    for filename in ("large_en.msgpack.gz", "small_en.msgpack.gz"):
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            sys.exit("Missing wordfreq data file " + path)
        args += ["--add-data", path + SEP + "wordfreq/data"]

    args.append(os.path.join(REPO, "src", "cookworm_exe_wrapper.pyw"))
    print("PyInstaller args:", args)
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
