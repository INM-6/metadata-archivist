from metadata_archivist import Archivist
from my_parser import my_parser
from pathlib import Path

arch = Archivist(config='config.json',
                 archive_path=Path('metadata_archive.tar'),
                 parser=my_parser)

arch.extract()
arch.export()
