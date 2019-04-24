from bs4 import BeautifulSoup
import requests
from urllib.request import urlopen
import re
import pandas as pd
import json
import os
from collections import Counter
os.chdir('D:/PythonProjektATOM/Git/Repositories/parsing-websites/YLEparsing/')

# Get articles and create article dataframe----------------------------------


def get_articles(searchword, limit, offset=0):

    # grab url and get source (notice in URL: limit, offset, query)
    url = 'https://yle-fi-search.api.yle.fi/v1/search?app_id=hakuylefi_v2_prod&app_key=4c1422b466ee676e03c4ba9866c0921f&language=fi&limit={}&offset={}&query={}'.format(
        limit, offset, searchword)

    with urlopen(url) as response:
        source = response.read()

    # decode json file
    data = json.loads(source.decode('utf-8'))

    # lists of items we need from articles
    dates = []
    headlines = []
    leads = []
    authors = []

    for item in data['data']:
        try:  # replace problematic characters
            date = item['datePublished'].replace('\u2009', '')
            headline = item['headline'].replace('\u2009', '')
            lead = item['lead'].replace('\u2009', '')
            author = ''.join(item['author'])
        except KeyError:
            print('data missing - continue')

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
    articles.to_excel('articleData/yle_articles_{}.xlsx'.format(searchword),
                      sheet_name=searchword)

    # location and shape
    print('Saved as yle_articles_{}.xlsx'.format(searchword))
    print('Shape of dataframe: ', articles.shape)

    return articles


# ----------------------------------------------------------------------------

# Print out most common words-----------------------------------------------
def most_common_words(category):
    # import article df
    words_df = pd.read_excel('articleData/yle_articles_{}.xlsx'.format(category))

    # create counter with collections Counter()
    results = Counter()

    # split strings to words, lowercase and move to results set/counter
    words_df.headline.astype(str).str.lower().str.split().apply(results.update)
    words_df.lead.astype(str).str.lower().str.split().apply(results.update)

    # print out words most common
    print('Most common words in yle_articles_{}.xlsx:'.format(category))
    print('# of articles: ', len(words_df.headline))
    for item in results.most_common():
        print(item)


# ----------------------------------------------------------------------------

get_articles('pietarsaari', 20000)
most_common_words('pietarsaari')
