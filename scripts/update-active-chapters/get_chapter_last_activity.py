import tweepy as tweepy
from dateutil.relativedelta import relativedelta
from tweepy import TweepError

__author__ = "Lorena Mesa"
__email__ = "lorena@pyladies.com"

import base64
import csv
import datetime
import time
from functools import wraps
from os import getenv
from os.path import join, dirname
from pathlib import Path
import requests
from urllib.parse import urlencode

from dotenv import load_dotenv
from geopy import OpenCage
import gspread
from gspread import SpreadsheetNotFound
from oauth2client.service_account import ServiceAccountCredentials
import tweepy
import yaml

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

CURRENT_DIR = Path(__file__).parent.resolve()

# Setup .env variables
GMAIL_ACCOUNT_NAME = getenv('GMAIL_ACCOUNT_NAME')
GMAIL_ACCOUNT_PASSWORD = getenv('GMAIL_ACCOUNT_PASSWORD')
GOOGLE_CREDENTIALS_FILE = getenv('GOOGLE_CREDENTIALS_FILE')
MEETUP_CLIENT_ID = getenv('MEETUP_CLIENT_ID')
MEETUP_CLIENT_SECRET = getenv('MEETUP_CLIENT_SECRET')
MEETUP_REDIRECT_URI = getenv('MEETUP_REDIRECT_URI')
GITHUB_TOKEN = getenv('GITHUB_TOKEN')
OPEN_CAGE_API_KEY = getenv('OPEN_CAGE_API_KEY')
TWITTER_CONSUMER_KEY = getenv('TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = getenv('TWITTER_CONSUMER_SECRET')
TWITTER_ACCESS_TOKEN = getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = getenv('TWITTER_ACCESS_SECRET')

# Ratelimiting defaults
MAX_MEETUP_REQUESTS_PER_HOUR = 200

# Datetime for csv
TODAY_DATE = datetime.datetime.now().strftime('%Y_%m_%d')
TODAY = datetime.datetime.now()
ONE_YEAR_AGO = TODAY - datetime.timedelta(days=365)
ONE_YEAR_AGO_DATESTR = ONE_YEAR_AGO.strftime('%Y-%m-%d')
TWO_MONTHS_FROM_NOW_DATESTR = (TODAY + datetime.timedelta(days=60)).strftime('%Y-%m-%d')

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
    def get_most_recent_event(self, chapter_name, start_date=None, end_date=None):
        """
        :param  chapter_name: meetup chapter urlnames
        e.g. meetup.com/Chicago-Pyladies/ the urlname is 'Chicago-Pyladies'
        :param  start_date: str represented YYYY-MM-DD
        :param  end_date: str represented YYYY-MM-DD
        :return dict with date and url of most recent event
        """
        events_endpoint = f'{MeetUpApi.api_url}/{chapter_name}/events'

        query_params = {
            'page': 1,
            'desc': 1,
            'status': 'upcoming,past'
        }
        if start_date:
            query_params['no_earlier_than'] = start_date
        if end_date:
            query_params['no_later_than'] = end_date

        query_string = urlencode(query_params)

        events_endpoint = f'{events_endpoint}/?{query_string}'

        try:
            response = requests.get(
                events_endpoint,
                headers={'Authorization': f'Bearer {self.token}'}
            )
            if response.ok:
                return True, response
            return False, response
        except Exception as e:
            raise e

class GoogleSheetsAPI(object):
    def __init__(self, scope, credentials_file):
        self.scope = scope
        self.credentials_file = credentials_file

    def get_client(self):
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, self.scope)
        self.client = gspread.authorize(creds)

    def _get_sheet(self, sheet):
        return self.client.open(sheet)

    def get_worksheet_by_title(self, sheet, worksheet_title):
        try:
            sheet = self._get_sheet(sheet)
        except SpreadsheetNotFound:
            raise SpreadsheetNotFound

        worksheet = list(filter(lambda sheet: sheet.title == worksheet_title, sheet.worksheets()))

        if len(worksheet):
            return worksheet[0]
        else:
            return None

