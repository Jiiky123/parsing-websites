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
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DayLocator, DateFormatter, HourLocator
import matplotlib.animation as animation
from yahoo_fin import stock_info as si
from pytz import timezone
import pytz
plt.style.use('dark_background')

# path relative to script
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


class TwitterAuthenticator:
    # API authentication
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
        for tweet in Cursor(self.twitter_client.user_timeline, id=self.twitter_user, tweet_mode='extended').items(num_tweets):
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
                    # timezone conversion, utc -> helsinki time
                    hels_time = timezone('Europe/Helsinki')
                    created_at = tweet.created_at
                    created_at = pytz.utc.normalize(pytz.utc.localize(
                        created_at, is_dst=None)).astimezone(hels_time)
                    # get rid of info at end of datetime str
                    created_at = created_at.replace(tzinfo=None)
                    date.append(created_at)
                    message.append(str(tweet.full_text.encode('utf-8', 'ignore')))
                    retweets.append(tweet.retweet_count)

            # replace encoding symbols from tweet
            message = [x.replace('b\'', '') for x in message]
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
        # replace symbols to make words easier to count
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
                    # retweeted tweets more weight in calculation
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
        # self.ax2.clear()

        plt.title('Twitter sentiment')
        # self.ax1.set_ylabel('tweet sentiment', fontsize=11)
        self.ax1.set_ylabel('stock/index price', fontsize=11)

        # get sentiment words
        pos_words = WordLists.positive_list
        neg_words = WordLists.negative_list

        print('fetching tweets...')
        data = TweetFetcher.get_tweets(self.query, items=20, count=20)
        print('analysing sentiment...')
        neg, pos = TweetAnalysis.words_count(data, neg_words, pos_words, plot=False)
        diff = pos.pos_words.sum() - neg.neg_words.sum()

        # plot price on every request, sentiment only when no overlap
        boundary = -2000
        with open('index_price.txt', 'a') as index_price:
            index_price.write('{},{}\n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                               TweetAnalysis.stock_price_get(self.pricequery)))

        with open('index_price.txt', 'r') as index:
            index = index.read()
            index = index.split('\n')

            index_dates = []
            index_prices = []

            for x in index:
                if len(x) > 1:
                    index_date, index_price = x.split(',')
                    index_dates.append(index_date)
                    index_prices.append(float(index_price))
            index_dates = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S') for x in index_dates]
            self.ax1.plot(index_dates[boundary:], index_prices[boundary:], c='lightgreen',
                          label='{} price'.format(self.pricequery))

        # update stream data for chart
        with open('stream_data.txt', 'r+') as file:
            file_list = file.readlines()
            length = len(file_list)
            new_list = [x.split(',') for x in file_list]
            # did this one with try/except block, necessary?
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
        yar = []
        bar = []
        for eachLine in dataArray:
            if len(eachLine) > 1:
                a, x, y, b = eachLine.split(',')
                dateX.append(a)
                yar.append(int(y))
                bar.append(float(b))

        # block for only showing hours and minutes in chart
        self.ax1.xaxis.set_major_locator(HourLocator())
        xformatter = matplotlib.dates.DateFormatter('%H:%M')
        self.ax1.xaxis.set_major_formatter(xformatter)
        self.ax1.xaxis.set_minor_formatter(xformatter)
        # self.ax2.xaxis.set_major_formatter(xformatter)
        # self.ax2.xaxis.set_minor_formatter(xformatter)

        # not all data is wanted in same chart, limit x-axis
        dateX = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S') for x in dateX]
        dateX_plot = dateX[boundary:]
        yar_plot = yar[boundary:]  # twitter sentiment plot
        bar_plot = bar[boundary:]  # price plot
        # self.ax1.plot(dateX_plot, yar_plot, c='skyblue', label='tweet sentiment', alpha=0.5)
        # self.ax2.plot(dateX_plot, bar_plot, c='lightgreen',
        #               label = '{} price'.format(self.pricequery))

        # buy & sell signals
        if len(yar) >= 6:
            # some arbitrary way of counting sentiment change
            current = yar[-1]
            past = yar[-6]
            sentiment = current - past
            print('sentiment on recent tweets: ', sentiment)
            with open('trade_data.txt', 'a') as trade:

                if (len(yar) >= 6) and sentiment > self.pos_sig:
                    trade.write('{},{}\n'.format(dateX_plot[-1], sentiment))
                    self.ax1.axvline(dateX_plot[-1], color='green', alpha=0.1)

                elif (len(yar) >= 6) and sentiment < self.neg_sig:
                    trade.write('{},{}\n'.format(dateX_plot[-1], sentiment))
                    self.ax1.axvline(dateX_plot[-1], color='red', alpha=0.1)

        # keep previous buy & sell signals in chart
        with open('trade_data.txt', 'r') as trade:
            trade = trade.read()
            tradeData = trade.split('\n')

            for eachline in tradeData[-500:]:
                if len(eachline) > 1:
                    x, sent = eachline.split(',')
                    x = datetime.strptime(x, '%Y-%m-%d %H:%M:%S')

                    if int(sent) > 22:
                        self.ax1.axvline(x, color='green', alpha=0.1)
                    elif int(sent) < -10:
                        self.ax1.axvline(x, color='red', alpha=0.1)

        # twitter user damp tweet alerts
        date, position = TweetAnalysis.drdamp_trade_alert()

        with open('damp_trades.txt', 'r') as damptrades:
            damptrades = damptrades.read()
            damptrades = damptrades.split('\n')

        dates = []
        if len(damptrades) >= 0:
            for line in damptrades:
                if len(line) > 1:
                    date_bef, trade = line.split(',')
                    dates.append(date_bef)
            if not str(date) in str(dates):
                if position == 0:
                    self.ax1.axvline(date, color='purple', alpha=1, linewidth=2)
                    with open('damp_trades.txt', 'a') as damp:
                        damp.write('{},{}\n'.format(date, position))

                elif position == 1:
                    self.ax1.axvline(date, color='y', alpha=1, linewidth=2)
                    with open('damp_trades.txt', 'a') as damp:
                        damp.write('{},{}\n'.format(date, position))

                elif position == 2:
                    self.ax1.axvline(date, color='white', alpha=1, linewidth=2)
                    with open('damp_trades.txt', 'a') as damp:
                        damp.write('{},{}\n'.format(date, position))

            with open('damp_trades.txt', 'r') as damp:
                damp = damp.read()
                damp = damp.split('\n')

            for trade in damp:
                if len(trade) > 0:
                    date, trade = trade.split(',')
                    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                    if int(trade) == 1:
                        self.ax1.axvline(date, color='y', alpha=1, linewidth=2)

            with open('damp_trades.txt', 'r') as damp:
                damp = damp.read()
                damp = damp.split('\n')

            for trade in damp:
                if len(trade) > 0:
                    date, trade = trade.split(',')
                    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                    if int(trade) == 0:
                        self.ax1.axvline(date, color='purple', alpha=1, linewidth=2)

            with open('damp_trades.txt', 'r') as damp:
                damp = damp.read()
                damp = damp.split('\n')

            for trade in damp:
                if len(trade) > 0:
                    date, trade = trade.split(',')
                    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                    if int(trade) == 2:
                        self.ax1.axvline(date, color='white', alpha=1, linewidth=2)

        else:
            if position == 0:
                self.ax1.axvline(date, color='purple', alpha=1, linewidth=2)
                with open('damp_trades.txt', 'a') as damp:
                    damp.write('{},{}\n'.format(date, position))

            elif position == 1:
                self.ax1.axvline(date, color='yellow', alpha=1, linewidth=2)
                with open('damp_trades.txt', 'a') as damp:
                    damp.write('{},{}\n'.format(date, position))

            elif position == 2:
                self.ax1.axvline(date, color='white', alpha=1, linewidth=2)
                with open('damp_trades.txt', 'a') as damp:
                    damp.write('{},{}\n'.format(date, position))

        self.ax1.legend(loc=2)  # bbox_to_anchor=(0, 0.95))
        # self.ax2.legend(loc=2)

    def drdamp_trade_alert():  # parsing twitter user DrDamp tweets for signals
        damp_tweets = UserTweetFetcher(twitter_user='DrDampen')
        damp_tweet = damp_tweets.get_user_timeline_tweets(1)

        date_created = [tw.created_at for tw in damp_tweet][0]

        # fix timezone like before when fetching
        hels_time = timezone('Europe/Helsinki')
        date_created = pytz.utc.normalize(pytz.utc.localize(
            date_created, is_dst=None)).astimezone(hels_time)
        date_created = date_created.replace(tzinfo=None)

        tweet_text = [tw.full_text for tw in damp_tweet][0].lower()

        if not '\@' in tweet_text:
            # really the best way to parse tweets for signals? works though
            if ('kort' in tweet_text or 'short' in tweet_text) and 'sp' in tweet_text:
                print('{}: DrDamp SHORT SP500'.format(date_created))
                print(tweet_text)
                position = 0  # 0 = short, 1 = long, 2 = exit
                return date_created, position

            elif ('long' in tweet_text or 'lång' in tweet_text) and 'sp' in tweet_text:
                print('{}: DrDamp LONG SP500'.format(date_created))
                print(tweet_text)
                position = 1
                return date_created, position

            elif ('kort' in tweet_text or 'short' in tweet_text) and 'dax' in tweet_text:
                print('{}: DrDamp SHORT DAX'.format(date_created))
                print(tweet_text)
                position = 0
                return date_created, position

            elif ('long' in tweet_text or 'lång' in tweet_text) and 'dax' in tweet_text:
                print('{}: DrDamp LONG DAX'.format(date_created))
                print(tweet_text)
                position = 1
                return date_created, position

            elif ('kort' in tweet_text or 'short' in tweet_text) and 'dj' in tweet_text:
                print('{}: DrDamp SHORT DOW'.format(date_created))
                print(tweet_text)
                position = 0
                return date_created, position

            elif ('long' in tweet_text or 'lång' in tweet_text) and 'dj' in tweet_text:
                print('{}: DrDamp LONG DOW'.format(date_created))
                print(tweet_text)
                position = 1
                return date_created, position

            elif ('kort' in tweet_text or 'short' in tweet_text) and 'omx' in tweet_text:
                print('{}: DrDamp SHORT OMXS'.format(date_created))
                print(tweet_text)
                position = 0
                return date_created, position

            elif ('long' in tweet_text or 'lång' in tweet_text) and 'omx' in tweet_text:
                print('{}: DrDamp LONG OMXS'.format(date_created))
                print(tweet_text)
                position = 1
                return date_created, position

            elif ('ur' in tweet_text or 'ut' in tweet_text) and (
                    'omx' in tweet_text or 'dax' in tweet_text or 'sp' in tweet_text or 'dj' in tweet_text):
                print('{}: DrDamp exited position'.format(date_created))
                position = 2
                return date_created, position

            else:
                position = None
                date_created = None
                return date_created, position

    def stock_price_get(stock):
        price = si.get_live_price(stock)
        return price

    def start_animation(self, query, pricequery, pos_sig=22, neg_sig=-10, interval=5000):
        fig = plt.figure(figsize=(12, 8))
        self.ax1 = fig.add_subplot(1, 1, 1)
        # self.ax2 = self.ax1.twinx()

        self.pos_sig = pos_sig
        self.neg_sig = neg_sig

        self.query = query
        self.pricequery = pricequery

        ani = animation.FuncAnimation(fig, stream.animation, interval=interval)

        plt.show()
        self.save_data()

    def save_data(self):  # on chart close - save fetched and processed data - reset
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
                    trade_data.write(line)

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

        if not os.path.exists('Querydata/{}/{}_damp.txt'.format(self.pricequery, date.today())):
            damp_trades = open(
                'Querydata/{}/{}_damp.txt'.format(self.pricequery, date.today()), 'w')

            with open('damp_trades.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    damp_trades.write(line)

            damp_trades.close()
            print('new file created')

        else:
            damp_trades = open(
                'Querydata/{}/{}_damp.txt'.format(self.pricequery, date.today()), 'a')

            with open('damp_trades.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    damp_trades.write(line)

            damp_trades.close()
            print('file appended')

        if not os.path.exists('Querydata/{}/{}_index.txt'.format(self.pricequery, date.today())):
            index_prices = open(
                'Querydata/{}/{}_index.txt'.format(self.pricequery, date.today()), 'w')

            with open('index_price.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    index_prices.write(line)

            index_prices.close()
            print('new file created')

        else:
            index_prices = open(
                'Querydata/{}/{}_index.txt'.format(self.pricequery, date.today()), 'a')

            with open('index_price.txt', 'r') as file:
                file = file.readlines()
                for line in file:
                    index_prices.write(line)

            index_prices.close()
            print('file appended')

        # this erases txt content for next live chart
        open('index_price.txt', 'w').close()
        open('stream_data.txt', 'w').close()
        open('trade_data.txt', 'w').close()
        open('damp_trades.txt', 'w').close()


if __name__ == '__main__':

    query = ('spx OR sp500 OR dax OR dax30 OR nasdaq OR djia OR dowjones OR nyse OR stocks OR equities OR investing')

    stream = TweetAnalysis()
    stream.start_animation(query, '^GDAXI', interval=5000)
