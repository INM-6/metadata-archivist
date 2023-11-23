from metadata_archivist import AExtractor, Formatter
import yaml


def key_val_split(string, split_char):
    string = string.strip()
    out = string.split(split_char)
    return {out[0].strip(): out[1].strip()}


class time_extractor(AExtractor):

    def __init__(self) -> None:
        super().__init__(
            name='time_extractor',
            input_file_pattern='time\.txt',
            schema={
                'type': 'object',
                'properties': {
                    'real': {
                        'type': 'string',
                        'description':
                        'the time from start to finish of the call'
                    },
                    'user': {
                        'type': 'string',
                        'description': 'amount of CPU time spent in user mode'
                    },
                    'sys': {
                        'type': 'string',
                        'description':
                        'amount of CPU time spent in kernel mode'
                    },
                    'system': {
                        '$ref': '#/properties/sys'
                    }
                }
            })

    def extract(self, file_path) -> dict:
        out = {}
        with file_path.open("r") as fp:
            for line in fp:
                if line != '\n':
                    out.update(key_val_split(line, '\t'))
        return out


class yml_extractor(AExtractor):

    def __init__(self) -> None:
        super().__init__(name='yml_extractor',
                         input_file_pattern='.*\.yml',
                         schema={
                            'type': 'object',
                            'properties': {
                                'input_files': {
                                    'type': 'object',
                                    'properties': {
                                        'precipitation': {
                                            'type': 'string',
                                            'description': 'precipitation input file name'
                                        },
                                        'temperature': {
                                            'type': 'string',
                                            'description': 'temperature input file name'
                                        }
                                    }
                                },
                                'parameters': {
                                    'type': 'object',
                                    'properties': {
                                        'a': {
                                            'type': 'number',
                                            'description': 'parameter a'
                                        },
                                        'b': {
                                            'type': 'number',
                                            'description': 'parameter b'
                                        }
                                    }
                                },
                                'info1': {
                                    'type': 'string',
                                    'description': 'this is a  metadata'
                                },
                                'info2': {
                                    'type': 'string',
                                    'description': 'this as well'
                                }
                            }
                         })

    def extract(self, file_path):
        with open(file_path, "r") as stream:
            try:
                out = yaml.safe_load(stream)
                return out
            except yaml.YAMLError as exc:
                print(exc)


my_schema = {
    '$schema': 'https://abc',
    '$id': 'https://abc.json',
    'description': 'my example schema',
    'type': 'object',
    'properties': {
        'metadata_archive': {
            'type': 'object',
            'properties': {
                'program_execution': {
                    'type': 'object',
                    'properties': {
                        'time_info': {
                            '$ref': '#/$defs/time_extractor'
                        },
                        'model_configuration': {
                            '$ref': '#/$defs/yml_extractor'
                        },
                    }
                },
            },
        },
    }
}

my_parser = Formatter(extractors=[time_extractor(),
                               yml_extractor()],
                   schema=my_schema)
