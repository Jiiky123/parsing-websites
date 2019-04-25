import requests
from urllib.request import urlopen
import numpy as np
import re
import pandas as pd
import json
import os
from collections import Counter
import matplotlib.pyplot as plt

# CLASS FUNCTIONS ------------------------------------------------------------

# __init__(query, search, limit=20000, offset=0, language='sv')
# category is the category you are looking for in articles
# limit is number of articles
# offset if you want to start from a given nr of articles
# languages are swedish=sv, finnish=fi, english=en

# save_excel(query, filename, loc)
# example: articles.save_excel('sports', '../data/')

# most_common_words(query, word=None)
# gives a list of 150 most common words in category
# word=None can be changed if you want to know count of specific word

# word_over_time(query, *words, c='b')
# takes unlimited words as argument
# plots all words and their popularity over time


# GET ARTICLES AND CREATE DATAFRAME---------------------------------------------


class GetArticles:

    def __init__(query, category, limit=20000, offset=0, language='sv'):
        query.category = category
        query.limit = limit
        query.offset = offset
        query.language = language

        # grab url and get source (notice in URL: limit, offset, query)
        url = 'https://yle-fi-search.api.yle.fi/v1/search?app_id=\
        hakuylefi_v2_prod&app_key=4c1422b466ee676e03c4ba9866c0921f&\
        language={}&limit={}&offset={}&query={}'.format(
            query.language, query.limit,
            query.offset, query.category)

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

        # make dataframe accessible within class
        query.articles = articles

        # location and shape
        print('Articles with query {}'.format(query.category))
        print('Shape of dataframe: ', query.articles.shape)
        print('Shape of dataframe: ', query.articles.info())

    # -------------------------------------------------------------------------

    # GET MOST COMMON WORDS BY SEARCHWORD--------------------------------------

    def most_common_words(query, word=None):

        # create counter with collections Counter()
        results = Counter()

        # split strings to words, lowercase and move to results set/counter
        query.articles.headline.astype(str).str.lower().str.split().apply(results.update)
        query.articles.lead.astype(str).str.lower().str.split().apply(results.update)

        # print out words most common
        print('Most common words in {}'.format(query.category))
        print('# of articles: ', len(query.articles.headline))

        if word is not None:
            print('Your exact word \'{}\' got mentioned'.format(word), results.get(word), 'times')

        count = 0
        for item in results.most_common():
            if count < 100:
                print(item)
                count += 1

    # -------------------------------------------------------------------------

    # WORD POPULARITY OVER TIME-------------------------------------------------

    def word_over_time(query, *words, c='b'):

        # make everything lowercase and split strings into wordlists
        query.articles.headline = query.articles.headline.astype(str).str.lower()
        query.articles.lead = query.articles.lead.astype(str).str.lower()

        # lists for needed objects
        dates = []
        counts = []

        # lists go in here when filled
        words_overtime = pd.DataFrame(columns=['date', 'occurrences'])

        # loop through wordlists and count occurrence
        for word in words:
            for date, counth, countl in zip(query.articles.index, query.articles.headline, query.articles.lead):
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
    def save_excel(query, namefile, loc):
        query.articles.to_excel('{}{}.xlsx'.format(loc, namefile),
                                sheet_name=query.search)
        print('{}.xlsx saved in {}'.format(namefile, loc))

# -----------------------------------------------------------------------------


if __name__ == '__main__':
    sport_artiklar = GetArticles('sport')
    sport_artiklar.most_common_words('fotboll')
    sport_artiklar.word_over_time('fotboll', 'hockey', 'innebandy')
else:
    print('run from another script')
