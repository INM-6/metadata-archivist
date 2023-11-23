from metadata_archivist import AParser, Formatter
import yaml


def key_val_split(string, split_char):
    string = string.strip()
    out = string.split(split_char)
    return {out[0].strip(): out[1].strip()}


class time_parser(AParser):

    def __init__(self) -> None:
        super().__init__(
            name='time_parser',
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

    def parse(self, file_path) -> dict:
        out = {}
        with file_path.open("r") as fp:
            for line in fp:
                if line != '\n':
                    out.update(key_val_split(line, '\t'))
        return out


class yml_parser(AParser):

    def __init__(self) -> None:
        super().__init__(name='yml_parser',
                         input_file_pattern='config\.yml',
                         schema={})

    def parse(self, file_path):
        with open(file_path, "r") as stream:
            try:
                out = yaml.safe_load(stream)
                return out
            except yaml.YAMLError as exc:
                print(exc)


class basin_character_parser(AParser):

    def __init__(self) -> None:
        super().__init__(name='basin_character_parser',
                         input_file_pattern='basin\.yml',
                         schema={'type': 'object',
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

    def parse(self, file_path):
        with open(file_path, "r") as stream:
            try:
                out = yaml.safe_load(stream)
                return out
            except yaml.YAMLError as exc:
                print(exc)


class station_character_parser(AParser):

    def __init__(self) -> None:
        super().__init__(name='station_character_parser',
                         input_file_pattern='station\.yml',
                         schema={'type': 'object',
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
                            }
                         )

    def parse(self, file_path):
        with open(file_path, "r") as stream:
            try:
                out = yaml.safe_load(stream)
                return out
            except yaml.YAMLError as exc:
                print(exc)


my_schema = {
    '$schema': 'https://abc',
    '$id': 'https://abc.json',
    'description': 'my example schema 2',
    'type': 'object',
    'properties': {
        'metadata_archive': {
            'type': 'object',
            'patternProperties': {
                "^basin_": {
                    "!varname": 'basin',
                    "type": "object",
                    'description': 'some description',
                    "properties": {
                        "basin_information": {
                            "!parsing": {
                                'path': '*/{basin}/basin.yml',
                                'keys': ['river', 'size']
                            },
                            '$ref': '#/$defs/basin_character_parser',
                        },
                    }
                },
                "^station_": {
                    "!varname": 'station',
                    "type": "object",
                    "properties": {
                        "station_information": {
                            "!parsing": {
                                'path': '*/{station}/station.yml',
                                'keys': ['river', 'mean_disch']
                            },
                            '$ref': '#/$defs/station_character_parser',
                        },

                    },
                }
            },
        }
    }
}

my_parser = Formatter(parsers=[
    time_parser(),
    yml_parser(),
    station_character_parser(),
    basin_character_parser()
],
                   schema=my_schema)
