#!/usr/bin/env python3
"""Cookworm - Help Information

Various bits of program information

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

from os import path as op
import time

# The path of the script file's containing folder
OP_PATH = op.dirname(__file__)

PROGRAM_NAME = "Cookworm"
PROGRAM_VER = "4.1.0"
ICON_PATH = op.join(OP_PATH, "cookworm.png")
LICENSE_NAME = "Apache License version 2.0"

INITIAL_COMMIT_DATE_STR = "Wed Mar 27 13:07:57 2024 -0400"
COMMIT_DATE_PARSEFORM = "%a %b %d %H:%M:%S %Y %z"
INITIAL_COMMIT_TIMESTAMP = time.mktime(
    time.strptime(INITIAL_COMMIT_DATE_STR, COMMIT_DATE_PARSEFORM)
)


class URL:
    """URLs to various places"""

    homepage = "https://github.com/thelabcat/cookworm"
    how_to_use = homepage + "?tab=readme-ov-file#usage"
    report_issue = homepage + "/issues"
    license = "https://www.apache.org/licenses/LICENSE-2.0"


if not op.exists(ICON_PATH):
    print("Icon path does not exist!")
