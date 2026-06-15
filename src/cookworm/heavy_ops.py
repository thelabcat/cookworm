#!/ur/bin/env python3
"""Cookworm heavy operations

Functions that take a long time to complete, and should be threaded if running via GUI

Copyright 2025 Wilbur Jaywright d.b.a. Marswide BGL.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

S.D.G."""

from typing import Protocol, TextIO
from . import utils


class HostInterface(Protocol):
    """Type hint for host interfaces which can call these functions"""

    def set_status_text(self, new: str) -> None: ...
    """
    Set the current operations message (thread-safe)

    Args:
        new (str): The new status text to show.
    """

    def op_show_message(self, title: str, message: str, level: int = 0) -> None: ...
    """
    Show information from an operation (thread-safe)

    Args:
        title (str): The dialog title.
        message (str): What to say.
        level (int): 0 for info, 1 for warning, 2 for error.
    """

    def make_backup(self) -> bool: ...
    """
    Save a backup of the files, with a timestamp.

    Returns:
        success (bool): Wether or not we were able to backup.
    """

    def _delete_word(self, word: str, quiet=True): ...
    """
    Delete a word from our wordlist and popdefs

    Args:
        word (str): The word to delete.
        quiet (bool): If the word doesn't exist, this silences an error.
            Defaults to True, silence the error.
    """

    words: list[str]
    """The ordered word list"""

    defs: dict[str, str]
    """Pop-up definitions"""

    wordlist_abs_path: str
    """Path to wordlist.txt"""

    popdefs_abs_path: str
    """Path to popdefs.txt"""

    unsaved_changes: bool
    """Wether or not changes have been made to the files that need saving"""


def __parse_alpha_file(host: HostInterface, f: TextIO):
    """Read a text file containing a human-readable list of words,
        close it, and filter the result to alpha-only words.

    Args:
        host: The main interface object.
        f (TextIO): The file object the user has selected

    Returns:
        words (list): The list of alpha-only words from the file.
            Returns empty list if cancelled."""

    # Read and close the file, splitting into words by whitespace
    if not f:  # The user cancelled file selection
        return []
    host.set_status_text("Reading file...")
    listed_words = f.read().strip().lower().split()
    f.close()

    # There were no words
    if not listed_words:
        host.op_show_message(
            "Invalid file",
            "Did not find any words in file.",
            2,
            )
        return []

    # Filter out duplicates
    host.set_status_text("Filtering out duplicates in file...")
    nodupe_words = set(listed_words)
    dupe_count = len(listed_words) - len(nodupe_words)
    if dupe_count:
        host.op_show_message(
            "Some duplicates in file",
            f"The file had {dupe_count:,} duplicate listings in itself.",
            1,
            )

    # filter file to only alpha words
    host.set_status_text("Filtering to alpha-only words...")
    alpha_words = [
        word for word in nodupe_words if word.isalpha()
    ]
    nonalpha_count = len(nodupe_words) - len(alpha_words)

    # There was no text besides non-alpha symbols
    if not alpha_words:
        host.op_show_message(
            "Invalid file",
            "File did not contain any alpha-only words.",
            2,
            )
        return []

    # There were some non-alpha words
    if nonalpha_count:
        host.op_show_message(
            "Some invalid words",
            f"{nonalpha_count:,} words were rejected because they " +
            "contained non-alpha characters.",
            1,
            )

    return alpha_words


def load_files(host: HostInterface):
    """Load the wordlist and the popdefs, given the game_path attribute

    Args:
        host: The main interface object."""

    # First, load the wordlist
    host.set_status_text(f"Loading {utils.WORDLIST_FILE}...")
    with open(
        host.wordlist_abs_path, encoding=utils.FILE_ENC
    ) as f:
        host.words = sorted(utils.unpack_wordlist(f.read().strip()))

    # Then, load the popdefs
    host.set_status_text(f"Loading {utils.POPDEFS_FILE}...")
    with open(
        host.popdefs_abs_path, encoding=utils.FILE_ENC
    ) as f:
        host.defs = dict(
            sorted(
                utils.unpack_popdefs(f.read().strip()).items()
                )
            )

    # Update the query list
    host.set_status_text("Updating display...")

    # The files were just (re)loaded, so there are no unsaved changes
    host.unsaved_changes = False


