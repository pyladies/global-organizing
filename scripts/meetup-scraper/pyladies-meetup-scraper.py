#!/usr/bin/env python
#  -*- coding: utf-8 -*-

"""
Script to download PyLadies config.yaml and update the following
MeetUp information, if a chapter has a MeetUp:
- MeetUp name
- MeetUp id
- MeetUp organizers

To use you'll need to register a MeetUp app at
https://secure.meetup.com/meetup_api/oauth_consumers/ and insert the
following values in the `.env` file:
- GITHUB_TOKEN
- MEETUP_CLIENT_ID
- MEETUP_CLIENT_SECRET
- MEETUP_REDIRECT_URI\
- OPEN_CAGE_API_KEY

You can run from the commandline with: pyladies-meetup-scraper.py
"""
import base64
import csv
import time

from dotenv import load_dotenv
from functools import wraps
from os import getenv
from os.path import join, dirname
from pathlib import Path
from urllib.parse import urlencode
import requests
import yaml

from geopy.geocoders import OpenCage


__author__ = "Lorena Mesa"
__email__ = "lorena@pyladies.com"


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

CURRENT_DIR = Path(__file__).parent.resolve()

# Setup env tokens
MEETUP_CLIENT_ID = getenv('MEETUP_CLIENT_ID')
MEETUP_CLIENT_SECRET = getenv('MEETUP_CLIENT_SECRET')
MEETUP_REDIRECT_URI = getenv('MEETUP_REDIRECT_URI')
GITHUB_TOKEN = getenv('GITHUB_TOKEN')
OPEN_CAGE_API_KEY = getenv('OPEN_CAGE_API_KEY')

# Ratelimiting defaults
MAX_MEETUP_REQUESTS_PER_HOUR = 200


def ratelimit(number_times):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            nonlocal number_times

            completed, response = fn(*args, **kwargs)
            number_times = response.headers.get('X-RateLimit-Remaining')
            if not completed and response.status_code == 429:
                seconds_until_reset = int(
                    response.headers.get('X-RateLimit-Reset')
                )

                meetup_errors = response.json().get('errors')
                meetup_errors = [e.get('code') for e in meetup_errors]

                if seconds_until_reset and 'throttled' in meetup_errors:
                    print(f'Throttling {seconds_until_reset} ...')
                    time.sleep(seconds_until_reset)
                    print(f'Trying again ...')
                    completed, response = fn(*args, **kwargs)
                return completed, response

            return completed, response

        return wrapper
    return decorator


class MeetUpApi(object):
    """
    Lightweight wrapper to make requests against MeetUp API.
    """

    api_url = 'https://api.meetup.com'
    api_auth_url = 'https://secure.meetup.com'

    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token = None

    def get_bearer_token(self):
        auth_endpoint = f'{MeetUpApi.api_auth_url}/oauth2/authorize' \
                        f'?client_id={self.client_id}' \
                        f'&redirect_uri={self.redirect_uri}' \
                        f'&response_type=code'
        code = input(f'Visit {auth_endpoint} and enter response code:')

        data = {
            'client_id': f'{self.client_id}',
            'client_secret':  f'{self.client_secret}',
            'redirect_uri': f'{self.redirect_uri}',
            'code': f'{code}',
            'grant_type': 'authorization_code'
        }

        try:
            response = requests.post(
                f'{MeetUpApi.api_auth_url}/oauth2/access',
                data=data
            )
            if response.ok:
                data = response.json()
                self.token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                print(response.status_code, self.token, self.refresh_token)
                return True
            return False
        except Exception as e:
            raise e

    @ratelimit(number_times=MAX_MEETUP_REQUESTS_PER_HOUR)
    def get_groups(self, topic_ids):
        """
        :param  meetup_ids: list of numeric topic_ids
        :return list of pyladies meetup dicts
        """

        query_params = {
            'category': topic_ids,
        }

        query_string = urlencode(query_params)

        find_groups_endpoint = u'{}/{}?{}'.format(
            MeetUpApi.api_url, 'find', 'groups', query_string
        )

        try:
            response = requests.get(
                find_groups_endpoint,
                headers={'Authorization': f'Bearer {self.token}'}
            )
            if response.ok:
                return True, response
            return False, response
        except Exception as e:
            raise e

    @ratelimit(number_times=MAX_MEETUP_REQUESTS_PER_HOUR)
    def get_group(self, chapter_name):
        """
        :param  chapter_name: meetup chapter urlnames
        e.g. meetup.com/Chicago-Pyladies/ the urlname is 'Chicago-Pyladies'
        :return dict of pyladies meetup group info
        """
        group_endpoint = f'{MeetUpApi.api_url}/{chapter_name}'

        try:
            response = requests.get(
                group_endpoint,
                headers={'Authorization': f'Bearer {self.token}'}
            )
            if response.ok:
                return True, response
            return False, response
        except Exception as e:
            raise e

    @ratelimit(number_times=MAX_MEETUP_REQUESTS_PER_HOUR)
    def get_most_recent_event(self, chapter_name):
        """
        :param  chapter_name: meetup chapter urlnames
        e.g. meetup.com/Chicago-Pyladies/ the urlname is 'Chicago-Pyladies'
        :return dict with date and url of most recent event
        """
        group_endpoint = f'{MeetUpApi.api_url}/{chapter_name}/events'

        try:
            response = requests.get(
                group_endpoint,
                headers={'Authorization': f'Bearer {self.token}'}
            )
            if response.ok:
                return True, response
            return False, response
        except Exception as e:
            raise e

