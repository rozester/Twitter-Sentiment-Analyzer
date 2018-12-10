from flask import render_template, request, jsonify, redirect, url_for

from Fleed import app
from Fleed import tree_helper
from Fleed import api
from Fleed import html_functions
from Fleed import mongodb_functions
from Fleed import languaes

from pymongo import MongoClient
from datetime import datetime
from dateutil import parser
from itertools import groupby
from collections import Counter

import os
import json
import operator
import re

# Todo if main combobox is empty then visible false.
client = MongoClient('localhost', 27017)
db = client.twitter
profiles = db.profiles
user_lists = db.user_lists
tweets = db.tweets
profile_cats = db.profile_cats
custom_lists = db.custom_lists

emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002600-\U000027B0"  # Misc
                               "]+", flags=re.UNICODE)

@app.route('/')
@app.route('/home')
def home():
    top_tweets = profiles.aggregate([{'$project': {'_id': 0, 'name': 1, 'statuses_count': 1} }, {'$sort': { 'statuses_count': -1 } }, {'$limit': 10}])
    top_tweets = list(top_tweets)

    top_followers = profiles.aggregate([{'$project': {'_id': 0, 'name': 1, 'followers_count': 1} }, {'$sort': { 'followers_count': -1 } }, {'$limit': 10}])
    top_followers = list(top_followers)

    top_following = profiles.aggregate([{'$project': {'_id': 0, 'name': 1, 'friends_count': 1} }, {'$sort': { 'friends_count': -1 } }, {'$limit': 10}])
    top_following = list(top_following)

    top_likes = profiles.aggregate([{'$project': {'_id': 0, 'name': 1, 'favourites_count': 1} }, {'$sort': { 'favourites_count': -1 } }, {'$limit': 10}])
    top_likes = list(top_likes)

    return render_template('index.html',
        top_tweets=json.dumps(top_tweets),
        top_followers=json.dumps(top_followers),
        top_following=json.dumps(top_following),
        top_likes=json.dumps(top_likes),
        year=datetime.now().year)


@app.route('/contact')
def contact():
    return render_template('contact.html',
        year=datetime.now().year)


@app.route('/profile_list')
def profile_list():
    saved_accounts = list(profiles.find().sort([['_id', -1]]).limit(90))
    total_tweets = tweets.aggregate([{'$group': {'_id': '$user.screen_name', 'count': {'$sum': 1}}}])
    total_tweets = list(total_tweets)

    for account in saved_accounts:
        if not account['protected']:
            tweet = filter(lambda tweet: tweet['_id'] == account['screen_name'], total_tweets)
            account['downloaded'] = 0 if account['statuses_count'] == 0 else (list(tweet)[0]['count'] / account['statuses_count']) * 100
        else:
            account['downloaded'] = 0
            
    return render_template('profile_list.html',
        saved_accounts=saved_accounts,
        year=datetime.now().year)


@app.route('/twitter_search')
def twitter_search():
    search_text = request.args.get('search_text')
    is_username = request.args.get('is_username')

    if is_username != 'true':
        results = api.get_users_search(search_text)
        return jsonify(results=results)
    else:
        user = api.get_user(screen_name=search_text)
        return jsonify(results=[user])


@app.route('/delete_profile_classification', methods=['GET'])
def delete_profile_classification():
    screen_name = request.args.get('screen_name')
    id = request.args.get('id')

    profiles.update({"screen_name": screen_name }, {'$pull' : {"classification_types": int(id)}})
    
    return jsonify(message='Item deleted successfully !!!')


@app.route('/delete_profile_custom_list', methods=['GET'])
def delete_profile_custom_list():
    screen_name = request.args.get('screen_name')
    id = request.args.get('id')

    profiles.update({"screen_name": screen_name }, {'$pull' : {"custom_list": int(id)}})

    return jsonify(message='Item deleted successfully !!!')


