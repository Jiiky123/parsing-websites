from bs4 import BeautifulSoup
import requests

source_pos = requests.get(
    'https://www.enchantedlearning.com/wordlist/positivewords.shtml').text

soup_pos = BeautifulSoup(source_pos, "lxml")

positive_list = []

for word in soup_pos.find_all('div', class_='wordlist-item'):
    word = word.text
    positive_list.append(word)

source_neg = requests.get(
    'https://www.enchantedlearning.com/wordlist/negativewords.shtml').text

neg_soup = BeautifulSoup(source_neg, "lxml")

negative_list = []

for word in neg_soup.find_all('div', class_='wordlist-item'):
    word = word.text
    negative_list.append(word)

neg_words = 'bear', 'sell', 'resistance', 'short'
pos_words = 'bull', 'buy', 'support', 'long'

for x in range(len(neg_words)):
    positive_list.append(pos_words[x])
    negative_list.append(neg_words[x])

positive_list = positive_list[42:]
