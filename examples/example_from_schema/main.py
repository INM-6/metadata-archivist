#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from metadata_archivist import Archivist
from my_parser import my_parser
from pathlib import Path

arch = Archivist(archive_path=Path('metadata_archive.tar'),
                 extraction_directory='tmp',
                 parser=my_parser,
                 output_directory="./",
                 output_file="metadata.json",
                 overwrite=True,
                 auto_cleanup=True,
                 verbose=True)

arch.extract()
arch.export()
