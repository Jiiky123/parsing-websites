from bs4 import BeautifulSoup
import requests
from urllib.request import urlopen
import re
import pandas as pd
import json
import os
os.chdir('D:/PythonProjektATOM/Git/Repositories/parsing-websites/YLEparsing/')

# grab url and get source (notice in URL: limit, offset, query)
search_word = 'politiikka'
url = 'https://yle-fi-search.api.yle.fi/v1/search?app_id=hakuylefi_v2_prod&app_key=4c1422b466ee676e03c4ba9866c0921f&language=fi&limit=1000&offset=0&query={}'.format(
    search_word)
with urlopen(url) as response:
    source = response.read()

data = json.loads(source.decode('utf-8'))
# print(json.dumps(data, indent=2))


def get_articles():  # -------------------------------------------------------

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
    articles = pd.DataFrame(
        columns=['date', 'headline', 'lead', 'author'])
    articles.date = dates
    articles.headline = headlines
    articles.lead = leads
    articles.author = authors

    # clean up data
    articles = articles.drop_duplicates(subset='headline')
    articles.date = pd.to_datetime(
        articles.date, format='%Y-%m-%d', errors='coerce').dt.date
    articles.sort_values('date', inplace=True, ascending=False)
    articles.set_index('date', inplace=True)

    # finally save to excel
    articles.to_excel('articleData/yle_articles_{}.xlsx'.format(search_word))
    print('Saved as yle_articles_{}.xlsx'.format(search_word))
    print('Shape: ', articles.shape)


# ----------------------------------------------------------------------------
get_articles()
