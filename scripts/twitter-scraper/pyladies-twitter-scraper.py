#!/usr/bin/env python
#  -*- coding: utf-8 -*-

"""
script to generate PyLadies twitter .csv with the following information:
- twitter screen name
- description
- expanded tweet profile url
- date of last tweet

To use you'll need to register a Twitter app at developer.twtter.com and insert the following values in the `.env` file:
- CLIENT_ID
- CLIENT_SECRET

You can run from the commandline with: pyladies-twitter-scraper.py
"""

__author__ = "Lorena Mesa"
__email__ = "lorena@pyladies.com"

import base64
import csv
from datetime import datetime
from dotenv import load_dotenv
from os import getenv
from os.path import join, dirname
import requests
from requests_oauthlib import OAuth2
from urllib.parse import quote_plus
import sys

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Setup twitter tokens
CLIENT_ID = getenv('CLIENT_ID')
CLIENT_SECRET = getenv('CLIENT_SECRET')

# Twitter Specific Info
TWITTER_API = 'https://api.twitter.com'
MAX_USER_RESULTS = 1000
MAX_USER_COUNT = 20
PYLADIES_LOCATIONS_LIST = 'pyladies-locations'


def get_bearer_token(client_id, client_secret):
    credentials = f'{quote_plus(client_id)}:{quote_plus(client_secret)}'.encode('utf-8')
    bearer_token = base64.b64encode(credentials).decode('utf-8')

    response = requests.post(url=f'{TWITTER_API}/oauth2/token',
                            headers=
                            {
                                'Authorization': f'Basic {bearer_token}',
                                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
                            },
                            data={'grant_type': 'client_credentials'})
    if response.ok:
        return response.json()

    raise Exception('Unable to obtain Twitter bearer token.')


def build_request(url, search_params):
    twitter_api = f'{TWITTER_API}/1.1'

    try:
        token = get_bearer_token(CLIENT_ID, CLIENT_SECRET)
    except Exception as e:
        print(f'Stopping script: {e}')
        sys.exit(1)

    request = requests.get(
        url=f'{twitter_api}/{url}',
        auth=OAuth2(
            client_id=CLIENT_ID,
            token=dict(access_token=token.get('access_token'), token_type='bearer')
        ),
        params=search_params
    )
    return request


def make_request(num_requests, url, search_params, page_number, key):
    data = []

    for i in range(1, num_requests + 1):
        if page_number:
            search_params['page'] = f'{i}'

        response = build_request(url=url, search_params=search_params)

        if response.ok:
            response = response.json()
            if key:
                data += response.get(key)
            elif isinstance(response, dict):
                data.append(response)
            else:
                data += response
    return data

def get_pyladies_handles(data):
    return list(map(
        lambda result: result.get('screen_name'),
        data
    ))

if __name__ == "__main__":
    # Get PyLadies twitter handles data from Twitter API
    print('Getting known PyLadies Locations list members...')
    pyladies_lists = make_request(
        num_requests=1,
        url='lists/list.json',
        search_params={'screen_name': 'pyladies'},
        page_number=False,
        key=None
    )

    pyladies_lists = [a_list.get('id') for a_list in pyladies_lists if PYLADIES_LOCATIONS_LIST in a_list.get('full_name')]

    known_pyladies_handles = make_request(
        num_requests=1,
        url='lists/members.json',
        search_params={'list_id': f'{pyladies_lists[0]}', 'skip_status': True, 'count': 5000},
        page_number=False,
        key='users'
    )

    print('Done getting known PyLadies Locations handles...')

    print('Searching...')
    pyladies_user_search_handles = make_request(
        num_requests=MAX_USER_RESULTS // MAX_USER_COUNT,
        url='users/search.json',
        search_params={'q': 'pyladies'},
        page_number=True,
        key=None
    )

    pyladies_tweets_search_handles = make_request(
        num_requests=100,
        url='search/tweets.json',
        search_params={'q': 'pyladies'},
        page_number=False,
        key='statuses'
    )
    print('Done searching!')

    # Flatten into set of unique handles
    known_pyladies_handles = get_pyladies_handles(known_pyladies_handles)

    pyladies_user_search_handles = get_pyladies_handles(pyladies_user_search_handles)

    pyladies_tweets_search_handles = list(map(
        lambda result: result.get('user').get('screen_name'),
        pyladies_tweets_search_handles
    ))

    unique_pyladies_handles = known_pyladies_handles + pyladies_user_search_handles + pyladies_tweets_search_handles

    unique_pyladies_handles = set(
        filter(lambda screen_name: 'pyladies' in screen_name.lower(), unique_pyladies_handles)
    )

    # Write list to csv
    print('Writing...')
    with open('pyladies_twitter_handles.csv', mode='w') as csv_file:
        fieldnames = ['screen_name', 'description', 'url', 'last_tweeted']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for twitter_handle in unique_pyladies_handles:

            twitter_user = make_request(
                num_requests=1,
                url='users/show.json',
                search_params={'screen_name': f'{twitter_handle}'},
                page_number=False,
                key=None
            )

            last_tweet = make_request(
                num_requests=1,
                url='statuses/user_timeline.json',
                search_params={'screen_name': f'{twitter_handle}', 'count': 1},
                page_number=False,
                key=None
            )

            desciption = twitter_user[0].get('description')

            if twitter_user[0].get('entities') and twitter_user[0].get('entities').get('url'):
                url = twitter_user[0].get('entities').get('url').get('urls')[0].get('expanded_url')
            else:
                url = ''

            if last_tweet:
                last_tweet_timestamp = last_tweet[0].get('created_at')
                last_tweet_timestamp = datetime.strptime(last_tweet_timestamp, '%a %b %d %H:%M:%S +0000 %Y')
                last_tweet_timestamp = last_tweet_timestamp.date().strftime('%m/%d/%Y')
            else:
                last_tweet_timestamp = ''

            writer.writerow(
                {
                    'screen_name': twitter_handle,
                    'description': desciption,
                    'url': url,
                    'last_tweeted': last_tweet_timestamp
                }
            )
    print('Done writing!')
