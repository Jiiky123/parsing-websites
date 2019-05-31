import WordLists
from collections import Counter
from tweepy.streaming import StreamListener
from tweepy import Cursor
from tweepy import API
from tweepy import OAuthHandler
from tweepy import Stream
import twitter_credentials
import numpy as np
import pandas as pd
import os
import time
import re
from datetime import date
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DayLocator, DateFormatter, HourLocator
import matplotlib.animation as animation
from yahoo_fin import stock_info as si
plt.style.use('dark_background')

# make path relative to script
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


class TwitterAuthenticator:

    def authenticate_twitter_app():
        auth = OAuthHandler(twitter_credentials.CONSUMER_KEY, twitter_credentials.CONSUMER_SECRET)
        auth.set_access_token(twitter_credentials.ACCESS_TOKEN,
                              twitter_credentials.ACCESS_TOKEN_SECRET)
        return auth


class UserTweetFetcher:  # inspect specific twitter users
    def __init__(self, twitter_user=None):
        self.auth = TwitterAuthenticator.authenticate_twitter_app()
        self.twitter_client = API(self.auth)
        self.twitter_user = twitter_user

    def get_twitter_client_api(self):
        return self.twitter_client

    def get_user_timeline_tweets(self, num_tweets):
        tweets = []
        for tweet in Cursor(self.twitter_client.user_timeline, id=self.twitter_user).items(num_tweets):
            tweets.append(tweet)
        return tweets

    def get_friend_list(self, num_friends):
        friend_list = []
        for friend in Cursor(self.twitter_client.friends, id=self.twitter_user).items(num_friends):
            friend_list.append(friend)
        return friend_list

    def get_home_timeline_tweets(self, num_tweets):
        home_timeline_tweets = []
        for tweet in Cursor(self.twitter_client.home_timeline, id=self.twitter_user).items(num_tweets):
            home_timeline_tweets.append(tweet)
        return home_timeline_tweets


class TwitterStreamer:
    def __init__(self):
        self.twitter_authenticator = TwitterAuthenticator()

    def stream_tweets(self, fetched_tweets_filename, hash_tag_list):
        # This handles API stuff
        listener = TwitterListener(fetched_tweets_filename)
        auth = self.twitter_authenticator.authenticate_twitter_app()
        stream = Stream(auth, listener)

        stream.filter(track=hash_tag_list)


class TwitterListener(StreamListener):  # stream tweets

    def __init__(self, fetched_tweets_filename):
        self.fetched_tweets_filename = fetched_tweets_filename

    def on_data(self, data):
        try:
            print(data)
            with open(self.fetched_tweets_filename, 'a') as tf:
                tf.write(data)
            return True
        except BaseException as e:
            print('Error on data: {}'.format(str(e)))

    def on_error(self, status):
        if status == 420:
            # Return False on on_data method in case rate limit occur
            return False
        print(status)


class TweetFetcher:

    def get_tweets(query, items=30000, count=200):
        auth = TwitterAuthenticator.authenticate_twitter_app()
        api = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        df = pd.DataFrame(columns=['date', 'message', 'retweets'])

        date = []
        message = []
        retweets = []

        try:  # try except block for the case of rate_limit
            tweepy_tweet = Cursor(api.search, q=query,
                                  result_type='recent', include_rts=False, tweet_mode='extended',
                                  since='2019-5-23', count=count).items(items)
            for tweet in tweepy_tweet:  # exclude tweets with RT @
                if 'RT @' not in str(tweet.full_text.encode('utf-8', 'ignore')):
                    date.append(tweet.created_at)
                    message.append(str(tweet.full_text.encode('utf-8', 'ignore')))
                    retweets.append(tweet.retweet_count)

            message = [x.replace('b\'', '') for x in message]  # clean tweet
            temp_df = pd.DataFrame({'date': date, 'message': message,
                                    'retweets': retweets})
            df = df.append(temp_df)
            df.set_index('date', inplace=True)
            df.drop_duplicates(subset='message', inplace=True)

        except BaseException as e:
            print('error on data: {}'.format(str(e)))

        print('query: ', query)
        print('{} tweets fetched'.format(len(df)))
        return df


