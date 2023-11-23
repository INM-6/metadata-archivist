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
                         input_file_pattern='config\.yml',
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


class basin_character_extractor(AExtractor):

    def __init__(self) -> None:
        super().__init__(name='basin_character_extractor',
                         input_file_pattern='basin\.yml',
                         schema={
                            'type': 'object',
                            'properties': {
                                'river': {
                                    'type': 'string',
                                    'description': 'name of the river'
                                },
                                'length': {
                                    'type': 'integer',
                                    'description': 'length in km'
                                },
                                'size': {
                                    'type': 'integer',
                                    'description': 'flow accumulation in km^2'
                                },
                                'max_depth': {
                                    'type': 'integer',
                                    'description': 'maximum depth in m'
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


class station_character_extractor(AExtractor):

    def __init__(self) -> None:
        super().__init__(name='station_character_extractor',
                         input_file_pattern='station\.yml',
                         schema={
                            'type': 'object',
                            'properties': {
                                'river': {
                                    'type': 'string',
                                    'description': 'name of the river'
                                },
                                'grdc_id': {
                                    'type': 'string',
                                    'description': 'grdc id'
                                },
                                'mean_disch': {
                                    'type': 'number',
                                    'description': 'mean annual discharge in m^3s^-1'
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
    'description': 'my example schema 3',
    'type': 'object',
    'properties': {
        'metadata_archive': {
            'type': 'object',
            'patternProperties': {
                "^basin_": {
                    "type": "object",
                    "properties": {
                        "basin_characteristics": {
                            "$ref": "#/$defs/basin_character_extractor"
                        },
                        "simulation": {
                            'type': 'object',
                            'properties': {
                                'time_info': {
                                    '$ref': '#/$defs/time_extractor'
                                },
                                'model_configuration': {
                                    '$ref': '#/$defs/yml_extractor'
                                },
                            }
                        }
                    }
                },
                "^station_": {
                    "type": "object",
                    "properties": {
                        "basin_characteristics": {
                            "$ref": "#/$defs/station_character_extractor"
                        },
                        "simulation": {
                            'type': 'object',
                            'properties': {
                                'time_info': {
                                    '$ref': '#/$defs/time_extractor'
                                },
                                'model_configuration': {
                                    '$ref': '#/$defs/yml_extractor'
                                },
                            }
                        }
                    }
                }
            }
        },
    }
}

my_parser = Formatter(extractors=[
    time_extractor(),
    yml_extractor(),
    station_character_extractor(),
    basin_character_extractor()
],
                   schema=my_schema)
