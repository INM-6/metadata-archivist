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
        self.ref = '#/$defs/time_extractor'

        self.schema = {
            'type': 'object',
            'properties': {
                'real': {
                    'type': 'string',
                    'description': 'the time from start to finish of the call'
                },
                'user': {
                    'type': 'string',
                    'description': 'amount of CPU time spent in user mode'
                },
                'sys': {
                    'type': 'string',
                    'description': 'amount of CPU time spent in kernel mode'
                },
                'system': {
                    '$ref': '#/properties/sys'
                }
            }
        }

    def extract(self, data) -> dict:
        out = {}
        for line in data:
            if line != '\n':
                out.update(key_val_split(line, '\t'))
        return out


class yml_extractor(AExtractor):

    def __init__(self) -> None:
        self.name = 'yml_extractor'
        self._input_file_pattern = '*.yml'
        self._extracted_metadata = {}
        self.ref = '#/$defs/yml_extractor'

        self.schema = {}

    def extract(self, data) -> dict:
        out = yaml.safe_load(data)
        return out


my_schema = {
    '$schema': 'https://abc',
    '$id': 'https://abc.json',
    'description': 'my example schema',
    'type': 'object',
    'properties': {
        'real_runtime': {
            '$ref': '#/$defs/time_extractor/real'
        },
        'model_configuration': {
            '$ref': '#/$defs/yml_extractor'
        },
        'further_info': {
            'type': 'object',
            'properties': {
                'time_info': {
                    '$ref': '#/$defs/time_extractor'
                }
            }
        },
        'nested_other_block': {
            'type': 'object',
            'properties': {
                'extended_info': {
                    '$ref': '#/$defs/other_block'
                }
            }
        }
    },
    '$defs': {
        'time_extractor': {
            'type': 'object',
            'properties': {
                'real': {
                    'type': 'string',
                    'description': 'the time from start to finish of the call'
                },
                'user': {
                    'type': 'string',
                    'description': 'amount of CPU time spent in user mode'
                },
                'sys': {
                    'type': 'string',
                    'description': 'amount of CPU time spent in kernel mode'
                },
                'system': {
                    '$ref': '#/properties/sys'
                }
            }
        },
        'yml_extractor': {
            'type': 'object',
            'properties': {
                'input_files': {
                    'type': 'object',
                    'properties': {
                        'precipitation': {
                            'type': 'str',
                            'description': 'precipitation input file name'
                        },
                        'temperature': {
                            'type': 'str',
                            'description': 'temperature input file name'
                        }
                    }
                },
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'a': {
                            'type': 'float',
                            'description': 'parameter a'
                        },
                        'b': {
                            'type': 'float',
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
        },
        'other_block': {
            'type': 'object',
            'properties': {
                'nested_info': {
                    'type': 'object',
                    'properties': {
                        'user_time_info': {
                            '$ref': '#/$defs/time_extractor/user'
                        }
                    }
                }
            }
        }
    }
}

my_parser = Parser(extractors=[time_extractor(),
                               yml_extractor()],
                   metadata_tree='from_schema',
                   schema=my_schema)