class TweetAnalysis:

    def words_count(df, neg_words, pos_words, plot=True):
        results = Counter()  # stores word-count pairs
        df.message = df.message.str.replace('\.', '')
        df.message = df.message.str.replace('\_', '')
        df.message = df.message.str.replace('\#', '')
        df.message = df.message.str.replace('\&', '')
        df.message = df.message.str.replace('\$', '')
        df.message = df.message.str.replace('\(', '')
        df.message = df.message.str.replace('\)', '')
        df.message = df.message.str.replace('\@', '')
        df.message = df.message.str.replace('\!', '')
        df.message = df.message.str.replace('\:', '')
        df.message = df.message.str.replace('\;', '')
        df.message = df.message.str.replace('\\', '')
        df.message = df.message.str.replace('\/', '')
        df.message = df.message.str.replace('x80', '')
        df.message = df.message.str.replace('xe2', '')
        df.message = df.message.str.replace('x94', '')
        df.message = df.message.str.replace('x86', '')
        df.message = df.message.str.replace('daxx98', '')
        df.message.astype(str).str.lower().str.split().apply(results.update)

        print(results)
        # make tweet.text lowercase for regex
        df.message = df.message.astype(str).str.lower()
        # count negative words
        neg_word_count = []
        neg_word_dates = []

        for word in neg_words:
            for date, words, retweets in zip(df.index, df.message, df.retweets):
                count = len(re.findall(r'\b{}\w*'.format(word), words))
                if retweets == 0:
                    neg_word_count.append(count)
                else:
                    neg_word_count.append(count*retweets)
                neg_word_dates.append(date)

        neg_word_df = pd.DataFrame(
            {'date': neg_word_dates, 'neg_words': neg_word_count})

        print('# of bearish words: ', neg_word_df.neg_words.sum())

        # count positive words
        pos_word_list = []
        pos_word_dates = []

        for word in pos_words:
            for date, words, retweets in zip(df.index, df.message, df.retweets):
                count = len(re.findall(r'\b{}\w*'.format(word), words))
                if retweets == 0:
                    pos_word_list.append(count)
                else:
                    pos_word_list.append(count*retweets)
                pos_word_dates.append(date)

        pos_word_df = pd.DataFrame(
            {'date': pos_word_dates, 'pos_words': pos_word_list})

        print('# of bullish words: ', pos_word_df.pos_words.sum())

        # sort both df's
        neg_word_df.sort_values('date', inplace=True)
        pos_word_df.sort_values('date', inplace=True)
        neg_word_df = neg_word_df.reset_index(drop=True)
        pos_word_df = pos_word_df.reset_index(drop=True)
        print('START: ', neg_word_df.date.head(1))
        print('END: ', neg_word_df.date.tail(1))

        if plot == True:  # plot pos/neg tweet difference over time
            diff = pos_word_df.pos_words.cumsum() - neg_word_df.neg_words.cumsum()

            f, ax = plt.subplots()
            ax.plot(pos_word_df.index, diff,
                    c='b', label='pos/neg tweet diff')

            plt.legend()
            plt.tight_layout()
            plt.show()

        return neg_word_df, pos_word_df

    def animation(self, i):  # use start_animation()

        self.ax1.clear()
        self.ax2.clear()

        plt.title('Twitter sentiment')
        self.ax1.set_ylabel('tweet sentiment', fontsize=11)
        self.ax2.set_ylabel('stock/index price', fontsize=11)

        # get sentiment words
        pos_words = WordLists.positive_list
        neg_words = WordLists.negative_list

        print('fetching tweets...')
        data = TweetFetcher.get_tweets(self.query, items=20, count=20)
        print('analysing sentiment...')
        neg, pos = TweetAnalysis.words_count(data, neg_words, pos_words, plot=False)
        diff = pos.pos_words.sum() - neg.neg_words.sum()

        # update stream data for chart
        with open('stream_data.txt', 'r+') as file:
            file_list = file.readlines()
            length = len(file_list)
            new_list = [x.split(',') for x in file_list]
            try:
                if length > 0:
                    if not any(item in str(neg.date) for item in [x[0] for x in new_list]):
                        prev_value = int(new_list[-1][2])
                        file.write('{},{},{},{}\n'.format(neg.iloc[-1, 0], length+1,
                                                          prev_value+diff, TweetAnalysis.stock_price_get(self.pricequery)))
                        print('data updated')
                    else:
                        print('overlap in data')
                else:
                    file.write('{},{},{},{}\n'.format(neg.iloc[-1, 0], length+1,
                                                      diff, TweetAnalysis.stock_price_get(self.pricequery)))
            except BaseException as e:
                print('Data error: ', str(e))

        # read stream data
        pullData = open("stream_data.txt", "r").read()
        dataArray = pullData.split('\n')
        dateX = []
        xar = []
        yar = []
        bar = []
        for eachLine in dataArray:
            if len(eachLine) > 1:
                a, x, y, b = eachLine.split(',')
                dateX.append(a)
                xar.append(int(x))
                yar.append(int(y))
                bar.append(float(b))

        dateX = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S') for x in dateX]
        self.ax1.xaxis.set_major_locator(HourLocator())
        xformatter = matplotlib.dates.DateFormatter('%H:%M')
        self.ax1.xaxis.set_major_formatter(xformatter)
        self.ax1.xaxis.set_minor_formatter(xformatter)
        self.ax2.xaxis.set_major_formatter(xformatter)
        self.ax2.xaxis.set_minor_formatter(xformatter)

        self.ax1.plot(dateX[-1000:], yar[-1000:], c='skyblue', label='tweet sentiment')
        self.ax2.plot(dateX[-1000:], bar[-1000:], c='lightgreen',
                      label='{} price'.format(self.pricequery))

        # buy & sell signals
        if len(yar) >= 6:
            current = yar[-1]
            past = yar[-6]
            sentiment = current - past
            print('sentiment on recent tweets: ', sentiment)
            with open('trade_data.txt', 'a') as trade:

                if (len(yar) >= 6) and sentiment > 22:
                    trade.write('{},{}\n'.format(dateX[-1], sentiment))
                    self.ax1.axvline(dateX[-1], color='green', alpha=0.3)

                elif (len(yar) >= 6) and sentiment < -10:
                    trade.write('{},{}\n'.format(dateX[-1], sentiment))
                    self.ax1.axvline(dateX[-1], color='red', alpha=0.3)

        # keep previous buy & sell signals in chart
        with open('trade_data.txt', 'r') as trade:
            trade = trade.read()
            tradeData = trade.split('\n')

            for eachline in tradeData[-400:]:
                if len(eachline) > 1:
                    x, sent = eachline.split(',')
                    if sent != '' and int(sent) > 22:
                        self.ax1.axvline(x, color='green', alpha=0.3)
                    elif sent != '' and int(sent) < -10:
                        self.ax1.axvline(x, color='red', alpha=0.3)

        self.ax1.legend(loc=2, bbox_to_anchor=(0, 0.95))
        self.ax2.legend(loc=2)

    def stock_price_get(stock):
        price = si.get_live_price(stock)
        return price

    def start_animation(self, query, pricequery, interval=5000):
        fig = plt.figure(figsize=(12, 8))
        self.ax1 = fig.add_subplot(1, 1, 1)
        self.ax2 = self.ax1.twinx()
        self.query = query
        self.pricequery = pricequery

        ani = animation.FuncAnimation(fig, stream.animation, interval=interval)

        plt.show()
        self.save_data()

    def save_data(self):
        dirName = 'Querydata/{}'.format(self.pricequery)
        if not os.path.exists(dirName):
            os.mkdir(dirName)
            print("Directory ", dirName,  " Created ")
        else:
            print("Directory ", dirName,  " already exists")

        if not os.path.exists('Querydata/{}/{}_trade.txt'.format(self.pricequery, date.today())):
            trade_data = open(
                'Querydata/{}/{}_trade.txt'.format(self.pricequery, date.today()), 'w')
            with open('trade_data.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    trade_data.write(line)
            trade_data.close()
            print('new file created')
        else:
            trade_data = open(
                'Querydata/{}/{}_trade.txt'.format(self.pricequery, date.today()), 'a')
            with open('trade_data.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    data.write(line)
            trade_data.close()
            print('file appended')

        if not os.path.exists('Querydata/{}/{}_stream.txt'.format(self.pricequery, date.today())):
            stream_data = open(
                'Querydata/{}/{}_stream.txt'.format(self.pricequery, date.today()), 'w')
            with open('stream_data.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    stream_data.write(line)
            stream_data.close()
            print('new file created')
        else:
            stream_data = open(
                'Querydata/{}/{}_stream.txt'.format(self.pricequery, date.today()), 'a')
            with open('stream_data.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    stream_data.write(line)
            stream_data.close()
            print('file appended')

        open('stream_data.txt', 'w').close()
        open('trade_data.txt', 'w').close()


if __name__ == '__main__':

    query = ('spx OR sp500 OR dax OR dax30 OR nasdaq OR djia OR dowjones OR nyse OR stocks OR equities OR investing')

    stream = TweetAnalysis()
    stream.start_animation(query, '^GDAXI')
