from bs4 import BeautifulSoup
import requests
import re
import pandas as pd

# get source code & soup it
source = requests.get('https://yle.fi/uutiset/18-204933').text
soup = BeautifulSoup(source, 'lxml')

# get article
article = soup.find('div', class_='yle__article__listItem__textualContent')


def parse_yle_articles():
    # create dataframe for content
    yle_articles = pd.DataFrame(columns=['date', 'title', 'lead', 'category'])

    # lists for article pieces
    dates = []
    titles = []
    leads = []
    categories = []

    for article in soup.find_all('article'):

        # get date
        date = soup.find('time', class_='yle__article__listItem__meta__published')['datetime']
        date = pd.Series(date.split('T')[0])

        # get title
        title = article.h1.text

        # get lead of article
        lead = article.p.text

        # get category
        category = soup.find(
            'span', class_=re.compile(r'yle__subject yle__borderColor')).text

        # append lists
        dates.append(date)
        titles.append(title)
        leads.append(lead)
        categories.append(category)

    # append everything to pd dataframe
    yle_articles['date'] = dates
    yle_articles['title'] = titles
    yle_articles['lead'] = leads
    yle_articles['category'] = categories

    return yle_articles


def split_words(object):  # figure out how to split series of strings
    pass


def most_used_words(splitwords):  # count most used words (keywords)
    pass
