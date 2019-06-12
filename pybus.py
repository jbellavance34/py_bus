#!/usr/bin/python
import urllib.request
import re
import requests
from bs4 import BeautifulSoup
from requests import ConnectionError

# Fetch the html file
try:
    response = urllib.request.urlopen('http://www.ville.saint-jean-sur-richelieu.qc.ca/transport-en-commun/Documents/horaires/96.html', timeout=10)
    html_doc = response.read()
except Exception as e:
    print("Exception is :" + e)

# Parse the html file
soup = BeautifulSoup(html_doc, 'html.parser')

dir_list = soup.find_all('div', attrs={"id" : "div-horaires"})
dir_to_mtrl_table = dir_list[0].find('table')
dir_from_mtrl_table = dir_list[3].find('table')

speed_to_mtrl = dir_to_mtrl_table.find_all('div', attrs={"align" : "center"})
time_to_mtrl = dir_to_mtrl_table.find_all('tr')
start_to_mtrl = time_to_mtrl[1]
end_to_mtrl = time_to_mtrl[-1]

speed_to_sjsr = dir_from_mtrl_table.find_all('div', attrs={"align" : "center"})
time_to_sjsr = dir_from_mtrl_table.find_all('tr')
start_to_sjsr = time_to_sjsr[1]
end_to_sjsr = time_to_sjsr[-1]

# filter the return and populate list MTRL
start_to_mtrl_lst = []
end_to_mtrl_lst = []
for item in start_to_mtrl:
    item = str(item)
    if item != '\n':
        start_to_mtrl_lst.append(re.sub("<.*?>", "", item))
for item in end_to_mtrl:
    item = str(item)
    if item != '\n':
        end_to_mtrl_lst.append(re.sub("<.*?>", "", item))

# filter the return and populate list SJSR
start_to_sjsr_lst = []
end_to_sjsr_lst = []
for item in start_to_sjsr:
    item = str(item)
    if item != '\n':
        start_to_sjsr_lst.append(re.sub("<.*?>", "", item))
for item in end_to_sjsr:
    item = str(item)
    if item != '\n':
        end_to_sjsr_lst.append(re.sub("<.*?>", "", item))

# todo, prendre en charge caractere unicode pour les jours ferier
# https://www.fileformat.info/info/unicode/char/2600/index.htm

for speed, start, end in zip(speed_to_mtrl, start_to_mtrl_lst, end_to_mtrl_lst):
    if "S" in speed.text:
        speed_long = "Super Express"
    if "E" in speed.text:
        speed_long = "Express      "
    if "L" in speed.text:
        speed_long = "Locale       "
    if "A" in speed.text:
        speed_long = "Autoroute 30 "
    print("Autobus destination MTRL - Vitesse: " + speed_long + " Depart:" + start + " Arriver:" + end)

for speed, start, end in zip(speed_to_sjsr, start_to_sjsr_lst, end_to_sjsr_lst):
    if "S" in speed.text:
        speed_long = "Super Express"
    if "E" in speed.text:
        speed_long = "Express      "
    if "L" in speed.text:
        speed_long = "Locale       "
    if "A" in speed.text:
        speed_long = "Autoroute 30 "
    print("Autobus destination SJSR - Vitesse: " + speed_long + " Depart:" + start + " Arriver:" + end)
