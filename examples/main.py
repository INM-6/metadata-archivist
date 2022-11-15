#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata extraction, collection and save pipeline example.
Tested with Python 3.8.10
Author: Jose V.

"""

import sys
import json
import importlib.util

from pathlib import Path
from argparse import ArgumentParser

from metadata_archivist import decompressor as dc
from metadata_archivist import parser as pr
from metadata_archivist import exporter as ex


def load_config(config_path: str) -> dict:
    """
    Checks path to configuration file and attempts to load it.

    Args:
        config_path: String path to configuration file.

    Returns:
        Dictionary containing loaded configuration
    """

    path = Path(config_path)

    assert path.is_file and path.suffix == ".json"

    with path.open() as f:
        res = json.load(f)

    return res


def check_dir(dir_path: str, allow_existing: bool = False) -> Path:
    """
    Checks directory path.
    If a directory with the same name already exists then continue.
    If a directory in the specified path cannot be created then execution is
    stopped.

    Args:
        dir_path: String path to output directory.
        allow_existing: Control boolean to allow the use of existing folders.

    Returns:
        Path object to output directory.
    """

    path = Path(dir_path)

    if dir_path != "":
        exists = path.exists()
        if not allow_existing:
            assert not exists, f"Directory already exists: {dir_path}"
        elif exists:
            assert path.is_dir(), f"Incorrect path to directory: {path}"
            return path

        try:
            path.mkdir()
        except FileNotFoundError as e:
            # This exception is raised if a nested path is given and intermediate directories do not exist
            print(f"Incorrect path to directory: {e.args}")
            sys.exit()

    return path


def check_args(args) -> tuple:
    """
    Checks arguments to be of correct type and value.
    If an error is found, an error help message is printed and the execution
    is stopped.

    Args:
        _args: Namespace object containing all argument values as attributes.

    Returns:
        Tuple of checked arguments.
    """

    assert all(v is not None for v in vars(args).values(
    )) and args.archive != "", "Please specify a metadata archive to extract."

    config = load_config(args.config)

    archive_path, archive_type = dc.check_archive(args.archive)
    dc_dir_path = check_dir(config["extraction_directory"],
                            allow_existing=False)
    out_dir_path = check_dir(config["output_directory"], allow_existing=True)
    checked_format = ex.check_format(config["output_format"])

    members = config["extraction_members"]
    assert members is None or (isinstance(members, list)
                               and all(isinstance(em, str) for em in members))
    mode = config["parsing_rules"]["mode"].lower()
    if mode == "standard":
        module_path = None
    else:
        assert mode == "overwrite"
        assert isinstance(config["parsing_rules"]["module"], str)
        module_path = Path(config["parsing_rules"]["module"])
        assert module_path.is_file() and module_path.suffix == ".py"
        # TODO: implement checksum for security check against malicious code

    return archive_path, archive_type, dc_dir_path, members, out_dir_path, checked_format, mode, module_path, not args.keep_decompressed, args.verbose


def get_args():
    """
    Argument parser where arguments are first defined to be identified by the
    system call
    and then the parsed result is returned.

    Returns:
        arguments: Namespace object containing all argument values as
        attributes.
    """

    parser = ArgumentParser(
        prog="Metadata archive extractor and file generator.")

    parser.add_argument("archive",
                        type=str,
                        help=f'''Path to archive where metadata is stored.
Accepted archive formats: {dc.formats()}''')
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration file. Must be in JSON format.")
    parser.add_argument(
        "-k",
        "--keep_decompressed",
        default=False,
        action="store_true",
        help='''Boolean to control whether the decompressed archives are kept
after execution. Default is False.''')
    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="Boolean to control verbose output. Default is False.")

    return parser.parse_args()


def main():
    archive, arch_type, dc_dir, members, out_dir, out_format, mode, module_path, rm_dc_dir, verbose = check_args(
        get_args())

    if verbose:
        print(f'''Archive path: {archive}\nOutput path: {out_dir}
Extraction path: {dc_dir}
Remove extracted: {rm_dc_dir}''')

    dc.decompress(archive, arch_type, dc_dir, members, verb=verbose)

    if verbose:
        print("Finished extracting archive.")

    arch_name = archive.stem.split(".")[0]
    dc_arch_dir = dc_dir.joinpath(arch_name)

    if verbose:
        print(f'''Extracted archive path: {dc_arch_dir}
Beginning collecting metadata.''')

    module = None
    if mode == "overwrite":
        # Taken from https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        spec = importlib.util.spec_from_file_location(module_path.name,
                                                      module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path.name] = module
        spec.loader.exec_module(module)

    metadata = {"_id": arch_name}
    pr.parse_data(dc_arch_dir,
                  metadata,
                  mode,
                  module,
                  rm=rm_dc_dir,
                  verb=verbose)

    if verbose:
        print("Finished collecting metadata.")

    if rm_dc_dir and str(dc_dir) != ".":
        dc_dir.rmdir()

    metadata_file = out_dir.joinpath(f"{arch_name}.json")
    ex.export(metadata, metadata_file, out_format, verb=verbose)


if __name__ == "__main__":
    main()