def save_files(host: HostInterface, backup: bool = False):
    """Attempt to save the worldist and popdefs.
        Reference host.unsaved_changes to know the result.

    Args:
        host: The main interface object.
        backup (bool): Wether or not to copy the original files to a backup name.
            Defaults to False."""

    if backup:
        host.set_status_text("Creating backup...")
        host.make_backup()

    # First, encode the wordlist
    host.set_status_text(f"Encoding {utils.WORDLIST_FILE}...")

    # Ensure that the wordlist encodes properly
    # Technically, this should never fail because a word should always be alpha
    try:
        encoded_wordlist = utils.pack_wordlist(sorted(host.words))\
            .encode(utils.FILE_ENC)
    except UnicodeEncodeError:
        # Failure to encode stops us from even trying to open the file
        host.op_show_message(
            "File encoding error",
            "One or more word entries contain characters that couldn't" +
            f"be encoded in {utils.FILE_ENC}.",
            2,
            )
        return

    # Then, encode the popdefs
    host.set_status_text(f"Encoding {utils.POPDEFS_FILE}...")

    # Ensure that the popdefs encodes properly
    try:
        encoded_popdefs = utils.pack_popdefs(dict(sorted(host.defs.items())))\
            .encode(utils.FILE_ENC)
    except UnicodeEncodeError:
        # Failure to encode stops us from even trying to open the file
        host.op_show_message(
            "File encoding error",
            "One or more definition entries contain characters that couldn't" +
            f"be encoded in {utils.FILE_ENC}.",
            2,
            )
        return

    host.set_status_text("Writing to disk...")
    with open(host.wordlist_abs_path, "wb") as f:
        f.write(encoded_wordlist)
    with open(host.popdefs_abs_path, "wb") as f:
        f.write(encoded_popdefs)

    host.unsaved_changes = False  # All changes are now saved


def mass_add_words(host: HostInterface, f: TextIO):
    """
    Add a whole file's worth of words

    Args:
        self (tk.Tk): The main GUI
        f (TextIO): The selected file
    """

    alpha_words = __parse_alpha_file(host, f)
    if not alpha_words:
        return

    # Filter to words we do not already have
    host.set_status_text("Filtering to only new words...")
    new_words = [
        word for word in alpha_words
        if utils.binary_search(host.words, word) is None
    ]
    already_have = len(alpha_words) - len(new_words)

    # There were no words that we didn't already have
    if not new_words:
        host.op_show_message(
            "Already have all words",
            f"All {len(alpha_words):,} alpha-only words are already " +
            "in the word list.",
        )
        return

    # We already have some of the words
    if already_have:
        host.op_show_message(
            "Already have some words",
            f"{already_have:,} words are already in the word list.",
        )

    # Filter to words of valid lengths
    host.set_status_text("Filtering out invalid length words...")
    new_lenvalid_words = [
        word for word in new_words if utils.is_len_valid(word)
        ]
    len_invalid = len(new_words) - len(new_lenvalid_words)

    # There were no words of valid length
    if not new_lenvalid_words:
        host.op_show_message(
            "Invalid word lengths",
            f"All {len(new_words):,} new words were rejected because " +
            f"they were not between {utils.WORD_LENGTH_MIN:,} and " +
            f"{utils.WORD_LENGTH_MAX:,} letters long.",
            2,
            )
        return

    # There were some words of invalid length
    if len_invalid:
        host.op_show_message(
            "Some invalid word lengths",
            f"{len_invalid:,} words were rejected because they were not " +
            f"between {utils.WORD_LENGTH_MIN:,} and {utils.WORD_LENGTH_MAX:,} " +
            "letters long.",
        )

    # Add the new words
    host.set_status_text("Combining lists...")
    host.words += new_lenvalid_words
    host.words.sort()

    # There are now major unsaved changes
    host.op_show_message(
        "Words added",
        f"Added {len(new_lenvalid_words):,} new words to the word list."
    )

    # Mass changes were made, mark as unsaved
    host.unsaved_changes = True


def mass_delete_words(host: HostInterface, f: TextIO):
    """Delete a whole file's worth of words

    Args:
        self (tk.Tk): The main GUI
        f (TextIO): The selected file"""

    # Get the list of words to delete
    del_words = __parse_alpha_file(host, f)
    if not del_words:
        return

    # Filter down to words we actually have
    host.set_status_text("Finding words we do have...")
    old_words = [
        word for word in del_words
        if utils.binary_search(host.words, word) is not None
    ]
    dont_have = len(del_words) - len(old_words)

    # We don't have any of the words in the list
    if not old_words:
        host.op_show_message(
            "Don't have any of the words",
            f"None of the {len(del_words):,} words are in the word list.",
        )
        return

    # We only have some of the words in the list
    if dont_have:
        host.op_show_message(
            "Don't have some words",
            f"{dont_have:,} of the words are not in the wordlist.",
        )

    # Perform the deletion
    host.set_status_text("Deleting...")
    for word in old_words:
        host._delete_word(word)

    # There are now major unsaved changes
    host.op_show_message(
        "Words deleted",
        f"Removed {len(old_words):,} words from the word list.",
    )

    # Mass changes were made, mark as unsaved
    host.unsaved_changes = True