@app.route('/add_profile_classifications', methods=['POST'])
def add_profile_classifications():
    screen_name = request.args.get('screen_name')
    user_data = json.loads(request.data.decode('utf-8'))
    
    if screen_name == '':
        return jsonify(results={})

    if len(user_data['classification_types']) == 0 and len(user_data['custom_list']) == 0:
        return jsonify(results={})

    profile_cat_ids = []
    for item in user_data['classification_types']:
        item_id = 0
        if '-' in item['id']:
            item_id = mongodb_functions.get_next_sequence(profile_cats, 'id')
            profile_cats.insert_one({ 'id': item_id, 'name': item['text'] })
        else:
            item_id = int(item['id'])

        profile_cat_ids.append({ 'id': item_id, 'text': item['text'] })
        
    custom_list_ids = []
    for item in user_data['custom_list']:
        item_id = 0
        if '-' in item['id']:
            item_id = mongodb_functions.get_next_sequence(custom_lists, 'id')
            custom_lists.insert_one({ 'id': item_id, 'name': item['text'] })
        else:
            item_id = int(item['id'])

        custom_list_ids.append({ 'id': item_id, 'text': item['text'] })

    account = profiles.find({'screen_name': screen_name})
    account = list(account)[0]

    if len(profile_cat_ids) > 0:
        if 'classification_types' in account:
            for item in [cat['id'] for cat in profile_cat_ids]:
                if item not in account['classification_types']:
                    profiles.update({"screen_name": screen_name }, {'$push' : {"classification_types": item}})
        else:
            profiles.update({"screen_name": screen_name }, {'$set' : {"classification_types": [cat['id'] for cat in profile_cat_ids]}})

    if len(custom_list_ids) > 0:
        if 'custom_list' in account:
            for item in [lst['id'] for lst in custom_list_ids]:
                if item not in account['custom_list']:
                    profiles.update({"screen_name": screen_name }, {'$push' : {"custom_list": item}})
        else:
            profiles.update({"screen_name": screen_name }, {'$set' : {"custom_list": [lst['id'] for lst in custom_list_ids]}})

    account = profiles.aggregate([{'$match': { 'screen_name': screen_name }}, {'$project': {'_id': 0, 'classification_types': 1, 'custom_list': 1} }])
    account = list(account)[0]
    if 'classification_types' in account:
        profile_cat_ids = profile_cats.aggregate([{'$match': { 'id': {'$in': account['classification_types']} }}, {'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
        profile_cat_ids = list(profile_cat_ids)

    if 'custom_list' in account:
        custom_list_ids = custom_lists.aggregate([{'$match': { 'id': {'$in': account['custom_list']} }}, {'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
        custom_list_ids = list(custom_list_ids)

    return jsonify(results={'classification_types': profile_cat_ids, 'custom_list': custom_list_ids})
    

@app.route('/profile_search')
def profile_search():

    return render_template('profile_search.html',
        year=datetime.now().year)


@app.route('/profile_compare', methods=['GET', 'POST'])
def profile_compare():
    accounts = list(profiles.aggregate([{'$project': {'_id': 0, 'id': {"$concat" : "$id_str"}, "text" : {"$concat" : "$name"}, 'profile_image_url': 1} }, {'$sort': { 'text': 1 } }]))
    
    users = {}
    compare_tweets = []
    compare_followers = []
    compare_following = []
    compare_likes = []
    users_tweets = []
    lang_summary = []
    length_summary = []
    daily_tweets = []
    weekly_tweets = []
    if request.method == 'POST':
        user_data = json.loads(request.form['user_data'])
        users = [str(i['id']) for i in user_data['profiles']]
        
        compare_tweets = profiles.aggregate([{'$match': { 'id_str': {'$in': users} }}, {'$project': {'_id': 0, 'name': 1, 'statuses_count': 1} }, {'$sort': { 'statuses_count': -1 } }, {'$limit': 10}])
        compare_tweets = list(compare_tweets)

        compare_followers = profiles.aggregate([{'$match': { 'id_str': {'$in': users} }}, {'$project': {'_id': 0, 'name': 1, 'followers_count': 1} }, {'$sort': { 'followers_count': -1 } }, {'$limit': 10}])
        compare_followers = list(compare_followers)

        compare_following = profiles.aggregate([{'$match': { 'id_str': {'$in': users} }}, {'$project': {'_id': 0, 'name': 1, 'friends_count': 1} }, {'$sort': { 'friends_count': -1 } }, {'$limit': 10}])
        compare_following = list(compare_following)

        compare_likes = profiles.aggregate([{'$match': { 'id_str': {'$in': users} }}, {'$project': {'_id': 0, 'name': 1, 'favourites_count': 1} }, {'$sort': { 'favourites_count': -1 } }, {'$limit': 10}])
        compare_likes = list(compare_likes)

        for user in user_data['profiles']:
            account = profiles.find({'id_str': user['id']})
            account = list(account)[0]

            filtered_tweets = tweets.aggregate([{'$match': { 'user.id_str': user['id'] }}, {'$project': {'_id': 0} }])
            filtered_tweets = list(filtered_tweets)

            tweets_langs = tweets.aggregate([{'$match': { 'user.id_str': user['id']  }}, 
                             {'$group': {'_id': '$lang', 'count': {'$sum': 1}}}])
            tweets_langs = list(tweets_langs)
            if len(tweets_langs) > 0:
                tweets_langs = sorted(tweets_langs, key=operator.itemgetter('count'), reverse=True)

            user_langs = []
            hashtags_summary = []
            emoji_summary = []
            user_length = [{'name': '1 To 50', 'count': 0}, {'name': '51 To 100', 'count': 0},
                          {'name': '101 To 150', 'count': 0}, {'name': '151 To 200', 'count': 0},
                          {'name': '201 To 250', 'count': 0}, {'name': '251 To 280', 'count': 0}]
            
            user_daily = []
            for hour in range(0, 24):
                user_daily.append({'name': hour, 'count': 0})

            user_weekly = []
            week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            for day in week_days:
                user_weekly.append({'name': day, 'count': 0})

            retweets_summary = []
            quoted_summary = []
            replies_summary = []
            mentions_summary = []

            for tweet in filtered_tweets:
                user_weekly[datetime.weekday(tweet['created_time'])]['count'] += 1
                user_daily[tweet['created_time'].hour]['count'] += 1

                languaes.detected_tweet_lang(tweet, user_langs, tweets_langs, account['lang'])

                if 'hashtags' in tweet['entities']:
                    for hashtag in tweet['entities']['hashtags']:
                        (i, item) = next(((i, item) for (i, item) in enumerate(hashtags_summary) if item['name'] == hashtag['text']), (None, False))
                        if not item:
                            hashtags_summary.append({'name': hashtag['text'], 'count': 1})
                        else:
                            hashtags_summary[i]['count'] += 1

                if 'retweeted_status' in tweet:
                    tweet_length = len(tweet['retweeted_status']['full_text']) + len(tweet['retweeted_status']['quoted_status']['full_text']) if 'quoted_status' in tweet['retweeted_status'] else len(tweet['retweeted_status']['full_text'])
                else:
                    tweet_length = len(tweet['full_text'])
            
                if tweet_length >= 0 and tweet_length <= 50:
                    user_length[0]['count'] += 1
                elif tweet_length > 50 and tweet_length <= 100:
                    user_length[1]['count'] += 1
                elif tweet_length > 100 and tweet_length <= 150:
                    user_length[2]['count'] += 1
                elif tweet_length > 150 and tweet_length <= 200:
                    user_length[3]['count'] += 1
                elif tweet_length > 200 and tweet_length <= 250:
                    user_length[4]['count'] += 1
                elif tweet_length > 250:
                    user_length[5]['count'] += 1
            
                if 'retweeted_status' in tweet:
                    emojis = re.findall(emoji_pattern, tweet['retweeted_status']['full_text'] + tweet['retweeted_status']['quoted_status']['full_text'] if 'quoted_status' in tweet['retweeted_status'] else tweet['retweeted_status']['full_text'])
                else:
                    emojis = re.findall(emoji_pattern, tweet['full_text'])

                emojis = list(''.join(emojis))
                emoji_summary.extend(emojis)

                if 'retweeted_status' in tweet:
                    (i, item) = next(((i, item) for (i, item) in enumerate(retweets_summary) if item['name'] == tweet['retweeted_status']['user']['screen_name']), (None, False))
                    if not item:
                        retweets_summary.append({'name': tweet['retweeted_status']['user']['screen_name'], 'count': 1})
                    else:
                        retweets_summary[i]['count'] += 1

                if 'quoted_status' in tweet:
                    (i, item) = next(((i, item) for (i, item) in enumerate(quoted_summary) if item['name'] == tweet['quoted_status']['user']['screen_name']), (None, False))
                    if not item:
                        quoted_summary.append({'name': tweet['quoted_status']['user']['screen_name'], 'count': 1})
                    else:
                        quoted_summary[i]['count'] += 1

                if tweet['in_reply_to_screen_name'] != None:
                    (i, item) = next(((i, item) for (i, item) in enumerate(replies_summary) if item['name'] == tweet['in_reply_to_screen_name']), (None, False))
                    if not item:
                        replies_summary.append({'name': tweet['in_reply_to_screen_name'], 'count': 1})
                    else:
                        replies_summary[i]['count'] += 1

                if 'user_mentions' in tweet['entities']:
                    for mention in tweet['entities']['user_mentions']:
                        (i, item) = next(((i, item) for (i, item) in enumerate(mentions_summary) if item['name'] == mention['name']), (None, False))
                        if not item:
                            mentions_summary.append({'name': mention['name'], 'count': 1})
                        else:
                            mentions_summary[i]['count'] += 1

            if len(user_daily) > 0:
                for item in user_daily:
                    daily_tweets.append({'name': item['name'], 'screen_name': user['text'], 'count': item['count']})

            if len(user_weekly) > 0:
                for item in user_weekly:
                    weekly_tweets.append({'name': item['name'], 'screen_name': user['text'], 'count': item['count']})

            if len(user_langs) > 0:
                user_langs = sorted(user_langs, key=operator.itemgetter('count'), reverse=True)
                others_langs = 0
                for item in user_langs[4:]:
                    others_langs += item['count']

                user_langs = user_langs[0: 4]
                user_langs.append({'name': 'Others', 'count': str(others_langs)})

                for item in user_langs:
                    lang_summary.append({'name': item['name'], 'screen_name': user['text'], 'count': item['count']})

            if len(hashtags_summary) > 0:
                hashtags_summary = sorted(hashtags_summary, key=operator.itemgetter('count'), reverse=True)
                others_hashtags = 0
                for item in hashtags_summary[20:]:
                    others_hashtags += item['count']

                hashtags_summary = hashtags_summary[0: 20]
                hashtags_summary.append({'name': 'Others', 'count': str(others_hashtags)})

            length_summary.append({'name': '1 To 50', 'screen_name': user['text'], 'count': user_length[0]['count']})
            length_summary.append({'name': '51 To 100', 'screen_name': user['text'], 'count': user_length[1]['count']})
            length_summary.append({'name': '101 To 150', 'screen_name': user['text'], 'count': user_length[2]['count']})
            length_summary.append({'name': '151 To 200', 'screen_name': user['text'], 'count': user_length[3]['count']})
            length_summary.append({'name': '201 To 250', 'screen_name': user['text'], 'count': user_length[4]['count']})
            length_summary.append({'name': '251 To 280', 'screen_name': user['text'], 'count': user_length[5]['count']})

            if len(emoji_summary) > 0:
                emoji_summary = list(Counter(emoji_summary).items())
                emoji_summary = [{'name': n, 'count': c} for n, c in emoji_summary]
                emoji_summary = sorted(emoji_summary, key=operator.itemgetter('count'), reverse=True)
                others_emojis = 0
                for item in emoji_summary[30:]:
                    others_emojis += item['count']

                emoji_summary = emoji_summary[0: 30]
                emoji_summary.append({'name': 'Others', 'count': str(others_emojis)})

            if len(retweets_summary) > 0:
                retweets_summary = sorted(retweets_summary, key=operator.itemgetter('count'), reverse=True)
                others_retweets = 0
                for item in retweets_summary[12:]:
                    others_retweets += item['count']

                retweets_summary = retweets_summary[0: 12]
                retweets_summary.append({'name': 'Others', 'count': str(others_retweets)})

            if len(quoted_summary) > 0:
                quoted_summary = sorted(quoted_summary, key=operator.itemgetter('count'), reverse=True)
                others_quoted = 0
                for item in quoted_summary[12:]:
                    others_quoted += item['count']

                quoted_summary = quoted_summary[0: 12]
                quoted_summary.append({'name': 'Others', 'count': str(others_quoted)})

            if len(replies_summary) > 0:
                replies_summary = sorted(replies_summary, key=operator.itemgetter('count'), reverse=True)
                others_replies = 0
                for item in replies_summary[12:]:
                    others_replies += item['count']

                replies_summary = replies_summary[0: 12]
                replies_summary.append({'name': 'Others', 'count': str(others_replies)})

            if len(mentions_summary) > 0:
                mentions_summary = sorted(mentions_summary, key=operator.itemgetter('count'), reverse=True)
                others_mentions = 0
                for item in mentions_summary[12:]:
                    others_mentions += item['count']

                mentions_summary = mentions_summary[0: 12]
                mentions_summary.append({'name': 'Others', 'count': str(others_mentions)})

            users_tweets.append({'user_name': user['text'], 'screen_name': account['screen_name'], 
                                 'hashtags_summary': hashtags_summary, 'emoji_summary': emoji_summary,
                                 'retweets_summary': retweets_summary, 'quoted_summary': quoted_summary,
                                 'replies_summary': replies_summary, 'mentions_summary': mentions_summary})
            
    return render_template('profile_compare.html',
        accounts=accounts,
        compare_tweets=json.dumps(compare_tweets),
        compare_followers=json.dumps(compare_followers),
        compare_following=json.dumps(compare_following),
        compare_likes=json.dumps(compare_likes),
        lang_summary=lang_summary,
        length_summary=length_summary,
        daily_tweets=daily_tweets,
        weekly_tweets=weekly_tweets,
        users_tweets=users_tweets,
        user_data=users,
        year=datetime.now().year)


@app.template_filter('format_datetime')
def _jinja2_filter_datetime(date, format=None):
    if type(date) == str:
        date = parser.parse(date)
    return date.strftime(format) if format else date.strftime("%I:%M:%S %p - %d %b %Y")
    

@app.route('/profile_viewer', methods=['GET', 'POST'])
def profile_viewer():
    screen_name = request.args.get('screen_name')
    tweets_count = 200
    
    search_params = {
        'keywords': '',
        'from_date': '',
        'to_date': '',
        'results_size': '10',
        'tweets_types': '1',
        'sort_by': '1',
        'sort_desc': True
    }

    if request.method == 'POST':
        if 'tweets_count' in request.form:
            # reload all data from API
            tweets_count = int(request.form['tweets_count'])
            
            db.profiles.remove({'screen_name': screen_name}, 1)
            db.user_lists.remove({'user.screen_name': screen_name})
            db.tweets.remove({'user.screen_name': screen_name})
        else:
            # filter from db
            search_params['keywords'] = request.form['keywords']
            search_params['from_date'] = request.form['from_date']
            search_params['to_date'] = request.form['to_date']
            search_params['results_size'] = request.form['results_size']
            search_params['tweets_types'] = request.form['tweets_types']
            search_params['sort_by'] = request.form['sort_by']
            search_params['sort_desc'] = True if 'sort_desc' in request.form else False

    if profiles.find({'screen_name': screen_name}).count() == 0:
        account = api.get_user(screen_name=screen_name)
        profiles.insert_one(account)
        
        if not account['protected']:
            user_sub_lists = api.get_user_lists(screen_name)
            if len(user_sub_lists) > 0:
                user_lists.insert_many(user_sub_lists)

    account = profiles.find({'screen_name': screen_name})
    account = list(account)[0]
    account_time_zone = html_functions.format_time_zone(account)

    user_sub_lists = user_lists.find({'user.screen_name': screen_name})
    user_sub_lists = list(user_sub_lists)

    if account['protected']:
        return render_template('profile_viewer.html',
            account=account,
            account_time_zone = account_time_zone,
            filtered_tweets=[],
            tweets_summary=[],
            results_summary=[],
            daily_tweets=[],
            weekly_tweets=[],
            classifications=[],
            custom_list=[],
            year=datetime.now().year)

    if tweets.find({'user.screen_name': screen_name}).count() == 0:
        if tweets_count > account['statuses_count']:
            tweets_count = account['statuses_count']

        chunks_count = tweets_count // 200
        if tweets_count % 200 > 0:
            chunks_count = chunks_count + 1

        user_timeline = api.get_user_timeline(screen_name=screen_name, count=str(200), max_id=None)
        for indexer in range(1, chunks_count):
            buffer = api.get_user_timeline(screen_name=screen_name, count=str(200), max_id=user_timeline[len(user_timeline) - 1]['id_str'])
            del buffer[0]
            user_timeline = user_timeline + buffer
    
        for tweet in user_timeline:
            tweet['created_time'] = parser.parse(tweet['created_at'])
            tweet['total_interactions'] = tweet['retweet_count'] + tweet['favorite_count']
            tweets.insert_one(tweet)

    # Build tweets summary
    tweets_summary = {
        'first_tweet_datetime': '',
        'last_tweet_datetime': '',
        'total_tweets': 0,
        'total_retweets': 0,
        'total_quoted_tweets': 0,
        'total_replies_tweets': 0
    }

    first_tweet = tweets.find({'user.screen_name': screen_name}, {'created_time': 1}).sort("_id", -1).limit(1)
    first_tweet = list(first_tweet)[0]
    tweets_summary['first_tweet_datetime'] = first_tweet['created_time']

    last_tweet = tweets.find({'user.screen_name': screen_name}, {'created_time': 1}).sort("_id", 1).limit(1)
    last_tweet = list(last_tweet)[0]
    tweets_summary['last_tweet_datetime'] = last_tweet['created_time']

    total_tweets = tweets.aggregate([{'$match': {'user.screen_name': screen_name}}, 
                             {'$group': {'_id': None, 'count': {'$sum': 1}}}])
    total_tweets = list(total_tweets)
    tweets_summary['total_tweets'] = total_tweets[0]['count']

    total_retweets = tweets.aggregate([{'$match': 
                             { '$and' : [{ 'user.screen_name': screen_name }, { 'retweeted_status': { '$exists': True} }] }}, 
                             {'$group': {'_id': None, 'count': {'$sum': 1}}}])
    total_retweets = list(total_retweets)
    if len(total_retweets) > 0:
        tweets_summary['total_retweets'] = total_retweets[0]['count']

    total_quoted_tweets = tweets.aggregate([{'$match': 
                             { '$and' : [{ 'user.screen_name': screen_name }, { 'quoted_status': { '$exists': True} }] }}, 
                             {'$group': {'_id': None, 'count': {'$sum': 1}}}])
    total_quoted_tweets = list(total_quoted_tweets)
    if len(total_quoted_tweets) > 0:
        tweets_summary['total_quoted_tweets'] = total_quoted_tweets[0]['count']

    total_replies_tweets = tweets.aggregate([{'$match': 
                             { '$and' : [{ 'user.screen_name': screen_name }, { 'in_reply_to_screen_name': { '$ne': None} }] }}, 
                             {'$group': {'_id': None, 'count': {'$sum': 1}}}])
    total_replies_tweets = list(total_replies_tweets)
    if len(total_replies_tweets) > 0:
        tweets_summary['total_replies_tweets'] = total_replies_tweets[0]['count']

    # Build search criteria
    search_criteria = [{'$match': { '$and' : [{ 'user.screen_name': screen_name }] } },
                       {'$addFields': { "full_text_length" : {"$strLenCP" : "$full_text"}} },
                       {'$sort': { 'total_interactions' if search_params['sort_by'] == '1' else 'created_time' if search_params['sort_by'] == '2' else 'full_text_length': -1 if search_params['sort_desc'] else 1 } },
                       {'$limit': int(search_params['results_size'])}]

    if search_params['from_date'] != '' and search_params['to_date'] != '':
        search_criteria[0]['$match']['$and'].append({ 'created_time': { '$gte': parser.parse(search_params['from_date'], dayfirst=True), '$lte': parser.parse(search_params['to_date'], dayfirst=True) } })
        
    if search_params['tweets_types'] == '1':
        search_criteria[0]['$match']['$and'].append({ 'retweeted_status': { '$exists': False} })
        search_criteria[0]['$match']['$and'].append({ 'quoted_status': { '$exists': False} })
    elif search_params['tweets_types'] == '3':
        search_criteria[0]['$match']['$and'].append({ 'quoted_status': { '$exists': False} })
    elif search_params['tweets_types'] == '4':
        search_criteria[0]['$match']['$and'].append({ 'retweeted_status': { '$exists': False} })
    elif search_params['tweets_types'] == '5':
        search_criteria[0]['$match']['$and'].append({ 'retweeted_status': { '$exists': True} })
    elif search_params['tweets_types'] == '6':
        search_criteria[0]['$match']['$and'].append({ 'quoted_status': { '$exists': True} })
    elif search_params['tweets_types'] == '7':
        search_criteria[0]['$match']['$and'].append({ 'in_reply_to_screen_name': { '$ne': None} })

    if search_params['keywords'] != '':
        search_criteria[0]['$match']['$and'].append({ '$text': {'$search': search_params['keywords'] } })

    filtered_tweets = tweets.aggregate(search_criteria)
    filtered_tweets = list(filtered_tweets)
    
    results_summary = {
        'first_tweet_datetime': datetime.now(),
        'last_tweet_datetime': datetime.now(),
        'total_tweets': 0 if len(filtered_tweets) == 0 else len(filtered_tweets),
        'total_retweets': 0,
        'total_quoted_tweets': 0,
        'total_replies_tweets': 0
    }

    daily_tweets = []
    for hour in range(0, 24):
        daily_tweets.append({'name': hour, 'statuses_count': 0})

    weekly_tweets = []
    week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in week_days:
        weekly_tweets.append({'name': day, 'statuses_count': 0})

    tweets_langs = tweets.aggregate([{'$match': { 'user.screen_name': screen_name  }}, 
                             {'$group': {'_id': '$lang', 'count': {'$sum': 1}}}])
    tweets_langs = list(tweets_langs)
    if len(tweets_langs) > 0:
        tweets_langs = sorted(tweets_langs, key=operator.itemgetter('count'), reverse=True)

    retweets_summary = []
    quoted_summary = []
    replies_summary = []
    mentions_summary = []
    hashtags_summary = []
    emoji_summary = []
    length_summary = [{'name': '1 To 50', 'count': 0}, {'name': '51 To 100', 'count': 0},
                      {'name': '101 To 150', 'count': 0}, {'name': '151 To 200', 'count': 0},
                      {'name': '201 To 250', 'count': 0}, {'name': '251 To 280', 'count': 0}]
    frequent_words = []
    lang_summary = []
    for tweet in filtered_tweets:
        if tweet['created_time'] <= results_summary['first_tweet_datetime']:
            results_summary['first_tweet_datetime'] = tweet['created_time']
        if tweet['created_time'] >= results_summary['last_tweet_datetime']:
            results_summary['last_tweet_datetime'] = tweet['created_time']
        if 'retweeted_status' in tweet:
            results_summary['total_retweets'] += 1
        if 'quoted_status' in tweet:
            results_summary['total_quoted_tweets'] += 1
        if tweet['in_reply_to_screen_name'] != None:
            results_summary['total_replies_tweets'] += 1

        weekly_tweets[datetime.weekday(tweet['created_time'])]['statuses_count'] += 1
        daily_tweets[tweet['created_time'].hour]['statuses_count'] += 1

        if 'retweeted_status' in tweet:
            emojis = re.findall(emoji_pattern, tweet['retweeted_status']['full_text'] + tweet['retweeted_status']['quoted_status']['full_text'] if 'quoted_status' in tweet['retweeted_status'] else tweet['retweeted_status']['full_text'])
        else:
            emojis = re.findall(emoji_pattern, tweet['full_text'])

        emojis = list(''.join(emojis))
        emoji_summary.extend(emojis)

        languaes.detected_tweet_lang(tweet, lang_summary, tweets_langs, account['lang'])

        if 'retweeted_status' in tweet:
            tweet_length = len(tweet['retweeted_status']['full_text']) + len(tweet['retweeted_status']['quoted_status']['full_text']) if 'quoted_status' in tweet['retweeted_status'] else len(tweet['retweeted_status']['full_text'])
        else:
            tweet_length = len(tweet['full_text'])
            
        if tweet_length >= 0 and tweet_length <= 50:
            length_summary[0]['count'] += 1
        elif tweet_length > 50 and tweet_length <= 100:
            length_summary[1]['count'] += 1
        elif tweet_length > 100 and tweet_length <= 150:
            length_summary[2]['count'] += 1
        elif tweet_length > 150 and tweet_length <= 200:
            length_summary[3]['count'] += 1
        elif tweet_length > 200 and tweet_length <= 250:
            length_summary[4]['count'] += 1
        elif tweet_length > 250:
            length_summary[5]['count'] += 1
            
        if 'retweeted_status' in tweet:
            (i, item) = next(((i, item) for (i, item) in enumerate(retweets_summary) if item['name'] == tweet['retweeted_status']['user']['screen_name']), (None, False))
            if not item:
                retweets_summary.append({'name': tweet['retweeted_status']['user']['screen_name'], 'count': 1})
            else:
                retweets_summary[i]['count'] += 1

        if 'quoted_status' in tweet:
            (i, item) = next(((i, item) for (i, item) in enumerate(quoted_summary) if item['name'] == tweet['quoted_status']['user']['screen_name']), (None, False))
            if not item:
                quoted_summary.append({'name': tweet['quoted_status']['user']['screen_name'], 'count': 1})
            else:
                quoted_summary[i]['count'] += 1

        if tweet['in_reply_to_screen_name'] != None:
            (i, item) = next(((i, item) for (i, item) in enumerate(replies_summary) if item['name'] == tweet['in_reply_to_screen_name']), (None, False))
            if not item:
                replies_summary.append({'name': tweet['in_reply_to_screen_name'], 'count': 1})
            else:
                replies_summary[i]['count'] += 1

        if 'user_mentions' in tweet['entities']:
            for mention in tweet['entities']['user_mentions']:
                (i, item) = next(((i, item) for (i, item) in enumerate(mentions_summary) if item['name'] == mention['name']), (None, False))
                if not item:
                    mentions_summary.append({'name': mention['name'], 'count': 1})
                else:
                    mentions_summary[i]['count'] += 1

        if 'hashtags' in tweet['entities']:
            for hashtag in tweet['entities']['hashtags']:
                (i, item) = next(((i, item) for (i, item) in enumerate(hashtags_summary) if item['name'] == hashtag['text']), (None, False))
                if not item:
                    hashtags_summary.append({'name': hashtag['text'], 'count': 1})
                else:
                    hashtags_summary[i]['count'] += 1

    if len(emoji_summary) > 0:
        emoji_summary = list(Counter(emoji_summary).items())
        emoji_summary = [{'name': n, 'count': c} for n, c in emoji_summary]
        emoji_summary = sorted(emoji_summary, key=operator.itemgetter('count'), reverse=True)
        others_emojis = 0
        for item in emoji_summary[30:]:
            others_emojis += item['count']

        emoji_summary = emoji_summary[0: 30]
        emoji_summary.append({'name': 'Others', 'count': str(others_emojis)})

    if len(lang_summary) > 0:
        lang_summary = sorted(lang_summary, key=operator.itemgetter('count'), reverse=True)

    if len(retweets_summary) > 0:
        retweets_summary = sorted(retweets_summary, key=operator.itemgetter('count'), reverse=True)
        others_retweets = 0
        for item in retweets_summary[12:]:
            others_retweets += item['count']

        retweets_summary = retweets_summary[0: 12]
        retweets_summary.append({'name': 'Others', 'count': str(others_retweets)})

    if len(quoted_summary) > 0:
        quoted_summary = sorted(quoted_summary, key=operator.itemgetter('count'), reverse=True)
        others_quotes = 0
        for item in quoted_summary[12:]:
            others_quotes += item['count']

        quoted_summary = quoted_summary[0: 12]
        quoted_summary.append({'name': 'Others', 'count': str(others_quotes)})

    if len(replies_summary) > 0:
        replies_summary = sorted(replies_summary, key=operator.itemgetter('count'), reverse=True)
        others_replies = 0
        for item in replies_summary[12:]:
            others_replies += item['count']

        replies_summary = replies_summary[0: 12]
        replies_summary.append({'name': 'Others', 'count': str(others_replies)})

    if len(mentions_summary) > 0:
        mentions_summary = sorted(mentions_summary, key=operator.itemgetter('count'), reverse=True)
        others_mentions = 0
        for item in mentions_summary[12:]:
            others_mentions += item['count']

        mentions_summary = mentions_summary[0: 12]
        mentions_summary.append({'name': 'Others', 'count': str(others_mentions)})

    if len(hashtags_summary) > 0:
        hashtags_summary = sorted(hashtags_summary, key=operator.itemgetter('count'), reverse=True)
        others_hashtags = 0
        for item in hashtags_summary[20:]:
            others_hashtags += item['count']

        hashtags_summary = hashtags_summary[0: 20]
        hashtags_summary.append({'name': 'Others', 'count': str(others_hashtags)})

    classifications = profile_cats.aggregate([{'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
    classifications = list(classifications)

    custom_list = custom_lists.aggregate([{'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
    custom_list = list(custom_list)

    user_classifications = []
    if 'classification_types' in account:
        user_classifications = profile_cats.aggregate([{'$match': { 'id': {'$in': account['classification_types']} }}, {'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
        user_classifications = list(user_classifications)

    user_custom_list = []
    if 'custom_list' in account:
        user_custom_list = custom_lists.aggregate([{'$match': { 'id': {'$in': account['custom_list']} }}, {'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
        user_custom_list = list(user_custom_list)
        
    return render_template('profile_viewer.html',
        account=account,
        account_time_zone = account_time_zone,
        user_sub_lists=user_sub_lists,
        filtered_tweets=filtered_tweets,
        tweets_summary=tweets_summary,
        lang_summary=lang_summary,
        results_summary=results_summary,
        search_params=search_params,
        daily_tweets=json.dumps(daily_tweets),
        weekly_tweets=json.dumps(weekly_tweets),
        retweets_summary=json.dumps(retweets_summary),
        quoted_summary=json.dumps(quoted_summary),
        replies_summary=json.dumps(replies_summary),
        mentions_summary=json.dumps(mentions_summary),
        hashtags_summary=json.dumps(hashtags_summary),
        emoji_summary=json.dumps(emoji_summary),
        length_summary=json.dumps(length_summary),
        classifications=classifications,
        custom_list=custom_list,
        user_classifications=user_classifications,
        user_custom_list=user_custom_list,
        year=datetime.now().year)


@app.route('/profile_classification')
def profile_classification():
    classifications = profile_cats.aggregate([{'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
    classifications = list(classifications)

    accounts = list(profiles.aggregate([{'$project': {'_id': 0, 'id': {"$concat" : "$id_str"}, "text" : {"$concat" : "$name"}, 'profile_image_url': 1} }, {'$sort': { 'text': 1 } }]))

    return render_template('profile_classification.html',
        classifications=classifications,
        accounts=accounts,
        year=datetime.now().year)


@app.route('/add_profiles_to_classification', methods=['POST'])
def add_profiles_to_classification():
    user_data = json.loads(request.data.decode('utf-8'))
    
    if len(user_data['classification_types']) == 0 or len(user_data['profiles']) == 0:
        return jsonify(results={})
    
    for item in user_data['profiles']:
        account = profiles.find({'id_str': item['id']})
        account = list(account)[0]
        if 'classification_types' in account:
            if int(user_data['classification_types']) not in account['classification_types']:
                profiles.update({"screen_name": account['screen_name'] }, {'$push' : {"classification_types": int(user_data['classification_types'])}})
        else:
            profiles.update({"screen_name": account['screen_name'] }, {'$set' : {"classification_types": [int(user_data['classification_types'])]}})
            
    user_profiles = profiles.aggregate([{'$match': { 'classification_types': {'$in': [int(user_data['classification_types'])]} }}, {'$project': {'_id': 0, 'id': {"$concat" : "$id_str"}, "text" : {"$concat" : "$name"}, 'profile_image_url': 1} }])
    user_profiles = list(user_profiles)
    
    return jsonify(results={'profiles': user_profiles})

@app.route('/get_profiles_of_classification', methods=['GET'])
def get_profiles_of_classification():
    classification = request.args.get('classification')

    user_profiles = profiles.aggregate([{'$match': { 'classification_types': {'$in': [int(classification)]} }}, {'$project': {'_id': 0, 'id': {"$concat" : "$id_str"}, "text" : {"$concat" : "$name"}, 'profile_image_url': 1} }])
    user_profiles = list(user_profiles)
    
    return jsonify(results={'profiles': user_profiles})


@app.route('/delete_profile_from_classification', methods=['GET'])
def delete_profile_from_classification():
    classification = request.args.get('classification')
    user_id = request.args.get('user_id')

    profiles.update({"id_str": user_id }, {'$pull' : {"classification_types": int(classification)}})
    
    return jsonify(message='Item deleted successfully !!!')


@app.route('/profile_custom_list')
def profile_custom_list():
    lists = custom_lists.aggregate([{'$project': {'_id': 0, 'id': 1, "text" : {"$concat" : "$name"}} }])
    lists = list(lists)

    accounts = list(profiles.aggregate([{'$project': {'_id': 0, 'id': {"$concat" : "$id_str"}, "text" : {"$concat" : "$name"}, 'profile_image_url': 1} }, {'$sort': { 'text': 1 } }]))

    return render_template('profile_custom_list.html',
        lists=lists,
        accounts=accounts,
        year=datetime.now().year)


@app.route('/add_profiles_to_list', methods=['POST'])
def add_profiles_to_list():
    user_data = json.loads(request.data.decode('utf-8'))
    
    if len(user_data['list_types']) == 0 or len(user_data['profiles']) == 0:
        return jsonify(results={})
    
    for item in user_data['profiles']:
        account = profiles.find({'id_str': item['id']})
        account = list(account)[0]
        if 'custom_list' in account:
            if int(user_data['list_types']) not in account['custom_list']:
                profiles.update({"screen_name": account['screen_name'] }, {'$push' : {"custom_list": int(user_data['list_types'])}})
        else:
            profiles.update({"screen_name": account['screen_name'] }, {'$set' : {"custom_list": [int(user_data['list_types'])]}})
            
    user_profiles = profiles.aggregate([{'$match': { 'custom_list': {'$in': [int(user_data['list_types'])]} }}, {'$project': {'_id': 0, 'id': {"$concat" : "$id_str"}, "text" : {"$concat" : "$name"}, 'profile_image_url': 1} }])
    user_profiles = list(user_profiles)
    
    return jsonify(results={'profiles': user_profiles})

@app.route('/get_profiles_of_list', methods=['GET'])
def get_profiles_of_list():
    list_ = request.args.get('list')

    user_profiles = profiles.aggregate([{'$match': { 'custom_list': {'$in': [int(list_)]} }}, {'$project': {'_id': 0, 'id': {"$concat" : "$id_str"}, "text" : {"$concat" : "$name"}, 'profile_image_url': 1} }])
    user_profiles = list(user_profiles)
    
    return jsonify(results={'profiles': user_profiles})


@app.route('/delete_profile_from_list', methods=['GET'])
def delete_profile_from_list():
    list_ = request.args.get('list')
    user_id = request.args.get('user_id')

    profiles.update({"id_str": user_id }, {'$pull' : {"custom_list": int(list_)}})
    
    return jsonify(message='Item deleted successfully !!!')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    lastupdate = datetime.now().replace(microsecond=0).strftime("%I:%M %p")

    if request.method == 'POST':
        rate_limit_status = api.get_rate_limit_status()
        os.remove('Fleed/static/data/rate_limit_status.json')
        f = open('Fleed/static/data/rate_limit_status.json','w')
        json.dump(rate_limit_status, f)
        f.close()
    else:
        if not os.path.isfile('Fleed/static/data/rate_limit_status.json'):
            rate_limit_status = api.get_rate_limit_status()
            f = open('Fleed/static/data/rate_limit_status.json','w')
            json.dump(rate_limit_status, f)
            f.close()
        else:
            f_ctime = os.path.getctime('Fleed/static/data/rate_limit_status.json')
            f_ctime = datetime.fromtimestamp(f_ctime)
            t_now = datetime.now()

            minutes = (t_now - f_ctime).total_seconds() / 60

            if minutes < 15:
                f = open('Fleed/static/data/rate_limit_status.json','r')  
                rate_limit_status = json.load(f)
                f.close()
                lastupdate = f_ctime.replace(microsecond=0).strftime("%I:%M %p")
            else:
                rate_limit_status = api.get_rate_limit_status()
                os.remove('Fleed/static/data/rate_limit_status.json')
                f = open('Fleed/static/data/rate_limit_status.json','w')
                json.dump(rate_limit_status, f)
                f.close()
                
    list_of_dicts = []
    tree_helper.dict_traversal_leafs(rate_limit_status['resources'], list_of_dicts)
    data = []
    for value in list_of_dicts:
        if value['limit'] != value['remaining']:
            data.append({ 'Url': value['url'], 'Type': 'Limit', 'Value': value['limit']})
            data.append({ 'Url': value['url'], 'Type': 'Remaining', 'Value': value['remaining']})

    return render_template('admin/index.html',
        lastupdate=lastupdate,
        data=json.dumps(data),
        year=datetime.now().year)


@app.route('/admin/summary', methods=['GET', 'POST'])
def summary():
    lastupdate = datetime.now().replace(microsecond=0).strftime("%I:%M %p")

    if request.method == 'POST':
        rate_limit_status = api.get_rate_limit_status()
        os.remove('Fleed/static/data/rate_limit_status.json')
        f = open('Fleed/static/data/rate_limit_status.json','w')
        json.dump(rate_limit_status, f)
        f.close()
    else:
        if not os.path.isfile('Fleed/static/data/rate_limit_status.json'):
            rate_limit_status = api.get_rate_limit_status()
            f = open('Fleed/static/data/rate_limit_status.json','w')
            json.dump(rate_limit_status, f)
            f.close()
        else:
            f_ctime = os.path.getctime('Fleed/static/data/rate_limit_status.json')
            f_ctime = datetime.fromtimestamp(f_ctime)
            t_now = datetime.now()

            minutes = (t_now - f_ctime).total_seconds() / 60

            if minutes < 15:
                f = open('Fleed/static/data/rate_limit_status.json','r')
                rate_limit_status = json.load(f)
                f.close()
                lastupdate = f_ctime.replace(microsecond=0).strftime("%I:%M %p")
            else:
                rate_limit_status = api.get_rate_limit_status()
                os.remove('Fleed/static/data/rate_limit_status.json')
                f = open('Fleed/static/data/rate_limit_status.json','w')
                json.dump(rate_limit_status, f)
                f.close()

    list_of_dicts = []
    tree_helper.dict_traversal_leafs(rate_limit_status['resources'], list_of_dicts)
    return render_template('admin/summary.html',
        lastupdate=lastupdate,
        rate_limit_status=list_of_dicts,
        year=datetime.now().year)
