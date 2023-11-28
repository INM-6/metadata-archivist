#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from metadata_archivist import Archivist
from my_parser import my_parser
from pathlib import Path
from json import dumps, dump

arch = Archivist(path=Path('raw_metadata'),
                 formatter=my_parser,
                 output_directory="./",
                 output_file="metadata.json",
                 overwrite=True,
                 auto_cleanup=True,
                 verbose='debug',
                 add_description=True,
                 add_type=True)

arch.parse()
arch.export()

print("\nResulting schema:")
print(dumps(my_parser.schema, indent=4))
with Path("schema.json").open("w") as f:
    dump(my_parser.schema, f, indent=4)

print("\nResulting metadata:")
print(dumps(arch.get_metadata(), indent=4))
