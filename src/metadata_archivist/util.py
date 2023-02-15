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


def _search_list(metadata_list, ref, metadata, replace):
    for litem in metadata_list:
        if isinstance(litem, list):
            _search_list(litem, ref, metadata, replace)
        elif isinstance(litem, dict):
            _search_tree(litem, ref, metadata, replace)
        # elif isinstance(litem, str):
        #     _handle_str_entry(tree, k, ref, metadata)


def _search_tree(tree, ref, metadata, replace=True):
    for k, v in tree.copy().items():
        if isinstance(v, dict):
            if '$ref' in v.keys():
                if replace:
                    tree[k] = _handle_str_entry(v, '$ref', ref, metadata)
            else:
                _search_tree(v, ref, metadata, replace)
                if not v:
                    del tree[k]
        elif isinstance(v, list):
            _search_list(v, ref, metadata, replace)
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


def _update_tree_from_defs(schema: dict, ref, metadata):
    schema_keys = list(schema['$defs'].keys())
    if '$defs' not in schema.keys():
        return
    for k in schema_keys:
        if ref == f'#/$defs/{k}':
            continue
        else:
            _search_tree(schema['$defs'][k], ref, metadata, False)
            if not schema['$defs'][k]:
                del schema['$defs'][k]
    # update keys for iter
    # print('\n')
    # print(schema)
    for k in schema['$defs'].keys():
        # print(f'{k}')
        if ref == f'#/$defs/{k}':
            continue
        else:
            _replace_ref_with_def(schema['properties'], f'#/$defs/{k}',
                                  schema['$defs'][k])
    # del schema['$defs']


def _replace_ref_with_def(d, base_ref, ref_dict):
    for k in list(d.keys()):
        # print(f'    {k}')
        if k == '$ref':
            xx = _replace_ref_with_def_handler(d[k], base_ref, ref_dict)
            if xx is not None:
                d.update(xx)
                del d[k]
        elif isinstance(d[k], dict):
            _replace_ref_with_def(d[k], base_ref, ref_dict)
        elif isinstance(d[k], list):
            _replace_ref_with_def_list(d[k], base_ref, ref_dict)


def _replace_ref_with_def_list(l, base_ref, ref_dict):
    for ii in l:
        if isinstance(ii, dict):
            _replace_ref_with_def(ii, base_ref, ref_dict)
        elif isinstance(ii, list):
            _replace_ref_with_def_list(ii, base_ref, ref_dict)


def _replace_ref_with_def_handler(v, base_ref, ref_dict):
    # print(v)
    # print(base_ref)
    # print(ref_dict)
    if isinstance(v, str) and v[:len(base_ref)] == base_ref:
        if len(v) == len(base_ref):
            return ref_dict
        else:
            keys_list = [xx for xx in v[len(base_ref):].split('/') if xx != '']
            return reduce(lambda d, kk: d.get(kk)
                          if d else None, keys_list, ref_dict)


def delete_none(_dict):
    """Delete None values recursively from all of the dictionaries"""
    for key, value in list(_dict.items()):
        if isinstance(value, dict):
            delete_none(value)
            if not value:
                del _dict[key]
        elif value is None:
            del _dict[key]
        elif isinstance(value, list):
            for v_i in value:
                if isinstance(v_i, dict):
                    delete_none(v_i)

    return _dict


def get_structured_metadata(schema, ref, metadata):
    metadata_tree = schema.copy()
    _update_tree_from_defs(metadata_tree, ref, metadata)
    # print(metadata_tree)
    if '$defs' in metadata_tree.keys():
        del metadata_tree['$defs']
    metadata_tree = _rm_layers(metadata_tree, 'properties')
    _search_tree(metadata_tree, ref, metadata)
    metadata_tree = delete_none(metadata_tree)
    return metadata_tree
