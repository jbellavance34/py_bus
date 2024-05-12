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
#from flask_api import FlaskAPI, status
from flask import Flask

app = Flask(__name__)

# dynamodb table information
USERS_TABLE = os.environ.get('USERS_TABLE', 'users-table-prod')
dynamodb = boto3.resource('dynamodb', 'us-east-1')
table = dynamodb.Table(USERS_TABLE)


@app.before_first_request
###
# try to get information from dynamodb
###
def get_or_update_dynamodb_data():
    ###
    # TODO
    # fix AWS credentials for the git server
    ###
    try:
        response = table.scan()
        global dynamodb_data
        dynamodb_data = response['Items']
    except ClientError as e:
        print(e.response['Error']['Message'])
        print("Can't fetch data from dynamodb")
    if len(dynamodb_data) <= 4:
        ###
        # Updating the dynamoDB only if empty
        ###
        url = ('http://www.ville.saint-jean-sur-richelieu.qc.ca/' +
               'transport-en-commun/Documents/horaires/96.html')
        for tries in range(1, 11):
            try:
                response_web = urllib.request.urlopen(url, timeout=30)
                html_doc = response_web.read()
            except Exception as E:
                print("Try " + str(tries) + "/10 failed for " + url + " exception is : " + str(E))
                continue
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
                        'data': str(concat_response)
                    }
                )
            except ClientError as e:
                print(e.response['Error']['Message'])
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
                        'data': str(concat_response)
                    }
                )
            except ClientError as e:
                print(e.response['Error']['Message'])


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
        # Parsing given parameters
        ###
        if request.args.get("max"):
            direction_max = request.args.get("max", "")
            direction_max = int(direction_max)
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
            return return_message, 400

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

        complete_return_value_mtrl = []
        complete_return_value_sjsr = []
        complete_return_value = []

        def populate_complete(bus_data):
            for entry in bus_data:
                # Entry example
                # sjsr;17:06;17:46;<div align="center">S</div>
                dest, start, end, speed = entry['data'].split(';')
                loop_hours, loop_minutes = start.split(':')
                combined_loop_minutes = int(loop_hours)*60 + int(loop_minutes)
                combined_date_minutes = int(date_time_hours)*60 + int(date_time_minutes)
                if combined_loop_minutes >= combined_date_minutes:
                    value = ("Autobus destination " + dest + " : "
                             + list_of_speeds(speed) + " Depart:"
                             + start + " Arriver:" + end)
                    if dest == 'sjsr':
                        complete_return_value_sjsr.append(value)
                    elif dest == 'mtrl':
                        complete_return_value_mtrl.append(value)

        populate_complete(dynamodb_data)
        ###
        # Sorting bus rides based on the start hour
        ###

        def custom_sort(t):
            dest, speed, hour_start, minutes_start, hour_end, minutes_end = t.split(':')
            return hour_start, minutes_start
        complete_return_value_sjsr = sorted(complete_return_value_sjsr, key=custom_sort)
        complete_return_value_mtrl = sorted(complete_return_value_mtrl, key=custom_sort)
        ###
        # Adding only the bus rides up to direction_max
        ###
        if direction == 'sjsr':
            complete_return_value = complete_return_value_sjsr[:direction_max]
        elif direction == 'mtrl':
            complete_return_value = complete_return_value_mtrl[:direction_max]
        else:
            complete_return_value.extend(complete_return_value_sjsr[:direction_max])
            complete_return_value.extend(complete_return_value_mtrl[:direction_max])

        return complete_return_value, 200


if __name__ == "__main__":
    app.run()
