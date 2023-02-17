from metadata_archivist import AExtractor, Parser
import yaml


def key_val_split(string, split_char):
    string = string.strip()
    out = string.split(split_char)
    return {out[0].strip(): out[1].strip()}


class time_extractor(AExtractor):

    def __init__(self) -> None:
        self.name = 'time_extractor'
        self._input_file_pattern = 'time.txt'
        self._extracted_metadata = {}

        self._schema = {}

    def extract(self, file_path) -> dict:
        out = {}
        with file_path.open("r") as fp:
            for line in fp:
                if line != '\n':
                    out.update(key_val_split(line, '\t'))
            return out


class yml_extractor(AExtractor):

    def __init__(self) -> None:
        self.name = 'yml_extractor'
        self._input_file_pattern = '*.yml'
        self._extracted_metadata = {}

        self._schema = {}

    def extract(self, file_path) -> dict:
        with file_path.open("r") as fp:
            out = yaml.safe_load(fp)
            return out


my_parser = Parser(extractors=[time_extractor(), yml_extractor()])
