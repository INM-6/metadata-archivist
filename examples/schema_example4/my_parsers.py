#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Parsers instances examples with schema.
Authors: Matthias K., Jose V.

"""

from metadata_archivist import AParser
import yaml


def time_parser_sec(string):
    minute_split = string.split("m")
    minutes = int(minute_split[0]) * 60 * 1000
    second_split = minute_split[1].split(".")
    seconds = int(second_split[0]) * 1000
    milis = int(second_split[1][:-1])
    return (minutes + seconds + milis) / 1000


def key_val_split(string, split_char, functor=None):
    if functor is None:
        functor = lambda x: x
    string = string.strip()
    out = string.split(split_char)
    return {out[0].strip(): functor(out[1].strip())}


class time_parser(AParser):

    def __init__(self) -> None:
        super().__init__(
            name="time_parser",
            input_file_pattern="time\.txt",
            schema={
                "type": "object",
                "properties": {
                    "real": {
                        "type": "string",
                        "description": "the time from start to finish of the call",
                    },
                    "user": {
                        "type": "string",
                        "description": "amount of CPU time spent in user mode",
                    },
                    "sys": {
                        "type": "string",
                        "description": "amount of CPU time spent in kernel mode",
                    },
                    "system": {"$ref": "#/properties/sys"},
                },
            },
        )

    def parse(self, file_path) -> dict:
        out = {}
        with file_path.open("r") as fp:
            for line in fp:
                if line != "\n":
                    out.update(key_val_split(line, "\t", time_parser_sec))
        return out


class yml_parser(AParser):

    def __init__(self) -> None:
        super().__init__(
            name="yml_parser",
            input_file_pattern=".*\.yml",
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
                print(exc)