class OpenCageApi(object):
    def __init__(self, api_key):
        self.geolocator = OpenCage(api_key=api_key)

    def get_location_information(self, lat, long):
        location = self.geolocator.reverse(query=(lat, long))
        return {
            'country': location.raw.get('components').get('country'),
            'continent': location.raw.get('components').get('continent')
        }

def download_pyladies_chapters(token):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(
        url='https://api.github.com/repos/pyladies/'
            'pyladies/contents/www/config.yml',
        headers=headers
    )

    content = response.json().get('content')
    chapters = str(base64.b64decode(content), 'utf-8')

    chapters_file = f'{CURRENT_DIR}/pyladies_meetup_chapters.yml'
    with open(chapters_file, 'w+') as f:
        f.write(chapters)

    return chapters_file

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        GITHUB_TOKEN = input('To download the PyLadies MeetUp chapters, '
                             'please provide a GitHub token with repo '
                             'access privileges.\n')
    print('Download starting!')

    chapter_file = download_pyladies_chapters(GITHUB_TOKEN)

    if not chapter_file:
        exit(-1)

    with open(chapter_file, 'r') as stream:
        chapter_data = yaml.safe_load(stream)

    meetup_api = MeetUpApi(
        client_id=MEETUP_CLIENT_ID,
        client_secret=MEETUP_CLIENT_SECRET,
        redirect_uri=MEETUP_REDIRECT_URI
    )
    token_obtained = meetup_api.get_bearer_token()
    if not token_obtained:
        print('Unable to obtain token, exiting ...')
        exit(-1)

    for chapter in chapter_data.get('chapters'):
        meetup_url_name = chapter.get('meetup')
        if not meetup_url_name:
            continue

        completed, meetup_resp = meetup_api.get_group(meetup_url_name)

        if meetup_resp.status_code == 404:
            print(f'Chapter {meetup_url_name} has no meetup, deleting info')
            chapter.pop('meetup', None)
            continue

        if not completed:
            print(f'Error {meetup_resp.status_code}, '
                  f'skipping chapter {meetup_url_name}')
            continue

        meetup_resp = meetup_resp.json()

        if isinstance(chapter.get('meetup_id'), int):
            meetup_id = int(chapter.get('meetup_id', 0))
        else:
            meetup_id = 0

        new_meetup_id = id(meetup_resp.get('id', 0))
        if meetup_id != new_meetup_id:
            print(f'MeetUp Chapter {chapter.get("name")} '
                  f'id is wrong {new_meetup_id}')
            chapter['meetup_id'] = new_meetup_id

        if meetup_resp.get('organizer'):
            chapter['organizer'] = meetup_resp.get('organizer').get('name')

        chapter['location'] = {
            'latitude': meetup_resp.get('lat'),
            'longitude': meetup_resp.get('lon')
        }

        if meetup_resp.get('group_photo'):
            chapter['meetup_image'] = meetup_resp\
                .get('group_photo').get('highres_link')

        if meetup_resp.get('pro_network'):
            chapter['pro_network'] = meetup_resp.get('pro_network').get('name')

    with open('pyladies_meetup_locations.csv', 'w') as csvfile:
        chapters = chapter_data.get('chapters')
        writer = csv.DictWriter(csvfile, fieldnames=[
            'continent', 'country', 'email', 'image', 'last event date', 'last event link',
            'latitude', 'longitude', 'meetup', 'name', 'organizer', 'twitter'
        ])
        writer.writeheader()

        geolocator = OpenCageApi(OPEN_CAGE_API_KEY)
        for chapter in chapters:
            latitude = chapter.get('location').get('latitude') if chapter.get('location', '') else ''
            longitude = chapter.get('location').get('longitude') if chapter.get('location', '') else ''

            country = ''
            print(f'Retrieving country info for chapter: {chapter.get("name", "")}')
            if latitude and longitude:
                location_info = geolocator.get_location_information(latitude, longitude)

            print(f'Retrieving last event data for: {chapter.get("name", "")}')
            completed, event_resp = meetup_api.get_most_recent_event(meetup_url_name)

            last_event_date, last_event_link = '', ''
            if not completed:
                print((f'Error {event_resp.status_code}, '
                       f'unable to get chapter {meetup_url_name} event data'))
            else:
                event_resp = event_resp.json()[0]
                last_event_date = event_resp.get('local_time')
                last_event_link = event_resp.get('link')

            chapter_info = {
                'continent': location_info.get('continent') if location_info else '',
                'country': location_info.get('country') if location_info else '',
                'email': chapter.get('email', ''),
                'image': f'https://pyladies.com/assets/images/{chapter.get("image", "")}',
                'last event date': last_event_date,
                'last event link': last_event_link,
                'latitude': latitude,
                'longitude': longitude,
                'meetup': f'https://meetup.com/{chapter.get("meetup", "")}',
                'name': chapter.get('name', ''),
                'organizer': chapter.get('organizer', ''),
                'twitter': chapter.get('twitter', ''),
            }
            writer.writerow(chapter_info)

    with open(chapter_file, 'w') as stream:     # Overwrites original file
        chapter_data = yaml.dump(chapter_data, stream)

    print('Done!')
