from bs4 import BeautifulSoup
import requests
from urllib.request import urlopen
import re
import pandas as pd
import json
import os
os.chdir('D:/PythonProjektATOM/Git/Repositories/parsing-websites/YLEparsing')

# grab url and get source (notice in URL: limit, offset, query)
url = 'https://yle-fi-search.api.yle.fi/v1/search?app_id=hakuylefi_v2_prod&app_key=4c1422b466ee676e03c4ba9866c0921f&language=fi&limit=1000&offset=0&query=talous'
with urlopen(url) as response:
    source = response.read()

data = json.loads(source.decode('utf-8'))
# print(json.dumps(data, indent=2))


def get_articles():

    # list of items in articles
    dates = []
    headlines = []
    leads = []
    authors = []

    for item in data['data']:  # fill lists
        try:
            date = item['datePublished'].replace('\u2009', '')
            headline = item['headline'].replace('\u2009', '')
            lead = item['lead'].replace('\u2009', '')
            author = ''.join(item['author'])
        except KeyError:
            print('data not found')

        # append to lists
        dates.append(date)
        headlines.append(headline)
        leads.append(lead)
        authors.append(author)

    # move everything to pandas dataframe
    talous_articles = pd.DataFrame(
        columns=['date', 'headline', 'lead', 'author'])
    talous_articles.date = dates
    talous_articles.headline = headlines
    talous_articles.lead = leads
    talous_articles.author = authors

    # clean up data
    talous_articles = talous_articles.drop_duplicates(subset='headline')
    talous_articles.date = pd.to_datetime(
        talous_articles.date, format='%Y-%m-%d', errors='coerce').dt.date
    talous_articles.sort_values('date', inplace=True, ascending=False)
    talous_articles.set_index('date', inplace=True)

    # finally save to excel
    talous_articles.to_excel('yle_articles.xlsx')
    print('saved as xlsx file')


get_articles()
