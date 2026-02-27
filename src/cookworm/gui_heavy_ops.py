#!/ur/bin/env python3
"""Cookworm GUI heavy operations

Functions to be run via the main window's tread_process() method.

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

import tkinter as tk
from typing import TextIO
from . import utils


def __parse_alpha_file(self: tk.Tk, f: TextIO):
    """Read a text file containing a human-readable list of words,
        close it, and filter the result to alpha-only words.

    Args:
        self (tk.Tk): The main GUI.
        f (TextIO): The file object the user has selected

    Returns:
        words (list): The list of alpha-only words from the file.
            Returns empty list if cancelled."""

    # Read and close the file, splitting into words by whitespace
    if not f:  # The user cancelled file selection
        return []
    self.status_text = "Reading file..."
    listed_words = f.read().strip().lower().split()
    f.close()

    # There were no words
    if not listed_words:
        self.op_errors.put((
            "Invalid file",
            "Did not find any words in file.",
            ))
        return []

    # Filter out duplicates
    self.status_text = "Filtering out duplicates in file..."
    nodupe_words = set(listed_words)
    dupe_count = len(listed_words) - len(nodupe_words)
    if dupe_count:
        self.op_warnings.put((
            "Some duplicates in file",
            f"The file had {dupe_count:,} duplicate listings in itself.",
            ))

    # filter file to only alpha words
    self.status_text = "Filtering to alpha-only words..."
    alpha_words = [
        word for word in nodupe_words if word.isalpha()
    ]
    nonalpha_count = len(nodupe_words) - len(alpha_words)

    # There was no text besides non-alpha symbols
    if not alpha_words:
        self.op_errors.put((
            "Invalid file",
            "File did not contain any alpha-only words.",
            ))
        return []

    # There were some non-alpha words
    if nonalpha_count:
        self.op_warnings.put((
            "Some invalid words",
            f"{nonalpha_count:,} words were rejected because they " +
            "contained non-alpha characters.",
        ))

    return alpha_words


def load_files(self: tk.Tk):
    """Load the wordlist and the popdefs, given the game_path attribute

    Args:
        self (tk.Tk): The main GUI."""

    # First, load the wordlist
    self.status_text = f"Loading {utils.WORDLIST_FILE}..."
    with open(
        self.wordlist_abs_path, encoding=utils.FILE_ENC
    ) as f:
        self.words = sorted(utils.unpack_wordlist(f.read().strip()))

    # Then, load the popdefs
    self.status_text = f"Loading {utils.POPDEFS_FILE}..."
    with open(
        self.popdefs_abs_path, encoding=utils.FILE_ENC
    ) as f:
        self.defs = dict(
            sorted(
                utils.unpack_popdefs(f.read().strip()).items()
                )
            )

    # Update the query list
    self.status_text = "Updating display..."

    # The files were just (re)loaded, so there are no unsaved changes
    self.unsaved_changes = False


def save_files(self: tk.Tk, backup: bool = False):
    """Attempt to save the worldist and popdefs.
        Reference self.unsaved_changes to know the result.

    Args:
        self (tk.Tk): The main GUI.
        backup (bool): Wether or not to copy the original files to a backup name.
            Defaults to False."""

    if backup:
        self.status_text = "Creating backup..."
        self.make_backup()

    # First, encode the wordlist
    self.status_text = f"Encoding {utils.WORDLIST_FILE}..."

    # Ensure that the wordlist encodes properly
    # Technically, this should never fail because a word should always be alpha
    try:
        encoded_wordlist = utils.pack_wordlist(sorted(self.words))\
            .encode(utils.FILE_ENC)
    except UnicodeEncodeError:
        # Failure to encode stops us from even trying to open the file
        self.op_errors.put((
            "File encoding error",
            "One or more word entries contain characters that couldn't" +
            f"be encoded in {utils.FILE_ENC}."
            ))
        return

    # Then, encode the popdefs
    self.status_text = f"Encoding {utils.POPDEFS_FILE}..."

    # Ensure that the popdefs encodes properly
    try:
        encoded_popdefs = utils.pack_popdefs(dict(sorted(self.defs.items())))\
            .encode(utils.FILE_ENC)
    except UnicodeEncodeError:
        # Failure to encode stops us from even trying to open the file
        self.op_errors.put((
            "File encoding error",
            "One or more definition entries contain characters that couldn't" +
            f"be encoded in {utils.FILE_ENC}."
            ))
        return

    self.status_text = "Writing to disk..."
    with open(self.wordlist_abs_path, "wb") as f:
        f.write(encoded_wordlist)
    with open(self.popdefs_abs_path, "wb") as f:
        f.write(encoded_popdefs)

    self.unsaved_changes = False  # All changes are now saved


def mass_add_words(self: tk.Tk, f: TextIO):
    """
    Add a whole file's worth of words

    Args:
        self (tk.Tk): The main GUI
        f (TextIO): The selected file
    """

    alpha_words = __parse_alpha_file(self, f)
    if not alpha_words:
        return

    # Filter to words we do not already have
    self.status_text = "Filtering to only new words..."
    new_words = [
        word for word in alpha_words
        if utils.binary_search(self.words, word) is None
    ]
    already_have = len(alpha_words) - len(new_words)

    # There were no words that we didn't already have
    if not new_words:
        self.op_infos.put((
            "Already have all words",
            f"All {len(alpha_words):,} alpha-only words are already " +
            "in the word list.",
        ))
        return

    # We already have some of the words
    if already_have:
        self.op_infos.put((
            "Already have some words",
            f"{already_have:,} words are already in the word list.",
        ))

    # Filter to words of valid lengths
    self.status_text = "Filtering out invalid length words..."
    new_lenvalid_words = [
        word for word in new_words if self.is_len_valid(word)
        ]
    len_invalid = len(new_words) - len(new_lenvalid_words)

    # There were no words of valid length
    if not new_lenvalid_words:
        self.op_errors.put((
            "Invalid word lengths",
            f"All {len(new_words):,} new words were rejected because " +
            f"they were not between {utils.WORD_LENGTH_MIN:,} and " +
            f"{utils.WORD_LENGTH_MAX:,} letters long.",
        ))
        return

    # There were some words of invalid length
    if len_invalid:
        self.op_infos.put((
            "Some invalid word lengths",
            f"{len_invalid:,} words were rejected because they were not " +
            f"between {utils.WORD_LENGTH_MIN:,} and {utils.WORD_LENGTH_MAX:,} " +
            "letters long.",
        ))

    # Add the new words
    self.status_text = "Combining lists..."
    self.words += new_lenvalid_words
    self.words.sort()

    # Update the query display
    self.update_query()

    # There are now major unsaved changes
    self.op_infos.put((
        "Words added",
        f"Added {len(new_lenvalid_words):,} new words to the word list."
    ))

    # Mass changes were made, mark as unsaved
    self.unsaved_changes = True


def mass_delete_words(self: tk.Tk, f: TextIO):
    """Delete a whole file's worth of words

    Args:
        self (tk.Tk): The main GUI
        f (TextIO): The selected file"""

    # Get the list of words to delete
    del_words = __parse_alpha_file(self, f)
    if not del_words:
        return

    # Filter down to words we actually have
    self.status_text = "Finding words we do have..."
    old_words = [
        word for word in del_words
        if utils.binary_search(self.words, word) is not None
    ]
    dont_have = len(del_words) - len(old_words)

    # We don't have any of the words in the list
    if not old_words:
        self.op_infos.put((
            "Don't have any of the words",
            f"None of the {len(del_words):,} words are in the word list.",
        ))
        return

    # We only have some of the words in the list
    if dont_have:
        self.op_infos.put((
            "Don't have some words",
            f"{dont_have:,} of the words are not in the wordlist.",
        ))

    # Perform the deletion
    self.status_text = "Deleting..."
    for word in old_words:
        self._delete_word(word)

    # Words that were in the query may have been deleted, so update it.
    self.update_query()

    # There are now major unsaved changes
    self.op_infos.put((
        "Words deleted",
        f"Removed {len(old_words):,} words from the word list.",
    ))

    # Mass changes were made, mark as unsaved
    self.unsaved_changes = True


def del_invalid_len_words(self: tk.Tk):
    """Remove all words of invalid length from the wordlist

    Args:
        self (tk.Tk): The main GUI."""

    # Comprehensively filter to words of invalid length
    invalid = [word for word in self.words if not self.is_len_valid(word)]

    # If all words were of valid length, notify the user
    if not invalid:
        self.op_infos.put((
            "No invalid length words",
            f"All words are already between {utils.WORD_LENGTH_MIN:,} " +
            f"and {utils.WORD_LENGTH_MAX:,} letters long.",
        ))
        return

    # Perform the deletion
    for word in invalid:
        self._delete_word(word)

    # Update the query display
    self.update_query()

    # There are now mass unsaved changes
    self.op_infos.put((
        "Invalid length words deleted",
        f"Found and deleted {len(invalid):,} words of invalid length " +
        "from the word list."
    ))

    # Mass changes were made, mark as unsaved
    self.unsaved_changes = True


def del_orphaned_defs(self: tk.Tk):
    """Find and delete any orphaned definitions

    Args:
        self (tk.Tk): The main GUI."""

    self.status_text = "Finding orphaned definitions..."
    orphaned = [
        word for word in self.defs if utils.binary_search(self.words, word) is None
    ]

    # No orphaned definitions found
    if not orphaned:
        self.op_infos.put((
            "No orphaned definitions",
            "All recorded definitions have a word they are paired with.",
        ))
        return

    # Delete the orphaned definitions
    self.status_text = "Deleting orphans..."
    for o in orphaned:
        del self.defs[o]

    # There are now mass unsaved changes
    self.op_infos.put((
        "Orphaned definitions deleted",
        f"Found and deleted {len(orphaned):,} orphaned definitions.",
    ))

    # Mass changes were made, mark as unsaved
    self.unsaved_changes = True


def del_badenc_defs(self: tk.Tk):
    """Find and delete any unencodable definitions

    Args:
        self (tk.Tk): The main GUI."""
    self.status_text = "Finding and deleting unencodable definitions..."
    found = 0
    for word, definition in self.defs.copy().items():
        try:
            definition.encode(utils.FILE_ENC)
        except UnicodeEncodeError:
            del self.defs[word]
            found += 1

    # No unencodable definitions found
    if not found:
        self.op_infos.put((
            "No unencodable definitions",
            f"All definitions can encode properly to {utils.FILE_ENC}.",
        ))
        return

    # There are now mass unsaved changes
    self.op_infos.put((
        "Unencodable definitions deleted",
        f"Found and deleted {found} non {utils.FILE_ENC} encodable " +
        "definitions.",
    ))

    # Mass changes were made, mark as unsaved
    self.unsaved_changes = True


def del_dupe_words(self: tk.Tk):
    """Delete any duplicate word listings

    Args:
        self (tk.Tk): The main GUI."""

    self.status_text = "Searching for duplicates..."
    unduped = set(self.words)  # Sets don't have duplicate entries
    dupe_count = len(self.words) - len(unduped)

    # No duplicates
    if not dupe_count:
        self.op_infos.put((
            "No duplicates found",
            "All words are only listed once.",
            ))
        return

    # There were duplicates, so now convert and sort the set
    self.status_text = "Ordering unduplicated set..."
    self.words = list(unduped)
    self.words.sort()

    # There are now mass unsaved changes.
    self.op_infos.put((
        "Duplicates deleted",
        f"Found and removed {dupe_count:,} duplicate listings",
    ))

    # Mass changes were made, mark as unsaved
    self.unsaved_changes = True


def mass_auto_define(self: tk.Tk):
    """Find all words below the usage threshold, and try to define them

    Args:
        self (tk.Tk): The main GUI."""

    if not utils.HAVE_WORDNET:
        self.op_errors.put((
            "No dictionary",
            "We need to download the NLTK wordnet English dictionary " +
            "for auto-defining. Please connect to the internet, then " +
            "restart the application.",
        ))
        return

    # Find all words below the usage threshold and without a definition
    self.status_text = "Finding undefined rare words..."
    defined_words = tuple(self.defs)
    words_to_define = [
        word for word in self.words
        if utils.get_word_usage(word) < utils.RARE_THRESH
        and utils.binary_search(defined_words, word) is None
    ]
    total = len(words_to_define)

    # Nothing to do?
    if not total:
        self.op_infos.put((
            "No undefined rare words",
            "All words with a usage metric below the threshold already " +
            "have a popdef.",
        ))
        return

    # Attempt to define all the words
    self.status_text = f"Auto-defining {total:,} words..."
    fails = 0
    for word in words_to_define:
        result, success = utils.build_auto_def(word)
        if success:
            self.defs[word] = result
        else:
            fails += 1

    if fails == total:
        self.op_errors.put((
            "No definitions found",
            f"Failed to define any of the {total:,} undefined " +
            "rare words found.",
        ))
        return

    # If there were successes, sort the updated popdefs alphabetically
    self.status_text = "Sorting popdefs..."
    self.defs = dict(sorted(self.defs.items()))

    if fails:
        self.op_warnings.put((
            "Some definitions not found",
            f"Failed to define {fails:,} of the {total:,} undefined " +
            "rare words found.",
        ))

    # There are now unsaved changes
    self.op_infos.put((
        "Operation complete",
        f"Auto-defined {total - fails:,} words.",
    ))

    # Mass changes were made, mark as unsaved
    self.unsaved_changes = True
