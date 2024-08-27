"""
Unit tests for AParser
"""

import sys
import unittest
from pathlib import Path

import yaml

sys.path.append("src")
from metadata_archivist.formatter import Formatter
from metadata_archivist.parser import AParser

PARSER_NAME = "DummyParser"
INPUT_FILE_PATTERN = ".*_dummyfile\.yaml"
SCHEMA = {
    "type": "object",
    "properties": {
        "ModelName": {
            "type": "string",
            "description": "The name of the model",
        },
        "ModelVersion": {
            "type": "string",
            "description": "The model version",
        },
        "ModelNumTasks": {
            "type": "integer",
            "description": "Number of tasks used for model execution",
        },
    },
}

TESTFILE_CONTENT = {
    "ModelName": "A_model",
    "ModelVersion": "v5.13.1",
    "ModelNumTasks": 4,
}


class DummyParser(AParser):
    def __init__(self) -> None:
        super().__init__(name=PARSER_NAME, input_file_pattern=INPUT_FILE_PATTERN, schema=SCHEMA)

    def parse(self, file_path) -> dict:
        out = {}
        with file_path.open("r") as fp:
            out = yaml.safe_load(fp)
        return out


class TestAParser(unittest.TestCase):

    def test_parser_methods(self):
        """
        test Parser class
        """

        parser = DummyParser()

        self.assertEqual(parser.name, PARSER_NAME)
        self.assertEqual(parser.input_file_pattern, INPUT_FILE_PATTERN)
        self.assertEqual(parser.schema, SCHEMA)
        self.assertTrue(parser.validate_output)
        self.assertEqual(parser.get_reference(), f"#/$defs/{PARSER_NAME}")

        f1 = Path("tests/test_data/example_dummyfile.yaml")
        self.assertEqual(parser.run_parser(f1), TESTFILE_CONTENT)

        new_name = "new_DummyParser"
        new_input_file_pattern = "test_pattern.test"
        new_schema = {
            "type": "object",
            "properties": {
                "ModelName": {
                    "type": "string",
                    "description": "The name of the model",
                },
            },
        }
        parser.name = new_name
        self.assertEqual(parser.name, new_name)
        parser.input_file_pattern = new_input_file_pattern
        self.assertEqual(parser.input_file_pattern, new_input_file_pattern)
        parser.schema = new_schema
        self.assertEqual(parser.schema, new_schema)

    def test_formatter_interaction(self):
        """
        test interaction with formatter
        """

        parser = DummyParser()

        formatter1 = Formatter()

        parser.register_formatter(formatter1)
        self.assertEqual(parser._formatters[0], formatter1)

        parser.remove_formatter(formatter1)
        self.assertListEqual(parser._formatters, [])


if __name__ == "__main__":
    unittest.main()
