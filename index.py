import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import csv
import time
from http.server import BaseHTTPRequestHandler

odds_URL = "https://www.betfair.com/sport/football/scottish-premiership/105"
fixtures_URL = "http://api.clubelo.com/Fixtures"


def fractional_to_decimal(fractional):
    fractional = fractional.strip("\n")

    if fractional == "EVS":
        return np.NaN

    first, second = [float(x) for x in fractional.split("/")]

    return round(first/second+1.0, 2)

def current_odds():

    response = requests.get(odds_URL)
    soup = BeautifulSoup(response.text, 'html.parser')

    events = soup.findAll('div', attrs={"class":"event-information"})
    matches = []

    for event in events:
        teams = event.findAll("span", attrs={"class":"team-name"})
        home_name = teams[0].attrs['title']
        away_name = teams[1].attrs['title']
        home_name = home_name.replace("Utd", "United")
        away_name = away_name.replace("Utd", "United")
        home_name = home_name.replace("Co", "County")
        away_name = away_name.replace("Co", "County")

        odds = event.findAll("span", attrs={"class":"ui-runner-price"})[2:]

        home_odds = fractional_to_decimal(odds[0].text)
        draw_odds = fractional_to_decimal(odds[1].text)
        away_odds = fractional_to_decimal(odds[2].text)

        matches.append((home_name, away_name, home_odds, draw_odds, away_odds))

    return pd.DataFrame(matches, columns=('Home', "Away", "O(W)", "O(D)", "O(L)"))

def current_prob():

    # def current_prob():
    away = ["GD<-5","GD=-5","GD=-4","GD=-3","GD=-2","GD=-1"]
    draw = ["GD=0"]
    home = ["GD=1","GD=2","GD=3","GD=4","GD=5","GD>5"]

    response = requests.get(fixtures_URL)
    decoded_content = response.content.decode('utf-8')
    fixtures = pd.DataFrame(csv.reader(decoded_content.splitlines(), delimiter=','))
    fixtures.columns = fixtures.iloc[0]
    fixtures = fixtures.drop(0)

    fixtures = fixtures[fixtures['Country'] == 'SCO']

    fixtures["P(W)"] = round(fixtures[home].astype(float).sum(axis=1), 4)
    fixtures["P(D)"] = round(fixtures[draw].astype(float).sum(axis=1), 4)
    fixtures["P(L)"] = round(fixtures[away].astype(float).sum(axis=1), 4)

    fixtures = fixtures[["Date","Home", "Away", "P(W)", "P(D)", "P(L)"]]

    return fixtures

def color_negative(v, color, limit):
        return f"color: {color};" if v < limit else "color: green;font-weight: bold"

def display_summary():
    summary_df = summary()

    styler = summary_df.style.applymap(color_negative, color='red', limit=0, subset=['Payoff(W)', 'Payoff(D)', 'Payoff(L)'])
    styler = styler.applymap(color_negative, color='red', limit=0.03, subset=['Edge(W)', 'Edge(D)', 'Edge(L)'])
    styler.format({
        'P(W)': '{:,.2%}'.format,
        'P(D)': '{:,.2%}'.format,
        'P(L)': '{:,.2%}'.format,
        'Edge(W)': '{:,.2%}'.format,
        'Edge(D)': '{:,.2%}'.format,
        'Edge(L)': '{:,.2%}'.format,
    })

    return styler

def summary(bet_amount=1):


    prob = current_prob()
    odds = current_odds()

    summary_df = odds.merge(prob)

    summary_df["Payoff(W)"] = (summary_df["P(W)"]*(summary_df["O(W)"]-bet_amount))-((1-summary_df["P(W)"])*bet_amount)
    summary_df["Payoff(D)"] = (summary_df["P(D)"]*(summary_df["O(D)"]-bet_amount))-((1-summary_df["P(D)"])*bet_amount)
    summary_df["Payoff(L)"] = (summary_df["P(L)"]*(summary_df["O(L)"]-bet_amount))-((1-summary_df["P(L)"])*bet_amount)

    summary_df["Edge(W)"] = summary_df["P(W)"] - (1/summary_df["O(W)"])
    summary_df["Edge(D)"] = summary_df["P(D)"] - (1/summary_df["O(W)"])
    summary_df["Edge(L)"] = summary_df["P(L)"] - (1/summary_df["O(W)"])


    #[]
    return summary_df.head(len(summary_df)).iloc[:,[5,0,1,2,6,9,12,3,7,10,13,4,8,11,14]]

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        self.wfile.write(bytes(display_summary().render()), 'utf-8')
        self.wfile.close()
        return 

