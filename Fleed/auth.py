from Fleed import secrets

import oauth2

oauth2_consumer = oauth2.Consumer(key=secrets.consumer_key, secret=secrets.consumer_secret)
oauth2_token = oauth2.Token(key=secrets.access_token, secret=secrets.access_token_secret)
client = oauth2.Client(oauth2_consumer, oauth2_token)
