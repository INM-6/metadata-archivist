'''
functions for handling metadata tree
'''
from functools import reduce


def _handle_str_entry(tree, k, ref, metadata):
    if k != '$ref':
        del tree[k]
        return
    if ref == tree[k]:
        # tree[k] = metadata
        return metadata
    elif len(ref) < len(tree[k]) and ref == tree[k][:len(ref)]:
        keys_list = [xx for xx in tree[k][len(ref):].split('/') if xx != '']
        # tree[k] = reduce(lambda d, kk: d.get(kk)
        #                  if d else None, keys_list, metadata)
        return reduce(lambda d, kk: d.get(kk)
                      if d else None, keys_list, metadata)
    else:
        del tree[k]


def _search_list(metadata_list, ref, metadata):
    for litem in metadata_list:
        if isinstance(litem, list):
            _search_list(litem, ref, metadata)
        elif isinstance(litem, dict):
            _search_tree(litem, ref, metadata)
        # elif isinstance(litem, str):
        #     _handle_str_entry(tree, k, ref, metadata)


def _search_tree(tree, ref, metadata):
    for k, v in tree.copy().items():
        if isinstance(v, dict):
            if '$ref' in v.keys():
                tree[k] = _handle_str_entry(v, '$ref', ref, metadata)
            else:
                _search_tree(v, ref, metadata)
                if not v:
                    del tree[k]
        elif isinstance(v, list):
            _search_list(v, ref, metadata)
        # elif isinstance(v, str):
        #     _handle_str_entry(tree, k, ref, metadata)
        elif isinstance(v, str) and k != '$ref':
            del tree[k]


def _rm_layers(tree, layername):
    return_dict = {}
    for k, v in tree.items():
        if isinstance(v, dict) and k == layername:
            return_dict.update(_rm_layers(v, layername))
        elif isinstance(v, dict):
            return_dict.update({k: _rm_layers(v, layername)})
        else:
            return_dict.update({k: v})
    return return_dict


def get_structured_metadata(schema, ref, metadata):
    metadata_tree = schema.copy()
    if '$defs' in metadata_tree.keys():
        del metadata_tree['$defs']
    metadata_tree = _rm_layers(metadata_tree, 'properties')
    _search_tree(metadata_tree, ref, metadata)
    return metadata_tree
