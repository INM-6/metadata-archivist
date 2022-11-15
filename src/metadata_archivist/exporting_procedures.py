#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata file save rules example.
Tested with Python 3.8.10
Author: Jose V.

"""

# import odml
import json

from datetime import datetime
from pathlib import Path


def export_as_json(metadata: dict, outfile: Path):
    """
    Saves metadata to file as JSON.

    Args:
        metadata: Dictionary containing metadata.
        outfile: Path object to target file.
    """

    with outfile.open("w") as f:
        json.dump(metadata, f, indent=4)


# def recursive_create_odml(doc, metadata: dict):
#     """
#     Recursively creates odml document following metadata structure.
#     Dictionaries are converted to sections and simple values to properties.

#     Args:
#         doc: base odml object.
#         metadata: Dictionary containing metadata.
#     """

#     for i in metadata:
#         val = metadata[i]
#         if isinstance(val, dict):
#             # TODO: type=?, definition=?, reference=?,
#             #       repository=?, link=?, include=?, oid=?,
#             #       sec_cardinality=?, prop_cardinality=?
#             n_doc = odml.Section(name=i)
#             recursive_create_odml(n_doc, val)
#             doc.append(n_doc)
#         else:
#             # TODO: unit=?, uncertainty=?, reference=?, definition=?,
#             #       dependency=?, dependency_value=?, dtype=?, value_origin=?,
#             #       oid=?, val_cardinality=?
#             doc.append(odml.Property(name=i, values=val))

# def export_as_odml(metadata: dict, outfile: Path):
#     """
#     Saves metadata to file as odML.

#     Args:
#         metadata: Dictionary containing metadata.
#         outfile: Path object to target file.
#     """

#     # TODO: author=?, version=?, repository=?
#     root = odml.Document(date=datetime.date(datetime.now()),
#                          oid=metadata.pop("_id"))
#     recursive_create_odml(root, metadata)
#     odml.save(root, str(outfile), "JSON")

PROCEDURES = {"JSON": export_as_json}
