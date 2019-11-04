#!/usr/bin/python
import re
import urllib.request
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
from pytz import timezone
import pytz
from bs4 import BeautifulSoup
from flask import request
from flask_api import FlaskAPI, status

app = FlaskAPI(__name__)

###
# TODO
# fix AWS credentials for the git server
###
USERS_TABLE = os.environ['USERS_TABLE']
dynamodb = boto3.resource('dynamodb', 'us-east-1')
table = dynamodb.Table(USERS_TABLE)


@app.route("/", methods=['GET'])
def parse_bus():
    if request.method == 'GET':
        ###
        # Defining Montreal timezone to match data source timezone
        ###
        localtime = datetime.now(pytz.utc)
        montreal_tz = timezone('America/Montreal')
        date = localtime.astimezone(montreal_tz)
        date_time_hours = date.strftime("%H")
        date_time_minutes = date.strftime("%M")
        ###
        # try to get information from dynamodb
        ###
        try:
            response = table.scan()
            global data
            data = response['Items']
        except ClientError as e:
            print(e.response['Error']['Message'])
            print("Can't fetch data from dynamodb, trying to upload content from web")
        ###
        # Updating the dynamoDB only if empty
        ###
        if len(data) <= 4:
            ###
            # Trying to get data from town website
            ###
            for tries in range(1, 11):
                url = ('http://www.ville.saint-jean-sur-richelieu.qc.ca/'
                       'transport-en-commun/Documents/horaires/96.html')
                try:
                    response_web = urllib.request.urlopen(url, timeout=30)
                    html_doc = response_web.read()
                except Exception as E:
                    print("Try " + str(tries) + "/10 failed for " + url + " exception is : " + str(E))
                    continue
                finally:
                    ###
                    # Parsing the collected data
                    ###
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
                        for i in city_start:
                            i = str(i)
                            if i != '\n':
                                list_start.append(re.sub("<.*?>", "", i))
                        for i in city_end:
                            i = str(i)
                            if i != '\n':
                                list_end.append(re.sub("<.*?>", "", i))

                    populate_list_direction(start_to_mtrl, start_to_mtrl_lst, end_to_mtrl, end_to_mtrl_lst)
                    populate_list_direction(start_to_sjsr, start_to_sjsr_lst, end_to_sjsr, end_to_sjsr_lst)

                    ###
                    # Adding the data to dynamodb
                    ###
                    bus_id = 1
                    ###
                    # Adding Saint-Jean-Sur-Le-Richelieu bus runs information
                    ###
                    for start, end, speed in zip(start_to_sjsr_lst, end_to_sjsr_lst, speed_to_sjsr):
                        try:
                            speed = str(speed)
                            destination = 'sjsr'
                            concat_response = (destination + ';'
                                               + start + ';'
                                               + end + ';'
                                               + speed)
                            insert_data = table.put_item(
                                TableName=USERS_TABLE,
                                Item={
                                    'id': str(bus_id),
                                    'data': str(concat_response)
                                }
                            )
                            bus_id = bus_id + 1
                        except ClientError as e:
                            print(e.response['Error']['Message'])
                    ###
                    # TODO
                    # fix Montreal bus runs
                    # seems to load only a few
                    ###
                    ###
                    # Adding Montreal bus runs information
                    ###
                    for start, end, speed in zip(start_to_mtrl_lst, end_to_mtrl_lst, speed_to_mtrl):
                        try:
                            speed = str(speed)
                            destination = 'mtrl'
                            concat_response = (destination + ';'
                                               + start + ';'
                                               + end + ';'
                                               + speed)
                            insert_data = table.put_item(
                                TableName=USERS_TABLE,
                                Item={
                                    'id': str(bus_id),
                                    'data': str(concat_response)
                                }
                            )
                            bus_id = bus_id + 1
                        except ClientError as e:
                            print(e.response['Error']['Message'])

        ###
        # Parsing given parameters
        ###
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
            return_message = "Variable dest=" + direction.lower() + " invalid. Must be dest=" + destination[
                0].lower() \
                             + " or dest=" + destination[1].lower()
            return return_message, status.HTTP_400_BAD_REQUEST

        ###
        # Filtering output value to give
        ##
        def list_of_speeds(argument):
            switcher = {
                '<div align="center">S</div>': "Super Express  ",
                '<div align="center">S ☀</div>': "Super Express ☀",
                '<div align="center">E</div>': "Express        ",
                '<div align="center">E ☀</div>': "Express ☀     ",
                '<div align="center">L</div>': "Locale         ",
                '<div align="center">L ☀</div>': "Locale ☀      ",
                '<div align="center">A</div>': "Autoroute 30   ",
                '<div align="center">A ☀</div>': "Autoroute 30 ☀ ",
            }
            return switcher.get(argument, "Wrong speed    ")

        complete_return_value = []

        def populate_complete(bus_data, max_bus):
            ###
            # Sort content
            ###
            sorted_bus_data = []
            for i in bus_data:
                sorted_bus_data.append("temp")
            for i in bus_data:
                sorted_bus_data[(int(i['id']) - 1)] = i['data']
            for entry in sorted_bus_data:
                # Entry example
                # 44;sjsr;17:06;17:46;<div align="center">S</div>
                dest, start, end, speed = entry.split(';')
                if dest == direction or direction == 'all':
                    loop_hours, loop_minutes = start.split(':')
                    combined_loop_minutes = int(loop_hours)*60 + int(loop_minutes)
                    combined_date_minutes = int(date_time_hours)*60 + int(date_time_minutes)
                    if combined_loop_minutes >= combined_date_minutes:
                        if (sum(dest in s for s in complete_return_value)) <= (int(max_bus) - 1):
                            complete_return_value.append("Autobus destination " + dest + " : "
                                                         + list_of_speeds(speed) + " Depart:"
                                                         + start + " Arriver:" + end)

        populate_complete(data, direction_max)

        return complete_return_value, status.HTTP_200_OK


if __name__ == "__main__":
    app.run()
