#!/usr/bin/python
import re
import urllib.request
from datetime import datetime

from bs4 import BeautifulSoup
from flask import request
from flask_api import FlaskAPI, status

app = FlaskAPI(__name__)


@app.before_first_request
def load_huge_file():
    for tries in range(1, 11):
        url = ('http://www.ville.saint-jean-sur-richelieu.qc.ca/2'
               'transport-en-commun/Documents/horaires/96.html')
        try:
            response = urllib.request.urlopen(url, timeout=30)
            html_doc_load = response.read()
            global html_doc
            html_doc = html_doc_load
        except Exception as E:
            print("Try " + str(tries) + "/10 failed for " + url + " exception is : " + str(E))
            continue
    else:
        print("Can't fetch website data, exiting program")
        ######
        # todo, add routine when page doesn't get fetch.
        # Idea: Copy variable to file, and load file instead of
        #       a live version.
        #####
        #####


@app.route("/", methods=['GET'])
def parse_bus():
    if request.method == 'GET':
        localtime = datetime.now()
        date_time_hours = localtime.strftime("%H")
        date_time_minutes = localtime.strftime("%M")
        if request.args.get("max"):
            direction_max = request.args.get("max", "")
        else:
            direction_max = 10
        if request.args.get("dest"):
            direction = request.args.get("dest", "")
        else:
            direction = 'all'
        destination = ['sjsr', 'mtrl', 'all']
        if direction.lower() not in destination:
            return_message = "Variable dest=" + direction.lower() + " invalid. Must be dest=" + destination[0].lower() \
                             + " or dest=" + destination[1].lower()
            return return_message, status.HTTP_400_BAD_REQUEST

        soup = BeautifulSoup(html_doc, 'html.parser')

        dir_list = soup.find_all('div', attrs={"id": "div-horaires"})
        dir_to_mtrl_table = dir_list[0].find('table')
        dir_from_mtrl_table = dir_list[3].find('table')

        speed_to_mtrl = dir_to_mtrl_table.find_all('div', attrs={"align": "center"})
        start_to_mtrl = dir_to_mtrl_table.find_all('tr')[1]
        end_to_mtrl = dir_to_mtrl_table.find_all('tr')[-1]

        speed_to_sjsr = dir_from_mtrl_table.find_all('div', attrs={"align": "center"})
        start_to_sjsr = dir_from_mtrl_table.find_all('tr')[1]
        end_to_sjsr = dir_from_mtrl_table.find_all('tr')[-1]

        start_to_mtrl_lst = []
        end_to_mtrl_lst = []
        start_to_sjsr_lst = []
        end_to_sjsr_lst = []

        def populate_list_direction(city_start, list_start, city_end, list_end):
            for item in city_start:
                item = str(item)
                if item != '\n':
                    list_start.append(re.sub("<.*?>", "", item))
            for item in city_end:
                item = str(item)
                if item != '\n':
                    list_end.append(re.sub("<.*?>", "", item))
        populate_list_direction(start_to_mtrl, start_to_mtrl_lst, end_to_mtrl, end_to_mtrl_lst)
        populate_list_direction(start_to_sjsr, start_to_sjsr_lst, end_to_sjsr, end_to_sjsr_lst)
        ######
        # todo, prendre en charge caractere unicode pour les jours ferier
        # https://www.fileformat.info/info/unicode/char/2600/index.htm
        #####
        complete_return_value = []

        def listofspeeds(argument):
            switcher = {
                "S": "Super Express  ",
                "S ☀": "Super Express ☀",
                "E": "Express        ",
                "E ☀": "Express ☀      ",
                "L": "Locale         ",
                "L ☀": "Locale ☀      ",
                "A": "Autoroute 30   ",
                "A ☀": "Autoroute 30 ☀ ",
            }
            return switcher.get(argument, "Wrong speed    ")

        def populate_complete(speed_to, start_lst, end_lst, dest, max_bus):
            if dest.lower() == 'mtrl':
                int_dict = 1
            if dest.lower() == 'sjsr':
                int_dict = 0
            if destination[int_dict].lower() in direction or direction == "all":
                for speed, start, end in zip(speed_to, start_lst, end_lst):
                    loop_hours, loop_minutes = start.split(':')
                    if (int(loop_hours)*60 + int(loop_minutes)) >= (int(date_time_hours)*60 + int(date_time_minutes))\
                            or direction == 'all':
                        if (sum(dest in s for s in complete_return_value)) <= (int(max_bus) - 1):
                            complete_return_value.append("Autobus destination " + dest + " : "
                                                         + listofspeeds(speed.text) + " Depart:"
                                                         + start + " Arriver:" + end)

        populate_complete(speed_to_mtrl, start_to_mtrl_lst, end_to_mtrl_lst, 'MTRL', direction_max)
        populate_complete(speed_to_sjsr, start_to_sjsr_lst, end_to_sjsr_lst, 'SJSR', direction_max)

        return complete_return_value, status.HTTP_200_OK


if __name__ == "__main__":
    app.run()
