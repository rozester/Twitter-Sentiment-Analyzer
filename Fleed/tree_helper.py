
def is_last_node(node):
    for key, value in node.items():
        if (not isinstance(value, dict)):
            return True
    return False

def dict_traversal_leafs(node, list_of_dicts):
    if is_last_node(node):
        return None
        
    for key, value in node.items():
        c = dict_traversal_leafs(value, list_of_dicts)
        if (c == None and is_last_node(value)):
            mydict = {}
            mydict['url'] = key
            mydict['limit'] = value['limit']
            mydict['remaining'] = value['remaining']
            list_of_dicts.append(mydict)

def dict_traversal(node, list_of_dicts):
    if is_last_node(node):
        return None

    for key, value in node.items():
        c = dict_traversal(value, list_of_dicts)
        if (c == None):
            print(key + ':--- \n')
            print(str(value) + '\n')