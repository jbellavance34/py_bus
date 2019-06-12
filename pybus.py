#!/usr/bin/python
import urllib.request
import re
import requests
from bs4 import BeautifulSoup
from requests import ConnectionError

# Fetch the html file
try:
    RESPONSE = urllib.request.urlopen('http://www.ville.saint-jean-sur-richelieu.qc.ca/transport-en-commun/Documents/horaires/96.html', timeout=10)
    HTML_DOC = RESPONSE.read()
except Exception as E:
    print("Exception is :" + E)

# Parse the html file
SOUP = BeautifulSoup(HTML_DOC, 'html.parser')

DIR_LIST = SOUP.find_all('div', attrs={"id" : "div-horaires"})
DIR_TO_MTRL_TABLE = DIR_LIST[0].find('table')
DIR_FROM_MTRL_TABLE = DIR_LIST[3].find('table')

SPEED_TO_MTRL = DIR_TO_MTRL_TABLE.find_all('div', attrs={"align" : "center"})
START_TO_MTRL = DIR_TO_MTRL_TABLE.find_all('tr')[1]
END_TO_MTRL = DIR_TO_MTRL_TABLE.find_all('tr')[-1]

SPEED_TO_SJSR = DIR_FROM_MTRL_TABLE.find_all('div', attrs={"align" : "center"})
START_TO_SJSR = DIR_FROM_MTRL_TABLE.find_all('tr')[1]
END_TO_SJSR = DIR_FROM_MTRL_TABLE.find_all('tr')[-1]

START_TO_MTRL_LST = []
END_TO_MTRL_LST = []
START_TO_SJSR_LST = []
END_TO_SJSR_LST = []
# filter the return and populate list MTRL

def populate_list_direction(city_start, list_start, city_end, list_end):
    for item in city_start:
        item = str(item)
        if item != '\n':
            list_start.append(re.sub("<.*?>", "", item))
    for item in city_end:
        item = str(item)
        if item != '\n':
            list_end.append(re.sub("<.*?>", "", item))
populate_list_direction(START_TO_MTRL, START_TO_MTRL_LST, END_TO_MTRL, END_TO_MTRL_LST)
populate_list_direction(START_TO_SJSR, START_TO_SJSR_LST, END_TO_SJSR, END_TO_SJSR_LST)

# todo, prendre en charge caractere unicode pour les jours ferier
# https://www.fileformat.info/info/unicode/char/2600/index.htm

for speed, start, end in zip(SPEED_TO_MTRL, START_TO_MTRL_LST, END_TO_MTRL_LST):
    if "S" in speed.text:
        speed_long = "Super Express"
    if "E" in speed.text:
        speed_long = "Express      "
    if "L" in speed.text:
        speed_long = "Locale       "
    if "A" in speed.text:
        speed_long = "Autoroute 30 "
    print("Autobus destination MTRL - Vitesse: " + speed_long + " Depart:" + start + " Arriver:" + end)

for speed, start, end in zip(SPEED_TO_SJSR, START_TO_SJSR_LST, END_TO_SJSR_LST):
    if "S" in speed.text:
        speed_long = "Super Express"
    if "E" in speed.text:
        speed_long = "Express      "
    if "L" in speed.text:
        speed_long = "Locale       "
    if "A" in speed.text:
        speed_long = "Autoroute 30 "
    print("Autobus destination SJSR - Vitesse: " + speed_long + " Depart:" + start + " Arriver:" + end)
