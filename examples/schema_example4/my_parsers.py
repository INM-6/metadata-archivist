#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Parsers instances examples with schema.
Authors: Matthias K., Jose V.

"""

import re

from metadata_archivist import AParser
import yaml


class time_parser(AParser):

    def __init__(self) -> None:
        super().__init__(
            name="time_parser",
            input_file_pattern="time\.txt",
            schema={
                "type": "object",
                "properties": {
                    "real": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "number",
                                "description": "the time from start to finish of the call",
                            },
                            "unit": {
                                "type": "string",
                                "description": "unit of the value of time",
                            },
                        },
                    },
                },
            },
        )

    def parse(self, file_path) -> dict:
        out = {"real": {"value": None, "unit": "s"}}
        rex = re.compile(r"^real\s+(\d+)m(\d+\.?\d*)s$")
        with file_path.open("r") as fp:
            for line in fp:
                rmatch = rex.match(line)
                if rmatch is not None and len(rmatch.groups()) > 1:
                    out["real"]["value"] = int(rmatch.group(1)) * 60 + float(rmatch.group(2))
                    break
            else:
                raise ValueError("Real time not found in file.", file_path)
        return out


class config_parser(AParser):

    def __init__(self) -> None:
        super().__init__(
            name="config_parser",
            input_file_pattern="config\.yml",
            schema={
                "type": "object",
                "properties": {
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sim_time": {
                                "type": "number",
                                "description": "total time to simulate",
                            },
                            "scale": {"type": "number", "description": "model scale"},
                            "num_procs": {
                                "type": "number",
                                "description": "number of MPI processes",
                            },
                            "threads_per_proc": {
                                "type": "number",
                                "description": "number of threads used per MPI process",
                            },
                            "step_size": {
                                "type": "number",
                                "description": "step size for advancing simulation",
                            },
                        },
                    }
                },
            },
        )

    def parse(self, file_path):
        with open(file_path, "r") as stream:
            try:
                out = yaml.safe_load(stream)
                return out
            except yaml.YAMLError as exc:
                raise ValueError("Could not open YAML file.", file_path, exc)
