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

## Schema Interpreter Notes
To be able to parse abstract schema and generate correctly structured metadata files,
an intermediary data structure is needed to convert implicit schema definitions to explicit functional rules.

### Basic premises
From the metadata file perspective, the structure can be separated by structure stemming from the parsing results
and structure stemming from the extraction results.
When using a schema the structure of the parsing results are dictated by the schema regardless of the extractors used.
Hence, when exploring the schema to generate the intermediary data structure
one can consider the branching of the schema structure as branching of the metadata structure
and the extractor structure as a terminal value.
Inside the schema extractor structures are defined as exernal defs i.e. in the $defs section, so
when exploring the schema properties to generate the intermediary data tree, all new objects can be considered as branches
and the references to the $defs section as leafs.

### Technical assumptions
- There are only two valid data types in the schema, dictionnaries and strings (key[str] -> value[dict|str]).
  - Any other type is to be considered as an non-implemented feature
  - From this we assume that we either explore a dictionnary as a branch or a string as a leaf.
- Currently the only functionnal leafs are either $refs to $defs and !varname for patternProperties
  - All other leafs are considered as JSONSchema speficic and ignored
  - $refs to properties should only be found inside extractor structure
  - As $defs are special strings comprise of an xml-style path using / as separators, extractor names should not contain /
  - !varname instructions are considered as additional contextual information
  - !varname instructions can only be found in a patterProperty context
- Exploring starts from the properties at the root of the schema and we recursively explore over every dictionnary found inside.
- An extractor structure must always be introduced inside a named dictionnary containing an optionnal !extractor instruction and a mandatory $ref to a $def (structure name -> {(!extractor: dict)?, $ref: $def})
  - Only a $ref to a $def is accepted in the independent dictionnary
  - !extractor instructions point to dictionnaries but this are not considered branches of the metadata structure, insitead are considered as additional contextual information
  - !extractor instructions can only be in an extractor context and always preceed the $ref
