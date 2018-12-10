from Fleed import auth
import json

url = 'https://api.twitter.com/1.1/'

def get_user(screen_name):
    resp, content = auth.client.request(
            url + 'users/show.json?screen_name=' + screen_name, 
            method="GET", body=b"", headers=None)
    return json.loads(content.decode('utf-8'))

def get_users_search(search_text, page = 1, count = 10, include_entities = 'true'):
    resp, content = auth.client.request(
            url + 'users/search.json?q=' + search_text + '&page=' + str(page) + '&count=' + str(count) + '&include_entities=' + include_entities,
            method="GET", body=b"", headers=None)
    return json.loads(content.decode('utf-8'))

def get_rate_limit_status():
    resp, content = auth.client.request(
            url + 'application/rate_limit_status.json', 
            method="GET", body=b"", headers=None)
    return json.loads(content.decode('utf-8'))

def get_followers():
    resp, content = auth.client.request(
            url + 'followers/list.json', 
            method="GET", body=b"", headers=None)
    return json.loads(content.decode('utf-8'))

def get_user_lists(screen_name):
    resp, content = auth.client.request(
            url + 'lists/list.json?screen_name=' + screen_name, 
            method="GET", body=b"", headers=None)
    return json.loads(content.decode('utf-8'))

def get_user_timeline(screen_name, count, max_id):
    if max_id != '' and max_id != None:
        resp, content = auth.client.request(
                url + 'statuses/user_timeline.json?screen_name=' + screen_name + '&tweet_mode=extended' + '&count=' + count + '&max_id=' + max_id,
                method="GET", body=b"", headers=None)
    else:
        resp, content = auth.client.request(
                url + 'statuses/user_timeline.json?screen_name=' + screen_name + '&tweet_mode=extended' + '&count=' + count,
                method="GET", body=b"", headers=None)
    return json.loads(content.decode('utf-8'))
