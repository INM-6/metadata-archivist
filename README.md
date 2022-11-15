# Metadata Archive Handler

## Description
At the end of the beNNch workflow one archive containing the metadata files for each simulation run during the benchmarking is generated. An example of this archive can be found in the example folder. The code in this directory is meant to handle the extraction of said archive, the collection/parsing of the metadata files and the generation of a metadata collection which is saved to a JSON or odML file (format can be passed as argument).

## Modules:
* extractor.py: Module containing archive extraction procedures.
* extraction_rules.py: Module containing per archive format extraction rules.
* collector.py: Module containing metadata collection procedures.
* collection_rules.py: Module containing per file collection rules (to be used with files from metadata_archive.py from beNNch).
* saver.py: Module containing metadata save to file procedures.
* save_rules.py: Module containing per file format save rules.

## Examples:
see examples:
* main.py: execute the extract, collect, save pipeline:
    * example:
        ```shell
        python3 main.py 6cf9f46c-1168-44f4-a08f-d14f036384df.tgz
        ```
        ```shell
        python3 main.py test_namelist.tgz -v --config config_example_namelist.json
        ```
    * for help with execution arguments:
    	```shell
        python3 main.py -h
        ```

