# -*- coding: utf-8 -*-

"""
script to generate PyLadies twitter .csv with the following information:
- twitter handle
- description
- expanded tweet profile url
- date of last tweet

To use you'll need to register a Twitter app at developer.twtter.com for the follwing values:
- CLIENT_ID
- CLIENT_SECRET
- ACCESS_TOKEN
- ACCESS_TOKEN_SECRET
"""

__author__ = "Lorena Mesa"
__email__ = "lorena@pyladies.com"

import csv
from datetime import datetime

import json

import requests
from requests_oauthlib import OAuth1


MAX_USER_RESULTS = 1000
MAX_USER_COUNT = 20

CLIENT_ID = 'client-id'
CLIENT_SECRET = 'client-secret'
ACCESS_TOKEN = 'access-token'
ACCESS_TOKEN_SECRET = 'access-token-secret'

PYLADIES_LOCATIONS_LIST = 'pyladies-locations'


def build_request(url, search_params):
	twitter_api = 'https://api.twitter.com/1.1'

	request = requests.get(
		url=f'{twitter_api}/{url}', 
		auth=OAuth1(
			CLIENT_ID,
			CLIENT_SECRET,
			ACCESS_TOKEN,
			ACCESS_TOKEN_SECRET
		),
		params=search_params
	)
	return request

def make_request(num_requests, url, search_params, page_number, key):
	data = []

	for i in range(1, num_requests+1):
		if page_number:
			search_params['page'] = f'{i}'
		
		response = build_request(url=url,search_params=search_params)   

		if response.ok:
			response = response.json()
			if key:
				data += response.get(key)
			elif isinstance(response, dict):
				data.append(response)
			else:
				data += response
	return data


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
pyladies_handles = make_request(
	num_requests=int(MAX_USER_RESULTS/MAX_USER_COUNT),
	url='users/search.json',
	search_params={'q': 'pyladies'},
	page_number=True,
	key=None
)

pyladies_search_handles = make_request(
	num_requests=100,
	url='search/tweets.json',
	search_params={'q': 'pyladies'},
	page_number=False,
	key='statuses'
)
print('Done searching!')

# Flatten into set of unique handles
known_pyladies_handles = list(map(
	lambda result: result.get('screen_name'),
	known_pyladies_handles
))

pyladies_handles = list(map(
	lambda result: result.get('screen_name'),
	pyladies_handles
))

pyladies_search_handles = list(map(
	lambda result: result.get('user').get('screen_name'),
	pyladies_search_handles
))

unique_pyladies_handles = known_pyladies_handles + pyladies_handles + pyladies_search_handles

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
			search_params={'screen_name':f'{twitter_handle}'},
			page_number=False,
			key=None
		)
		last_tweet = make_request(
			num_requests=1,
			url='statuses/user_timeline.json',
			search_params={'screen_name':f'{twitter_handle}', 'count':1},
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

