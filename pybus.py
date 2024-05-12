#!/usr/bin/python
import re
import urllib.request
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
from pytz import timezone
import pytz
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from flask import request
from flask import Flask
import json

app = Flask(__name__)
# if needed add logging
# app.logger.(my_variable)
# dynamodb table information

USERS_TABLE = os.environ.get('USERS_TABLE', 'users-table-prod')
URL = 'https://sjsr.ca/horaires/96.html'
DYNAMODB_DATA = []
dynamodb = boto3.resource('dynamodb', 'us-east-1')
table = dynamodb.Table(USERS_TABLE)

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def list_of_speeds(argument):
    """
    Filtering output value to give
    """
    argument = remove_html_tags(argument)
    switcher = {
        'S': "Super Express  ",
        'E': "Express        ",
        'E ☀<': "Express ☀     ",
        'L': "Locale         ",
        'L ☀': "Locale ☀      ",
        'A': "Autoroute 30   ",
        'A ☀': "Autoroute 30 ☀ ",
    }
    return switcher.get(argument, "Wrong speed    ")

def custom_sort(t):
    """
    Sorting bus rides based on the start hour
    TODO, aucune idée de ce que sa fait
    """
    dest, speed, hour_start, minutes_start, hour_end, minutes_end = t.split(':')
    return hour_start, minutes_start

def get_data_from_url(URL, remaining_retries=10, timeout=30):
    try:
        response_web = urllib.request.urlopen(URL, timeout=timeout)
        return response_web.read()
    except Exception as E:
        if remaining_retries > 0:
            print(f"{remaining_retries} remaining failed for {URL} exception is : {str(E)}")
            return get_data_from_url(URL, remaining_retries -1, timeout)
        else:
            raise

def get_data_from_db():
    try:
        response = table.scan()
    except ClientError as e:
        print(e.response['Error']['Message'])
        print("Can't fetch data from dynamodb")
    # TODO, do we need to handle failures ?
    return response['Items']

def parse_data(data) -> [List, List, List, List]:
    soup = BeautifulSoup(data, 'html.parser')
    dir_list = soup.find_all('div', attrs={"id": "div-horaires"})
    dir_to_mtrl_table = dir_list[0].find('table')
    dir_from_mtrl_table = dir_list[3].find('table')

    speed_to_mtrl = dir_to_mtrl_table.find_all('div', attrs={"align": "center"})
    start_to_mtrl = dir_to_mtrl_table.find_all('tr')[1]
    end_to_mtrl = dir_to_mtrl_table.find_all('tr')[-1]

    speed_to_sjsr = dir_from_mtrl_table.find_all('div', attrs={"align": "center"})
    start_to_sjsr = dir_from_mtrl_table.find_all('tr')[1]
    end_to_sjsr = dir_from_mtrl_table.find_all('tr')[-1]

    start_to_mtrl = [remove_html_tags(str(i)) for i in start_to_mtrl]
    end_to_mtrl = [remove_html_tags(str(i)) for i in end_to_mtrl]
    start_to_sjsr = [remove_html_tags(str(i)) for i in start_to_sjsr]
    end_to_sjsr = [remove_html_tags(str(i)) for i in end_to_sjsr]

    return start_to_mtrl, end_to_mtrl, speed_to_mtrl, start_to_sjsr, end_to_sjsr, speed_to_sjsr

def update_data_to_db():
    html_doc = get_data_from_url(URL)
    start_to_mtrl, end_to_mtrl, speed_to_mtrl, start_to_sjsr, end_to_sjsr, speed_to_sjsr = parse_data(html_doc)
    ###
    # Adding Saint-Jean-Sur-Le-Richelieu bus runs information
    ###
    for start, end, speed in zip(start_to_sjsr, end_to_sjsr, speed_to_sjsr):
        try:
            speed = str(speed)
            destination = 'sjsr'
            concat_response = (f"{destination};{start};{end};{speed}")
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
    for start, end, speed in zip(start_to_mtrl, end_to_mtrl, speed_to_mtrl):
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


def refresh_data():
    global DYNAMODB_DATA
    if len(DYNAMODB_DATA) <= 4:
        DYNAMODB_DATA = get_data_from_db()
        update_data_to_db()

with app.app_context():
    refresh_data()

def render_bus_data(data: List, sjsr: bool, mtrl: bool, direction_max: int):
    # Defining Montreal timezone to match data source timezone
    localtime = datetime.now(pytz.utc)
    montreal_tz = timezone('America/Montreal')
    date = localtime.astimezone(montreal_tz)
    date_time_hours = date.strftime("%H")
    date_time_minutes = date.strftime("%M")

    rendered_data = []
    # Entry example
    # sjsr;17:06;17:46;<div align="center">S</div>
    found_sjsr = 0
    found_mtrl = 0
    for entry in data:
        dest, start, end, speed = entry['data'].split(';')
        loop_hours, loop_minutes = start.split(':')
        combined_loop_minutes = int(loop_hours)*60 + int(loop_minutes)
        combined_date_minutes = int(date_time_hours)*60 + int(date_time_minutes)
        if combined_loop_minutes >= combined_date_minutes:
            speed = list_of_speeds(speed)
            value = f"Autobus destination {dest}: {speed} Depart:{start} Arriver:{end}"
            if dest == 'sjsr' and sjsr is True and found_sjsr < (direction_max / 2):
                rendered_data.append(value)
                found_sjsr = found_sjsr + 1
            if dest == 'mtrl' and mtrl is True and found_mtrl < (direction_max / 2):
                rendered_data.append(value)
                found_mtrl = found_mtrl +1
    return sorted(rendered_data, key=custom_sort)

@app.route("/", methods=['GET'])
def parse_bus():
    global DYNAMODB_DATA
    # Parsing given parameters
    direction_max = int(request.args.get("max", 10))
    direction = request.args.get("dest", "all").lower()
    destination = ['sjsr', 'mtrl', 'all']
    if direction not in destination:
        return f"Variable dest={direction} invalid. Must be dest={destination[0]} or dest={destination}", 400
    return app.response_class(
        response = json.dumps(
            render_bus_data(
                DYNAMODB_DATA,
                True if (direction == 'sjsr' or direction == 'all') else False, 
                True if (direction == 'mtrl' or direction == 'all') else False,
                direction_max
            )
        ),
        status = 200
    )

if __name__ == "__main__":
    app.run(
        debug=True # remove me
    )
