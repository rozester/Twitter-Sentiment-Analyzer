from langdetect import detect

def detected_tweet_lang(tweet, lang_summary, tweets_langs, account_lang):
    try:
        if 'retweeted_status' in tweet:
            context = tweet['retweeted_status']['full_text'] + tweet['retweeted_status']['quoted_status']['full_text'] if 'quoted_status' in tweet['retweeted_status'] else tweet['retweeted_status']['full_text']
        else:
            context = tweet['full_text']

        context = ' '.join(word for word in context.split() if not (word.startswith('#') or word.startswith('@') or word.startswith('http://') or word.startswith('https://')))
        tweet['tweet_length'] = len(context)
        if len(context) < 60:
            detected_lang = tweet['lang']
        else:
            detected_lang = detect(context)

        tweet['detected_lang'] = detected_lang
        (i, item) = next(((i, item) for (i, item) in enumerate(lang_summary) if item['name'] == detected_lang), (None, False))
        if not item:
            lang_summary.append({'name': detected_lang, 'count': 1})
        else:
            lang_summary[i]['count'] += 1
    except:
        if 'und' in lang_summary:
            lang_summary['und']['count'] += 1
        else:
            lang_summary.append({'name': 'und', 'count': 1})
        tweet['detected_lang'] = 'und'