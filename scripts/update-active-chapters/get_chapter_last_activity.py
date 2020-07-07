import base64
from os import getenv
from os.path import join, dirname
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

__author__ = "Lorena Mesa"
__email__ = "lorena@pyladies.com"


import gspread
from gspread import SpreadsheetNotFound, Cell
from oauth2client.service_account import ServiceAccountCredentials

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
            'meetup': f'https://meetup.com/{record.get("meetup")}' if record.get('meetup') else '',
            'twitter': f'https://twitter.com/{record.get("twitter")}' if record.get('twitter') else '',
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
    for email, chapter in email_to_google:
        new_chapter = {**chapter, **email_to_directory.get(email), **email_to_website.get(email)}
        print(new_chapter)

