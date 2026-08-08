import pandas as pd
import requests
import time
import json
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# my api token
api_token = os.getenv("API_KEY")
headers = {'X-Auth-Token': api_token}
# function to call for speicic league


def fetch_league_info(league_code):

    # fetch standings
    url_standing = f"https://api.football-data.org/v4/competitions/{league_code}/standings"
    res_standing = requests.get(url_standing, headers=headers).json()
    df_standing = pd.json_normalize(res_standing['standings'][0]['table'])
    df_standing.to_csv(f'{league_code}_standings.csv', index=False)
    print("fetched standings!! \n")
    # sleep for 2s
    time.sleep(2)

    # fetch scorers
    url_scorers = f'https://api.football-data.org/v4/competitions/{league_code}/scorers?season=2025'
    res_scorers = requests.get(url_scorers, headers=headers).json()
    df_scorers = pd.json_normalize(res_scorers['scorers'])
    df_scorers.to_csv(f'{league_code}_scorers.csv', index=False)
    print("fetched scorers \n")

    # sleep for 2s
    time.sleep(2)

    # fetch matches
    url_matches = f'https://api.football-data.org/v4/competitions/{league_code}/matches?season=2025'
    res_matches = requests.get(url_matches, headers=headers).json()
    df_matches = pd.json_normalize(res_matches['matches'])
    df_matches.to_csv(f'{league_code}_matches.csv', index=False)
    print("fetched matches \n")

    # sleep for 2s
    time.sleep(2)

    # fetch team players

    url_team_info = f'https://api.football-data.org/v4/competitions/{league_code}/teams?season=2025'
    res_team_info = requests.get(url_team_info, headers=headers).json()
    df_team_info = pd.json_normalize(res_team_info['teams'])
    df_team_info.to_csv(f'{league_code}_team_info.csv', index=False)
    print("fetched team players \n")

    print(f"succes!, fetching has been completed for {league_code}")


# call the function to requests api data
# fetch_league_info('PL')

# set up rollign data for tha matches file to then get the past statsistic
df_matches = pd.read_csv('PL_matches.csv')


# filter out games that havent been FINISHED!
df_matches = df_matches[df_matches['status'] == 'FINISHED']

# sort the df by utcDate as api often give unorganised data
df_matches = df_matches.sort_values('utcDate')


# SQL start - Create a connectino to a database
conn = sqlite3.connect('premier_league.db')

# write cleaned matches dataframe into a SQL table
df_matches.to_sql('matches', conn, if_exists='replace', index=False)
print('data succesfully loaded into SQLITE')

with open('get_features.sql', 'r') as file:
    query = file.read()

df_features = pd.read_sql_query(query, conn)
conn.close()


feature_cols = [
    'Home_Team_AvgGoals',
    'Away_Team_AvgGoals',
    'Home_Team_AvgConceded',
    'Away_Team_AvgConceded',
    'Home_Team_Form',
    'Away_Team_Form',
    'goal_attack_diff',
    'goal_conceded_diff',
    'form_diff'
]

# stoped on train test split x and y have to be given
X = df_features[feature_cols]
y = df_features['target']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=1, shuffle=False)
classifier = RandomForestClassifier(
    n_estimators=100, max_depth=4, min_samples_leaf=5, random_state=1)
classifier.fit(X_train, y_train)
y_pred = classifier.predict(X_test)
# print(y_pred)
# print(y_test)


# count = 0
# for i, prob in enumerate(y_pred):
# print(
#   f"Sample {i+1}: Class 0 PRobability = {prob[0]:.4f}, Class 1 Probability = {prob[1]:.4f}, class 2 prbability: {prob[2]:.4f}")
# count += 1
# if count > 5:
#   break


accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy * 100:.2f}%")


# cross validation checking mutliple didfferent amount of data to see if the dataframe is the reason accuracy is low.
tscv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(classifier, X, y, cv=tscv)
print(f"5 fold cross val scores: {scores}")


# improve accuracy by ading more feature !!!
# xG feature , Elo rating , player avaibility and sqaud depth., home advantage, fatigue , fixutre congestion

# add more features .
