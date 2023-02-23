from metadata_archivist import AExtractor, Parser
import f90nml

NML_SCHEMA = {}


class nml_extractor(AExtractor):

    def __init__(self):
        super().__init__(name='nml_extractor', input_file_pattern='*.nml', schema=NML_SCHEMA)

    def extract(self, f):
        nml = f90nml.read(f)
        return nml.todict()


my_parser = Parser(extractors=[nml_extractor()])

# xx = nml_extractor()

# with open('metadata_archive/mhm.nml') as ff:
#     yy = xx.extract(ff)
# print(yy)
