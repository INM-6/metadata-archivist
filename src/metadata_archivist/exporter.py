#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata file saver example.
Tested with Python 3.8.10
Author: Jose V.

"""

from pathlib import Path

from . import exporting_procedures as eprc


def formats() -> list:
    """
    Get function for acceptable metadata formats.

    Returns:
        List of acceptable metadata formats.
    """

    return list(eprc.PROCEDURES.keys())


def check_format(form: str) -> str:
    """
    Checks provided format for metadata file, to avoid ambiguity,
    upper case strings are used.
    Acceptable formats are stored in SAVE_FORMATS.
    Stops execution if format is incorrect.

    Args:
        form: String target format.

    Returns:
        String target format (upper cased).
    """

    form = form.upper()

    assert form in eprc.PROCEDURES, f'''Incorrect format: {form}.
    Acceptable formats: {form()}'''

    return form


def export(metadata: dict,
           outfile: Path,
           form: str = "JSON",
           verb: bool = False):
    """
    Saves metadata to file using given format.
    This function is called from the main python file where the check_format
    was previously used.
    No additional check needed.

    Args:
        metadata: Dictionary containing metadata.
        outfile: Path object to target file.
        form: String target form.
        verb: Boolean to control verbose output.
    """

    if verb:
        print(f"Saving metadata to file: {outfile}")

    eprc.PROCEDURES[form](metadata, outfile)

    if verb:
        print("Saved metadata file.")