def del_invalid_len_words(host: HostInterface):
    """Remove all words of invalid length from the wordlist

    Args:
        host: The main interface object."""

    # Comprehensively filter to words of invalid length
    invalid = [word for word in host.words if not utils.is_len_valid(word)]

    # If all words were of valid length, notify the user
    if not invalid:
        host.op_show_message(
            "No invalid length words",
            f"All words are already between {utils.WORD_LENGTH_MIN:,} " +
            f"and {utils.WORD_LENGTH_MAX:,} letters long.",
        )
        return

    # Perform the deletion
    for word in invalid:
        host._delete_word(word)

    # There are now mass unsaved changes
    host.op_show_message(
        "Invalid length words deleted",
        f"Found and deleted {len(invalid):,} words of invalid length " +
        "from the word list."
    )

    # Mass changes were made, mark as unsaved
    host.unsaved_changes = True


def del_orphaned_defs(host: HostInterface):
    """Find and delete any orphaned definitions

    Args:
        host: The main interface object."""

    host.set_status_text("Finding orphaned definitions...")
    orphaned = [
        word for word in host.defs if utils.binary_search(host.words, word) is None
    ]

    # No orphaned definitions found
    if not orphaned:
        host.op_show_message(
            "No orphaned definitions",
            "All recorded definitions have a word they are paired with.",
        )
        return

    # Delete the orphaned definitions
    host.set_status_text("Deleting orphans...")
    for o in orphaned:
        del host.defs[o]

    # There are now mass unsaved changes
    host.op_show_message(
        "Orphaned definitions deleted",
        f"Found and deleted {len(orphaned):,} orphaned definitions.",
    )

    # Mass changes were made, mark as unsaved
    host.unsaved_changes = True


def del_badenc_defs(host: HostInterface):
    """Find and delete any unencodable definitions

    Args:
        host: The main interface object."""
    host.set_status_text("Finding and deleting unencodable definitions...")
    found = 0
    for word, definition in host.defs.copy().items():
        try:
            definition.encode(utils.FILE_ENC)
        except UnicodeEncodeError:
            del host.defs[word]
            found += 1

    # No unencodable definitions found
    if not found:
        host.op_show_message(
            "No unencodable definitions",
            f"All definitions can encode properly to {utils.FILE_ENC}.",
        )
        return

    # There are now mass unsaved changes
    host.op_show_message(
        "Unencodable definitions deleted",
        f"Found and deleted {found} non {utils.FILE_ENC} encodable " +
        "definitions.",
    )

    # Mass changes were made, mark as unsaved
    host.unsaved_changes = True


def del_dupe_words(host: HostInterface):
    """Delete any duplicate word listings

    Args:
        host: The main interface object."""

    host.set_status_text("Searching for duplicates...")
    unduped = set(host.words)  # Sets don't have duplicate entries
    dupe_count = len(host.words) - len(unduped)

    # No duplicates
    if not dupe_count:
        host.op_show_message(
            "No duplicates found",
            "All words are only listed once.",
            )
        return

    # There were duplicates, so now convert and sort the set
    host.set_status_text("Ordering unduplicated set...")
    host.words = list(unduped)
    host.words.sort()

    # There are now mass unsaved changes.
    host.op_show_message(
        "Duplicates deleted",
        f"Found and removed {dupe_count:,} duplicate listings",
    )

    # Mass changes were made, mark as unsaved
    host.unsaved_changes = True


def mass_auto_define(host: HostInterface):
    """Find all words below the usage threshold, and try to define them

    Args:
        host: The main interface object."""

    if not utils.HAVE_WORDNET:
        host.op_show_message(
            "No dictionary",
            "We need to download the NLTK wordnet English dictionary " +
            "for auto-defining. Please connect to the internet, then " +
            "restart the application.",
            2,
            )
        return

    # Find all words below the usage threshold and without a definition
    host.set_status_text("Finding undefined rare words...")
    defined_words = tuple(host.defs)
    words_to_define = [
        word for word in host.words
        if utils.get_word_usage(word) < utils.RARE_THRESH
        and utils.binary_search(defined_words, word) is None
    ]
    total = len(words_to_define)

    # Nothing to do?
    if not total:
        host.op_show_message(
            "No undefined rare words",
            "All words with a usage metric below the threshold already " +
            "have a popdef.",
        )
        return

    # Attempt to define all the words
    host.set_status_text(f"Auto-defining {total:,} words...")
    fails = 0
    for word in words_to_define:
        result, success = utils.build_auto_def(word)
        if success:
            host.defs[word] = result
        else:
            fails += 1

    if fails == total:
        host.op_show_message(
            "No definitions found",
            f"Failed to define any of the {total:,} undefined " +
            "rare words found.",
            2,
            )
        return

    # If there were successes, sort the updated popdefs alphabetically
    host.set_status_text("Sorting popdefs...")
    host.defs = dict(sorted(host.defs.items()))

    if fails:
        host.op_show_message(
            "Some definitions not found",
            f"Failed to define {fails:,} of the {total:,} undefined " +
            "rare words found.",
            1,
            )

    # There are now unsaved changes
    host.op_show_message(
        "Operation complete",
        f"Auto-defined {total - fails:,} words.",
    )

    # Mass changes were made, mark as unsaved
    host.unsaved_changes = True
