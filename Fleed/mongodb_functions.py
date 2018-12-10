
def get_next_sequence(table, field):
    max_field = table.aggregate([ { '$group': {'_id': None, 'max_field': { '$max': "$" + field }} } ])
    return list(max_field)[0]['max_field'] + 1