class OpenCageApi(object):
    def __init__(self, api_key):
        self.geolocator = OpenCage(api_key=api_key)

    def get_location_information(self, lat=None, long=None, city=None, country=None):
        location = None
        if lat and long:
            location = self.geolocator.reverse(query=(lat, long))
        elif city or country:
            location = self.geolocator.geocode(query=f'{city} {country}')
        return {
            'country': location.raw.get('components').get('country'),
            'continent': location.raw.get('components').get('continent'),
            'latitude': location.latitude,
            'longitude': location.longitude,
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

    if not chapters:
        return False

    chapters_file = f'{CURRENT_DIR}/pyladies_meetup_chapters.yml'
    with open(chapters_file, 'w+') as f:
        f.write(chapters)

    return True

if __name__ == "__main__":
    print('Starting script ...')

    # Set names for directories & worksheets
    pyladies_group_sheet = 'User_Download_07072020_105237' #input('What is the name of the most reecent PyLadies user download sheet? (e.g. User_Download_07072020_105237)')
    pyladies_chapter_directory_sheet = 'PyLadies Chapter Directory'
    pyladies_chapter_directory_worksheet = 'PyLadies Chapter Directory Form Resp - Nov 2019'

    # Insantiate Google Sheets Client
    gsheets_api = GoogleSheetsAPI(
        scope=[
            'https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'
        ],
        credentials_file=GOOGLE_CREDENTIALS_FILE
    )
    gsheets_api.get_client()

    # Load all of PyLadies/Groups emails
    print('Downloading PyLadies/Groups emails...')
    last_download = None
    try:
        last_download = gsheets_api.get_worksheet_by_title(
            sheet=pyladies_group_sheet, worksheet_title=pyladies_group_sheet
        )
    except SpreadsheetNotFound:
        print(f'Download sheet: {pyladies_group_sheet} not found')

    if not last_download:
        print('Unable to download PyLadies/Groups emails')
        exit(-1)

    last_download_data = last_download.get_all_records()

    google_pyladies_emails = list(map(
        lambda record: {
            'email': record.get('Email Address [Required]'),
            'last_sign_in': record.get('Last Sign In [READ ONLY]'),
            'name': f'{record.get("First Name [Required]")} {record.get("Last Name [Required]")}',
        },
        last_download_data
    ))

    # Load all PyLadies Directory emails
    print('Downloading Directory emails...')
    chapter_sheets = None
    try:
        chapter_sheets = gsheets_api.get_worksheet_by_title(
            sheet=pyladies_chapter_directory_sheet, worksheet_title=pyladies_chapter_directory_worksheet
        )
    except SpreadsheetNotFound:
        print(f'Download sheet: {pyladies_group_sheet} not found')

    chapter_sheets_data = chapter_sheets.get_all_records()
    if not chapter_sheets_data:
        print('Unable to download PyLadies Directory emails')
        exit(-1)

    pyladies_directory_emails = list(map(
        lambda record: {
            'email': record.get('What is your PyLadies official email?'),
            'event_page': record.get('What is your chapter\'s MeetUp / website for listing events?').split(',')
            if record.get('What is your chapter\'s MeetUp / website for listing events?') else '',
            'directory_website': record.get('If applicable, what is your chapter\'s website?')
            if record.get('If applicable, what is your chapter\'s website?') else '',
            'language': record.get('What is the main spoken language of your chapter?').split(',')
            if record.get('What is the main spoken language of your chapter?') else '',
            'organizers': record.get('What are the organizer(s) name(s)?').split(',')
            if record.get('What are the organizer(s) name(s)?') else '',
            'city': record.get('What city is your chapter located in?')
            if record.get('What city is your chapter located in?') else '',
            'country': record.get('What country is your chapter located in?')
            if record.get('What country is your chapter located in?') else '',
            'name': record.get('What is your chapter name?')
            if record.get('What is your chapter name?') else '',
            'registered_in_directory': 'yes'
        },
        chapter_sheets_data
    ))

    # Load all PyLadies emails from website
    if not GITHUB_TOKEN:
        GITHUB_TOKEN = input('To download the PyLadies MeetUp chapters, '
                             'please provide a GitHub token with repo '
                             'access privileges.\n')
    print('Downloading website emails...')

    chapter_file = download_pyladies_chapters(GITHUB_TOKEN)

    if not chapter_file:
        print('Cannot load website config file')
        exit(-1)

    with open(f'{CURRENT_DIR}/pyladies_meetup_chapters.yml', 'r') as stream:
        website_chapter_data = yaml.safe_load(stream)

        website_chapter_emails = list(map(
        lambda record: {
            'email': record.get('email'),
            'website': record.get('website') if record.get('external_website')
            else f'https://pyladies.com/locations/{record.get("website")}',
            'meetup': record.get('meetup'),
            'twitter': record.get('twitter'),
            'latitude': record.get('lat') if record.get('location') else '',
            'longitude': record.get('lon') if record.get('location') else '',
            'image': f'https://pyladies.com/assets/images/{record.get("image")}'
            if record.get('image') else ''
        },
        website_chapter_data.get('chapters')
    ))

    email_to_google, email_to_directory, email_to_website = {}, {}, {}
    for chapter in google_pyladies_emails:
        email_to_google[chapter.get('email')] = chapter

    for chapter in pyladies_directory_emails:
        email_to_directory[chapter.get('email')] = chapter

    for chapter in website_chapter_emails:
        email_to_website[chapter.get('email')] = chapter

    print('Merging chapter information...')
    merged_chapter_data = []
    for email, chapter in email_to_google.items():
        new_chapter = {**chapter, **email_to_directory.get(email, {}), **email_to_website.get(email, {})}
        merged_chapter_data.append(new_chapter)

    meetup_api = MeetUpApi(
        client_id=MEETUP_CLIENT_ID,
        client_secret=MEETUP_CLIENT_SECRET,
        redirect_uri=MEETUP_REDIRECT_URI
    )
    token_obtained = meetup_api.get_bearer_token()
    if not token_obtained:
        print('Unable to obtain token, exiting ...')
        exit(-1)

    tweepy_auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    tweepy_auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
    twitter_api = tweepy.API(tweepy_auth)

    headers = ['email', 'last_sign_in', 'name', 'event_page', 'directory_website', 'language', 'organizers',
               'city', 'country', 'website', 'meetup', 'twitter', 'last_tweet_date', 'last_tweet_link',
               'latitude', 'longitude', 'image', 'continent', 'last_event_date', 'last_event_link',
               'registered_in_directory', 'active']
    with open(f'merged_chapter_data_{TODAY_DATE}.csv', 'w') as csvfile:

        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        geolocator = OpenCageApi(OPEN_CAGE_API_KEY)
        counter = 0
        for chapter in merged_chapter_data:
            if chapter.get('twitter'):
                twitter_name = chapter.get('twitter').strip('@')
                latest_status = None
                try:
                    latest_status = twitter_api.user_timeline(screen_name=twitter_name, count=1, include_rts=False)
                except TweepError as e:
                    print(f'Unable to get twitter name {twitter_name} status. Removing.')
                    chapter['twitter'] = None
                    continue

                if latest_status:
                    latest_status = latest_status[0]
                    chapter['last_tweet_date'] = latest_status.created_at.strftime('%Y-%m-%d')
                    chapter['last_tweet_link'] = f'https://twitter.com/{twitter_name}/statuses/{latest_status.id_str}'
                    chapter['twitter'] = f'https://twitter.com/{twitter_name}'

            meetup_name = chapter.get('meetup')
            if not meetup_name:
                if chapter.get('event_page'):
                    event_pages = chapter.get('event_page')
                    meetup_name = list(filter(lambda p: 'meetup' in p, event_pages))
                    if len(meetup_name) >= 1:
                        parsed_name = meetup_name[0]
                        parsed_name = parsed_name.rstrip('/')   # Remove trailing slash if full url includes trailing
                        parsed_name = parsed_name.split('/')[-1]
                        if parsed_name:
                            meetup_name = parsed_name

            chapter['meetup'] = f'https://meetup.com/{meetup_name}' if meetup_name else ''
            if chapter['meetup']:
                counter += 1
                print(counter, chapter['meetup'])
            chapter['last_event_date'], chapter['last_event_link'] = '', ''
            if meetup_name:
                _, meetup_resp = meetup_api.get_group(meetup_name)

                if meetup_resp.status_code == 404:
                    print(f'Chapter {meetup_name} has no meetup, deleting info')
                    chapter['meetup'] = None
                    continue

                meetup_resp = meetup_resp.json()
                chapter['latitude'] = meetup_resp.get('lat')
                chapter['longitude'] = meetup_resp.get('lon')

                print(f'Retrieving last event data for: {meetup_name}')
                start_date=ONE_YEAR_AGO
                completed, event_resp = meetup_api.get_most_recent_event(
                    meetup_name, start_date=ONE_YEAR_AGO_DATESTR, end_date=TWO_MONTHS_FROM_NOW_DATESTR
                )

                if completed:
                    event_resp = event_resp.json()
                    if len(event_resp) >= 1:
                        event_resp = event_resp[0]
                        chapter['last_event_date'] = event_resp.get('local_date')
                        chapter['last_event_link'] = event_resp.get('link')

            print(f'Retrieving country info for chapter: {chapter.get("name", "")}')

            location_info = None
            if chapter.get('latitude') and chapter.get('longitude'):
                location_info = geolocator.get_location_information(
                    lat=chapter.get('latitude'), long=chapter.get('longitude')
                )
            elif chapter.get('city') or chapter.get('country'):
                location_info = geolocator.get_location_information(
                    country=chapter.get('country'), city=chapter.get('city')
                )

            if location_info:
                chapter['latitude'] = location_info.get('latitude')
                chapter['longitude'] = location_info.get('longitude')
                chapter['country'] = location_info.get('country')
                chapter['continent'] = location_info.get('continent')

            last_sign_in = chapter.get('last_sign_in').lower()
            last_login = None
            if last_sign_in != 'never logged in':
                try:
                    last_login = datetime.datetime.strptime(last_sign_in, '%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    last_login = datetime.datetime.strptime(last_sign_in, '%Y/%m/%d %H:%M:%S')

            # Determine if active using email activity
            if chapter.get('last_event_date'):
                chapter['active'] = True
            elif chapter.get('last_tweet_date') and \
                    ONE_YEAR_AGO <= datetime.datetime.strptime(chapter.get('last_tweet_date'), '%Y-%m-%d') <= TODAY:
                chapter['active'] = True
            elif last_login and  ONE_YEAR_AGO <= last_login <= TODAY:
                chapter['active'] = True
            elif (
                    chapter.get('last_sign_in').lower() == 'never logged in' and
                    chapter.get('registered_in_directory', 'no') == 'no'
            ):
                chapter['active'] = False
            elif last_login <= ONE_YEAR_AGO:
                chapter['active'] = False

            row_to_write = {}
            for header in headers:
                row_to_write[header] = chapter.get(header)

            print(f'Writing row {chapter.get("name")}')
            writer.writerow(row_to_write)
