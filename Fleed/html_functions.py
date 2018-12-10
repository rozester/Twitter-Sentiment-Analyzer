
def format_time_zone(account):
    utc_offset = ''
    if account['utc_offset'] != None and account['utc_offset'] != "" and account['utc_offset'] != 0:
        utc_offset = account['utc_offset']

    time_zone = ''
    if account['time_zone'] != None and account['time_zone'] != "":
        time_zone = account['time_zone']

    if account['time_zone'] != None and account['utc_offset'] > 0:
        utc_offset = '(UTC+' + "{:,.0f}".format(account['utc_offset'] / 3600) + ':00)' if account['utc_offset'] > 36000 else '(UTC+0' + "{:,.0f}".format(account['utc_offset'] / 3600) + ':00)'
    elif account['time_zone'] != None and account['utc_offset'] == 0:
        utc_offset = '(UTC+00:00)'
    elif account['time_zone'] != None and account['utc_offset'] < 0:
        utc_offset = '(UTC-' + "{:,.0f}".format(abs(account['utc_offset']) / 3600) + ':00)' if account['utc_offset'] < -36000 else '(UTC-0' + "{:,.0f}".format(abs(account['utc_offset']) / 3600) + ':00)'

    if utc_offset != '' and time_zone != '':
        return utc_offset + ' ' + time_zone
    
    if utc_offset != '' and time_zone == '':
        return utc_offset

    if utc_offset == '' and time_zone != '':
        return time_zone

    return ''