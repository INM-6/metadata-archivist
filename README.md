# Metadata Archive Handler

## Description
At the end of the beNNch workflow one archive containing the metadata files for each simulation run during the benchmarking is generated. An example of this archive can be found in the example folder. The code in this directory is meant to handle the extraction of said archive, the collection/parsing of the metadata files and the generation of a metadata collection which is saved to a JSON or odML file (format can be passed as argument).

## Modules:
TODO: Needs update
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
an interpretable data structure is needed to convert implicit schema definitions to explicit functional rules.

### Terms
* Metadata archive:
  * Compressed directory containing a tree structure of sub-directories (branches) and raw metadata files (leafs).
  * The tree structure can be flat i.e. only contain leafs or have an arbitrary number of branches each containing at least one leaf.
* Parser/parsing results:
 * A Parser is the entity reading from raw metadata files and parsing the information as defined by the user.
 * The parsing results are the output of the Parser on a given raw metadata file.
 * Each Parser produces results in its own structure as defined by the user.
* Formatter/formatting result:
 * The Formatter is the entity gathering all the parsing results from all the defined Parsers and merging it together in an unified metadata file.
 * The formatting result is the output metadata file.
 * The Formatter produces results on either a default structure following the metadata archive tree or a JSON schema can be provided to specify the structure and contents.
* JSON schema:
  * Through the properties (and only the properties) of the schema the user can define the structure of the unified metadata file.
  * On a broad perspective, the properties (tree) of the schema are composed of either acyclic nested structure (branches) or simple values (leafs).
  * Parsers and their results can be referenced by defining references (leafs) at bottom level structures.

### Basic premise
The structure of the unified metadata file can be separated by structure stemming from the formatting results and structure stemming from the parsing results.
When using a schema, the structure of the formatting results are solely dictated by the schema.
Hence, when exploring the schema to generate the interpretable data structure one can consider the branching in the schema structure as branching of the metadata structure and the parsing structure as a terminal value.

### Technical assumptions
- There are only two valid data types in the schema, dictionaries and strings i.e. the schema is composed of key[str] -> value[dict|str],
  - Any other type is to be considered as an non-implemented feature.
  - From this we assume that we either explore a dictionary as a branch or a string as a leaf.
- Currently the only functional leafs are either references to extractor definitions and !varname for patternProperties,
  - All other leafs are considered as JSON Schema specific values and ignored.
  - It is possible to reference internal extractor properties however this can only be done inside the extractor definition.
  - References are defined through unix-style paths with the definition section at its root, due to "/" being used as path separator, the character cannot be used in extractor names.
  - !varname instructions are considered as additional contextual information.
  - !varname instructions can only be found in a patterProperty context.
- Exploring starts from the properties at the root of the schema and a recursion is applied over every dictionary found inside.
- A PArser must always be introduced inside a named dictionary containing an optional !parsing instruction and a mandatory reference to its definition (structure name -> {(!parsing: dict)?, $ref: $def})
  - Only one reference to a definition is accepted per named dictionary. (TODO: expand on the future?)
  - !parsing instructions point to dictionaries but this are not considered branches of the metadata structure, instead are considered as additional contextual information.
  - !parsing instructions must always precede the reference.
