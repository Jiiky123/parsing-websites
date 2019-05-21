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

# make path relative to script
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


class TwitterClient():  # inspect specific twitter users
    def __init__(self, twitter_user=None):
        self.auth = TwitterAuthenticator().authenticate_twitter_app()
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


class TwitterAuthenticator():

    def authenticate_twitter_app(self):
        auth = OAuthHandler(twitter_credentials.CONSUMER_KEY, twitter_credentials.CONSUMER_SECRET)
        auth.set_access_token(twitter_credentials.ACCESS_TOKEN,
                              twitter_credentials.ACCESS_TOKEN_SECRET)
        return auth


class TwitterStreamer():
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


class GetTweets(TwitterStreamer):

    def __init__(self):
        self.auth = TwitterAuthenticator().authenticate_twitter_app()
        self.api = API(self.auth)

    def get_tweets(self, query=[]):
        df = pd.DataFrame(columns=['date', 'message', 'retweets'])

        date = []
        message = []
        retweets = []

        try:  # try except block for the case of rate_limit
            tweepy_tweet = Cursor(self.api.search, q=query, lang='en',
                                  result_type='recent', include_rts=False,
                                  since='2019-5-12', count=200).items(99999)
            for tweet in tweepy_tweet:  # exclude tweets with RT @
                if 'RT @' not in str(tweet.text.encode('utf-8', 'ignore')):
                    date.append(tweet.created_at)
                    message.append(str(tweet.text.encode('utf-8', 'ignore')))
                    retweets.append(tweet.retweet_count)

            message = [x.replace('b\'', '') for x in message]  # clean tweet
            temp_df = pd.DataFrame({'date': date, 'message': message,
                                    'retweets': retweets})
            df = df.append(temp_df)
            df.set_index('date', inplace=True)
            df.drop_duplicates(subset='message', inplace=True)

        except BaseException as e:
            print('Error on data: {}'.format(str(e)))

        print('{} tweets fetched\n'.format(len(df)))
        return df


class TweetWordAnalysis():
    def __init__(self, df):
        self.df = df
        self.results = Counter()  # stores word-count pairs
        self.df.message.astype(str).str.lower().str.split().apply(self.results.update)
        # make tweet.text lowercase for regex
        self.df.message = self.df.message.astype(str).str.lower()

    def neg_pos_words_count(self, neg_words, pos_words):
        # list of positive and negative words as arguments
        # count negative words
        neg_word_list = []
        neg_word_dates = []

        for word in neg_words:

            for date, words, retweets in zip(self.df.index, self.df.message, self.df.retweets):
                count = len(re.findall(r'\b{}\w*'.format(word), words))
                if retweets == 0:
                    neg_word_list.append(count)
                else:  # give retweets weight by squaring
                    neg_word_list.append(count*retweets**2)
                neg_word_dates.append(date)

        neg_word_df = pd.DataFrame(
            {'date': neg_word_dates, 'neg_words': neg_word_list})

        print('# of bearish words: ', neg_word_df.neg_words.sum())

        # count positive words
        pos_word_list = []
        pos_word_dates = []

        for word in pos_words:

            for date, words, retweets in zip(self.df.index, self.df.message, self.df.retweets):
                count = len(re.findall(r'\b{}\w*'.format(word), words))
                if retweets == 0:
                    pos_word_list.append(count)
                else:  # give retweets weight by squaring
                    pos_word_list.append(count*retweets**2)
                pos_word_dates.append(date)

        pos_word_df = pd.DataFrame(
            {'date': pos_word_dates, 'pos_words': pos_word_list})

        print('# of bullish words: ', pos_word_df.pos_words.sum())

        return neg_word_df, pos_word_df


if __name__ == '__main__':

    # market_query = ['spx' or 'sp500' or 'dax' or
    #                 'dax30' or 'nasdaq' or 'stockmarket' or
    #                 'market' or 'nq' or 'djia' or 'dow' or
    #                 'dowjones' or 'nyse']
    # tweets = GetTweets()
    # df = tweets.get_tweets(
    #     market_query)

    neg_words = ['bear', 'sell', 'resistance', 'short']
    pos_words = ['bull', 'buy', 'support', 'long']
    word_analysis = TweetWordAnalysis(df)
    neg, pos = word_analysis.neg_pos_words_count(neg_words, pos_words)
