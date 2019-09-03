# PyLadies Twitter Scraper

A Python 3.6+ script, this project both uses the Twitter API to both search for twitter screen names (using the search users and tweets API endpoints) and the [PyLadies twitter location list](https://twitter.com/pyladies/lists/pyladies-locations) to create a a `pyladies_twitter_handles.csv` list including: 

- Screen Name
- Profile Description
- Profile URL
- Date of last tweet

### To Run

1. Register [a twitter app](developer.twtter.com) and insert the following values in the `.env` file: `CLIENT_ID`, `CLIENT_SECRET`
2. Ensure you have installed the libraries from `requirements.txt` via `pip install -r requirements.txt`
3. The script is both a bash executable script: `pyladies-twitter-scraper.py` or with `python` using `python pyladies-twitter-scraper.py`.

### Questions

Contact `lorena@pyladies.com` or reach out in the PyLadies Slack #organisers-resources channel.