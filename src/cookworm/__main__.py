# !/usr/bin/env python3
"""Cookworm - Main execution handle

Copyright 2026 Wilbur Jaywright d.b.a. Marswide BGL.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

S.D.G.
"""

import argparse
from glob import glob
from os import path as op
from sys import stderr, stdin
from warnings import warn
from .gui import main as gui_main
from . import config_io, operations, utils, info


class EditorCLI:
    """CLI editor host interface"""

    def __init__(self):
        """CLI editor host interface"""

        self.words: list[str] = None
        """The ordered word list"""

        self.defs: dict[str, str] = None
        """Pop-up definitions"""

        self.unsaved_changes: bool = False
        """Wether or not changes have been made to the files that need saving"""

        self.parser = argparse.ArgumentParser(
            description=f"The BookWorm Deluxe wordlist and popdefs editor. Version {info.PROGRAM_VER}, licensed under {info.LICENSE_NAME}. Project homepage: {info.URL.homepage}",
            epilog="NOTE: CLI options are run in documented order, not provided order. S.D.G.",
            )

        self.status_code: int = self.parse_args()

    def set_status_text(self, new: str) -> None:
        """
        Set the current operations message (thread-safe)

        Args:
            new (str): The new status text to show.
        """
        print("STATUS:", new)

    def op_show_message(self, title: str, message: str, level: int = 0) -> None:
        """
        Show information from an operation (thread-safe)

        Args:
            title (str): The dialog title.
            message (str): What to say.
            level (int): 0 for info, 1 for warning, 2 for error.
        """
        (print, warn, lambda s: stderr.write(s + "\n"))[level](f"{title}: {message}")

    def parse_args(self):
        """Parse all CLI arguments and act accordingly"""
        self.parser.add_argument(
            "-a", "--add",
            nargs="*",
            type=str,
            default=[],
            help="Add the given words to the list",
            )
        self.parser.add_argument(
            "-A", "--add-file",
            nargs="+",
            type=str,
            default=[],
            help="Add the given file(s) of words to the list, '-' for stdin",
            )
        self.parser.add_argument(
            "-x", "--delete",
            nargs="*",
            type=str,
            default=[],
            help="Remove the given words from the list",
            )
        self.parser.add_argument(
            "-X", "--delete-file",
            nargs="+",
            type=str,
            default=[],
            help="Remove the given file(s) of words from the list, '-' for stdin",
            )
        self.parser.add_argument(
            "-d", "--define",
            nargs="*",
            type=str,
            default=None,
            help="Define a word. Pass just the word to get its definition, pass the word then the definition to set it.",
            )
        self.parser.add_argument(
            "-D", "--auto-define",
            nargs="*",
            type=str,
            default=None,
            help="Automatically define specified words. Pass no arguments to define all rare ones",
            )
        self.parser.add_argument(
            "-k", "--remove-def",
            type=str,
            help="Remove the popup definition for the given word, because it is widely known",
            )
        self.parser.add_argument(
            "-o", "--orphan-fix",
            action="store_true",
            help="Find and delete all orphaned definitions",
            )
        # -s silence benign errors: allow "it already is that way" without raising an error.
        self.parser.add_argument(
            "-l", "--length-limit",
            action="store_true",
            help="Find and delete all words of invalid length",
            )
        self.parser.add_argument(
            "-e", "--encoding-check",
            action="store_true",
            help="Find and delete all unencodable definitions",
            )
        self.parser.add_argument(
            "-P", "--game-path",
            type=str,
            help="(CLI and GUI) Manually specify game program folder location",
            )
        self.parser.add_argument(
            "-b", "--backup",
            action="store_true",
            help="Create backup of game files, defaults to yes if they are older than the program",
            )
        self.parser.add_argument(
            "-p", "--parser",
            nargs="?",
            type=str,
            default=None,
            help="Work directly from a wordlist file, and parse it to an output. No argument to read stdin",
            )
        self.parser.add_argument(
            "-u", "--unparser",
            nargs="?",
            type=str,
            default=None,
            help="Work directly from a plain words file, and unparse it to a wordlist output. No argument to read stdin",
            )
        self.parser.add_argument(
            "outfile",
            nargs="?",
            type=str,
            default=None,
            help="Output file for raw (un)parser mode. Defaults to stdout",
            )

        args = self.parser.parse_args()

        assert not ((args.parser is not None) and (args.unparser is not None)), "Cannot parse and unparse at the same time!"
        raw_parser_mode = (args.parser is not None) or (args.unparser is not None)

        config_io.game_path_specified = args.game_path  # Could still be None, which is fine

        cli_mode = False
        for cli_option in (
            args.add,
            args.add_file,
            args.delete,
            args.delete_file,
            args.define is not None,
            args.auto_define is not None,
            args.remove_def,
            args.orphan_fix,
            args.length_limit,
            args.encoding_check,
            args.backup,
        ):
            if cli_option:
                cli_mode = True
                break

        assert not (raw_parser_mode and cli_mode), "Cannot use raw parser mode and other CLI options."

        # Raw parser mode
        if raw_parser_mode:
            # If an input file was not named but we are this far, use stdin
            infile_name = args.parser or args.unparser
            if not infile_name:
                intext = stdin.read().strip()
            else:
                # The path does not work directly, but maybe it is a pattern
                if not op.exists(infile_name):
                    infile_glob = glob(infile_name)
                    assert len(infile_glob) == 1, "Input file pattern must match exactly one file"
                    infile_name = infile_glob[0]
                with open(infile_name, encoding=utils.FILE_ENC) as f:
                    intext = f.read().strip()

            if args.parser is not None:
                outtext = utils.DOS_LINE_ENDING.join(utils.unpack_wordlist(intext))
            else:
                outtext = utils.pack_wordlist(intext.splitlines())

            if args.outfile:
                with open(args.outfile, encoding=utils.FILE_ENC) as f:
                    f.write(outtext)
            else:
                print(outtext)

            return 0

        # GUI mode
        if not (raw_parser_mode or cli_mode):
            return gui_main()

        # CLI mode
        self.__config = config_io.load_config()

        # Load the game files
        assert utils.is_game_path_valid(self.game_path), f"Could not find game files at '{self.game_path}', try specifying the game path manually"
        operations.load_files(self)

        # Add any directly provided words
        for word in args.add:
            operations.add_word(self, word)

        # Accept one or more files of words to add
        for filepattern in args.add_file:
            # Parse glob patterns
            found = glob(filepattern)
            if not found:
                self.op_show_message("Invalid file pattern", f"No files found that match '{filepattern}'", 2)
            for filename in found:
                print("Got file of words to add:", filename)
                with open(filename, encoding=utils.FILE_ENC) as f:
                    operations.mass_add_words(self, f)

        # Delete any directly provided words
        for word in args.delete:
            operations.delete_word(self, word, quiet=False)

        # Accept one or more files of words to delete
        for filepattern in args.delete_file:
            # Parse glob patterns
            found = glob(filepattern)
            if not found:
                self.op_show_message("Invalid file pattern", f"No files found that match '{filepattern}'", 2)
            for filename in found:
                print("Got file of words to delete:", filename)
                with open(filename, encoding=utils.FILE_ENC) as f:
                    operations.mass_delete_words(self, f)

        # Make sure the user doesn't have this flag with nothing
        # None means they didn't have the flag
        assert args.define or args.define is None, "Must pass word to define"

        # Either print the definition of a word, or set it to the one provided
        if args.define:
            assert len(args.define) in (1, 2), "Can only define one word at a time"
            word = args.define[0]
            assert utils.binary_search(self.words, word) is not None, f"Cannot define word '{word}' before it is added"

            # Print existing definition
            if len(args.define) == 1:
                print(self.defs.get(word))

            # Save new definition
            else:
                new_def = args.define[1]
                new_def.encode(utils.FILE_ENC)  # Ensure encodability
                self.defs[word] = new_def
                self.unsaved_changes = True

            self.defs = dict(sorted(self.defs.items()))

        # Auto-define specified words, or all rare words
        if args.auto_define is not None:
            assert utils.HAVE_WORDNET, "We need to download the NLTK wordnet English dictionary " + \
                "for auto-defining. Please connect to the internet, then " + \
                "restart the application."

            # Specific words selected for auto-define
            if args.auto_define:
                # Ensure all words exist before attempting to auto-define
                for word in args.auto_define:
                    assert utils.binary_search(self.words, word) is not None, f"Cannot define word '{word}' before it is added"
                for word in args.auto_define:
                    result, success = utils.build_auto_def(word)
                    if success:
                        self.defs[word] = result
                        print(word, ":", result)
                    else:
                        self.op_show_message(
                            "Auto-define failure",
                            f"Could not find a definition for word '{word}'",
                            2,
                            )
                self.defs = dict(sorted(self.defs.items()))
                self.unsaved_changes = True

            # All words auto-define
            else:
                operations.mass_auto_define(self)

        # Delete a definition of one word if requested
        # TODO: Should this accept multiple words?
        if args.remove_def:
            assert args.remove_def in self.defs, f"No definition saved for `{args.remove_def}`, so cannot remove it."
            del self.defs[args.remove_def]
            self.unsaved_changes = True

        # Miscellaneous repair utilities
        if args.orphan_fix:
            operations.del_orphaned_defs(self)

        if args.length_limit:
            operations.del_invalid_len_words(self)

        if args.encoding_check:
            operations.del_badenc_defs(self)

        # Save changes on exit
        if self.unsaved_changes:
            operations.save_files(self, backup=args.backup or min((
                op.getmtime(self.wordlist_abs_path),
                op.getmtime(self.popdefs_abs_path),
            )) < info.INITIAL_COMMIT_TIMESTAMP)

        return 0

    @property
    def game_path(self):
        """The path to the game program folder"""
        return self.__config["gamePath"]

    @property
    def wordlist_abs_path(self) -> str:
        """The absolute path of the wordlist file"""
        return op.join(self.game_path, utils.WORDLIST_FILE)

    @property
    def popdefs_abs_path(self) -> str:
        """The absolute path of the popdefs file"""
        return op.join(self.game_path, utils.POPDEFS_FILE)


def main() -> int:
    """The CLI and GUI frontend, returning an exit code"""
    e = EditorCLI()
    return e.status_code


if __name__ == "__main__":
    exit(main())
