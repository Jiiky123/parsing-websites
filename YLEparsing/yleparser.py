from bs4 import BeautifulSoup
import requests
from urllib.request import urlopen
import numpy as np
import re
import pandas as pd
import json
import os
from collections import Counter
import matplotlib.pyplot as plt
os.chdir('D:/PythonProjektATOM/Git/Repositories/parsing-websites/YLEparsing/')

# CLASS FUNCTIONS ------------------------------------------------------------

# __init__(searchword, search, limit=20000, offset=0, language='sv')
# search is the category you are looking for
# limit is number of articles
# offset if you want to start from a given nr of articles
# languages are swedish=sv, finnish=fi, english=en

# save_excel(searchword, filename, loc)
# example: articles.save_excel('sports', '../data/')

# most_common_words(searchword, word=None)
# gives a list of 150 most common words in category
# word=None can be changed if you want to know count of specific word

# word_over_time(searchword, *words, c='b')
# takes unlimited words as argument
# plots all words and their popularity over time


# GET ARTICLES AND CREATE DATAFRAME-------------------------------------------


class GetArticles:

    def __init__(searchword, search, limit=20000, offset=0, language='sv'):

        searchword.search = search
        searchword.limit = limit
        searchword.offset = offset
        searchword.language = language

        # grab url and get source (notice in URL: limit, offset, query)
        url = 'https://yle-fi-search.api.yle.fi/v1/search?app_id=hakuylefi_v2_prod&app_key=4c1422b466ee676e03c4ba9866c0921f&language={}&limit={}&offset={}&query={}'.format(
            searchword.language, searchword.limit, searchword.offset, searchword.search)

        with urlopen(url) as response:
            source = response.read()

        # load and decode json file
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
                pass

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

        searchword.articles = articles

        # # finally save to excel
        # articles.to_excel('articleData/yle_articles_{}.xlsx'.format(searchword),
        #                   sheet_name=searchword)

        # location and shape
        print('Articles with searchword {}'.format(searchword.search))
        print('Shape of dataframe: ', searchword.articles.shape)
        print('Shape of dataframe: ', searchword.articles.info())

    # -------------------------------------------------------------------------

    # GET MOST COMMON WORDS BY SEARCHWORD--------------------------------------

    def most_common_words(searchword, word=None):

        # create counter with collections Counter()
        results = Counter()

        # split strings to words, lowercase and move to results set/counter
        searchword.articles.headline.astype(str).str.lower().str.split().apply(results.update)
        searchword.articles.lead.astype(str).str.lower().str.split().apply(results.update)

        # print out words most common
        print('Most common words in {}'.format(searchword.search))
        print('# of articles: ', len(searchword.articles.headline))

        if word is not None:
            print('Your exact word \'{}\' got mentioned'.format(word), results.get(word), 'times')

        count = 0
        for item in results.most_common():
            if count < 100:
                print(item)
                count += 1

    # -------------------------------------------------------------------------

    # WORD POPULARITY OVER TIME-------------------------------------------------

    def word_over_time(searchword, *words, c='b'):

        # make everything lowercase and split strings into wordlists
        searchword.articles.headline = searchword.articles.headline.astype(str).str.lower()
        searchword.articles.lead = searchword.articles.lead.astype(str).str.lower()

        # lists for needed objects
        dates = []
        counts = []

        # lists go in here when filled
        words_overtime = pd.DataFrame(columns=['date', 'occurrences'])

        # loop through wordlists and count occurrence
        for word in words:
            for date, counth, countl in zip(searchword.articles.index, searchword.articles.headline, searchword.articles.lead):
                count1 = len(re.findall(r'\b{}\w*'.format(word), counth))
                count2 = len(re.findall(r'\b{}\w*'.format(word), countl))
                dates.append(date)
                counts.append(count1 + count2)

            # append pd dataframe and append lists
            words_overtime.date = dates
            words_overtime.occurrences = counts
            words_overtime.set_index('date', inplace=True)
            words_overtime.index = pd.to_datetime(words_overtime.index)
            words_overtime = words_overtime.resample('Q').sum()  # d/W/M/Q/y
            words_overtime.index = words_overtime.index.astype('O')

            # plot current word in loop
            plt.plot(words_overtime.index, words_overtime.occurrences,
                     label='\'{}\''.format(word), c=c)

            # print out word occurrence
            print('Your word \'{}\' got mentioned'.format(word),
                  words_overtime.occurrences.sum(), 'times')

            # empty lists & dataframe before looping over next word
            dates = []
            counts = []
            words_overtime = pd.DataFrame(columns=['date', 'occurrences'])

            # randomize plot color for next word
            c = np.random.rand(3,)

        plt.legend()
        plt.title('Word popularity over time')
        plt.tight_layout()
        plt.show()

# ------------------------------------------------------------------------------

# SAVE TO EXCEL---------------------------------------------------------------
    def save_excel(searchword, namefile, loc):
        searchword.articles.to_excel('{}{}.xlsx'.format(loc, namefile),
                                     sheet_name=searchword.search)
        print('{}.xlsx saved in {}'.format(namefile, loc))

# -----------------------------------------------------------------------------


sport_artiklar = GetArticles('sport')
sport_artiklar.save_excel(
    'lol', 'D:/PythonProjektATOM/Git/Repositories/parsing-websites/YLEparsing/articleData/')
# sport_artiklar.most_common_words('fotboll')
# sport_artiklar.word_over_time('fotboll', 'hockey', 'innebandy')
