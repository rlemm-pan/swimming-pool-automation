#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import urllib2
import urllib
import json
import pprint
import cherrypy
from datetime import datetime
import pyfirmata
from pyfirmata import Arduino, util
import multiprocessing.pool
from threading import Thread
from flask import *
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
from gevent import pywsgi, sleep
from socketio.namespace import BaseNamespace
from gevent import server
from gevent.server import _tcp_listener
from gevent import monkey
from apscheduler.schedulers.blocking import BlockingScheduler
import math
import time
import sys
import os
import logging
import traceback
import exceptions
import logging.config
monkey.patch_all()

board = Arduino('/dev/ttyACM0', baudrate=57600)
sched = BlockingScheduler()
pump = board.digital[8]
pump.write(0)
low = board.digital[9]
low.write(0)
high = board.digital[10]
high.write(0)
sweeper = board.digital[11]
sweeper.write(0)
blower = board.digital[12]
blower.write(0)

app = Flask(__name__)

pump_on_off = ""
pump_low_high = ""
sweeper_on_off = ""
blower_on_off = ""
psi = "0.0"
web_start_psi = "0"
start_psi = 0.0
psi_read = 0.0
maximum_psi = 0.0
wp_sensor_value = 0.0
read_start_pressure = False
pump_status = pump.read()
low_status = low.read()
high_status = high.read()
sweeper_status = sweeper.read()
blower_status = blower.read()
temperature = "0"
wind_speed = "0"
wind_direction = "S"
current_graphic = "clear-day"
day1_graphic = "clear-day"
day2_graphic = "clear-day"
day3_graphic = "clear-day"
day4_graphic = "clear-day"
day5_graphic = "clear-day"
current_date = "January 1st 2016"
current_conditions = "Sunny"
day1_conditions = "Sunny"
day2_conditions = "Sunny"
day3_conditions = "Sunny"
day4_conditions = "Sunny"
day5_conditions = "Sunny"
day1_max_temp = "0"
day1_min_temp = "0"
day2_max_temp = "0"
day2_min_temp = "0"
day3_max_temp = "0"
day3_min_temp = "0"
day4_max_temp = "0"
day4_min_temp = "0"
day5_max_temp = "0"
day5_min_temp = "0"
day1_day = "Mon"
day2_day = "Mon"
day3_day = "Mon"
day4_day = "Mon"
day5_day = "Mon"
pump_hour = ""
sweeper_hour = ""
sweeper_duration = ""
pump_cfg = open('./pump.cfg', 'r')
sweeper_cfg = open('./sweeper.cfg', 'r')
duration_cfg = open('./duration.cfg', 'r')
pump_hour = pump_cfg.read()
sweeper_hour = sweeper_cfg.read()
sweeper_duration = duration_cfg.read()
pump_cfg.close()
sweeper_cfg.close()
duration_cfg.close()
check_pump_5 = ""
check_pump_6 = ""
check_pump_7 = ""
check_pump_8 = ""
check_pump_9 = ""
check_pump_10 = ""
check_sweeper_5 = ""
check_sweeper_6 = ""
check_sweeper_7 = ""
check_sweeper_8 = ""
check_sweeper_9 = ""
check_sweeper_10 = ""
sweeper_duration_1 = ""
sweeper_duration_2 = ""
sweeper_duration_3 = ""
sweeper_duration_4 = ""
sweeper_duration_5 = ""
sweeper_duration_6 = ""
api_key = "d78436b25cd940aab6b12249160610"
partly_cloudy = ['116', '119', '122']
clear_day = ['113']
fog = ['260', '248', '143']
snow = ['395', '392', '377', '374', '371', '368',
        '350', '338', '335', '332', '329', '326', '323', '230', '227', '179']
sleet = ['365', '362', '320', '317', '284', '281', '185', '182']
rain = ['389', '386', '359', '356', '353', '314', '311',
        '308', '305', '302', '299', '296', '293', '266', '263', '200', '176']


def ordinal(n):
    return "%d%s" % (n, "tsnrhtdd" [(n / 10 % 10 != 1) *
                                    (n % 10 < 4) * n % 10::4])


@sched.scheduled_job('cron', hour=int(pump_hour), minute=0)
def scheduled_job_pump():
    global day1_max_temp
    try:
        run_length = 3600 * (int(day1_max_temp) / 10)
        low.write(0)
        high.write(1)
        pump.write(1)
        time.sleep(run_length)
        high.write(0)
        pump.write(0)
        pump_low_high = ""
        pump_on_off = ""

    except Exception, e:
        log_exception(e)
        return str(e)


@sched.scheduled_job('cron', hour=int(sweeper_hour), minute=0)
def scheduled_job_sweeper():
    global sweeper_duration
    try:
        time.sleep(10)
        run_length = 3600 * int(sweeper_duration)
        if pump_status == 1:
            sweeper_on_off = "on"
            sweeper.write(1)
        elif pump_status == 0:
            sweeper_on_off = ""
            sweeper.write(0)
            logging.warning('Pump is off.  Turning off Sweeper')
        time.sleep(run_length)
        sweeper_on_off = ""
        sweeper.write(0)

    except Exception, e:
        log_exception(e)
        return str(e)


def start_pump_scheduler():
    try:
        sched.start()

    except Exception, e:
        log_exception(e)
        return str(e)


def get_weather_loop():
    global temperature, wind_direction, wind_speed, api_key, \
        current_conditions, current_graphic, day1_day, \
        day1_graphic, day2_day, day2_graphic, day3_day, \
        day3_graphic, day4_day, day4_graphic, day5_day, \
        day5_graphic, day1_max_temp, day1_min_temp, \
        day2_max_temp, day2_min_temp, day3_max_temp, \
        day3_min_temp, day4_max_temp, day4_min_temp, \
        day5_max_temp, day5_min_temp, current_date, \
        day1_conditions, day2_conditions, day3_conditions, \
        day4_conditions, day5_conditions

    wait_for_internet_connection()
    while True:
        try:
            url = "http://api.worldweatheronline.com/premium/v1/weather.ashx?key="+api_key+"&q=77546&format=json&num_of_days=5"
            json_format = requests.get(url.decode("utf-8")).json()
            now = datetime.now()
            temperature = str(json_format['data']['current_condition'][0]['temp_F'])
            wind_speed = str(json_format['data']['current_condition'][0]['windspeedMiles'])
            wind_direction = str(json_format['data']['current_condition'][0]['winddir16Point'])
            current_graphic = str(json_format['data']['current_condition'][0]['weatherCode'])
            current_day = int(now.strftime("%d"))
            ordinal_day = ordinal(current_day)
            current_date = str(now.strftime("%B "+ordinal_day+" %Y"))
            current_conditions = str(json_format['data']['current_condition'][0]['weatherDesc'][0]['value'])
            current_time = now.strftime("%H:%M")
            day1_graphic = str(json_format['data']['weather'][0]['hourly'][4]['weatherCode'])
            day1_conditions = str(json_format['data']['weather'][0]['hourly'][4]['weatherDesc'][0]['value'])
            day1_date = str(json_format['data']['weather'][0]['date'])
            day1_max_temp = str(json_format['data']['weather'][0]['maxtempF'])
            day1_min_temp = str(json_format['data']['weather'][0]['mintempF'])
            day1_day = str(datetime.strptime(day1_date, '%Y-%m-%d').strftime('%a'))
            day1_sunrise = str(json_format['data']['weather'][0]['astronomy'][0]['sunrise'])
            day1_sunset = str(json_format['data']['weather'][0]['astronomy'][0]['sunset'])
            day2_graphic = str(json_format['data']['weather'][1]['hourly'][4]['weatherCode'])
            day2_conditions = str(json_format['data']['weather'][1]['hourly'][4]['weatherDesc'][0]['value'])
            day2_date = str(json_format['data']['weather'][1]['date'])
            day2_max_temp = str(json_format['data']['weather'][1]['maxtempF'])
            day2_min_temp = str(json_format['data']['weather'][1]['mintempF'])
            day2_day = str(datetime.strptime(day2_date, '%Y-%m-%d').strftime('%a'))
            day3_graphic = str(json_format['data']['weather'][2]['hourly'][4]['weatherCode'])
            day3_conditions = str(json_format['data']['weather'][2]['hourly'][4]['weatherDesc'][0]['value'])
            day3_date = str(json_format['data']['weather'][2]['date'])
            day3_max_temp = str(json_format['data']['weather'][2]['maxtempF'])
            day3_min_temp = str(json_format['data']['weather'][2]['mintempF'])
            day3_day = str(datetime.strptime(day3_date, '%Y-%m-%d').strftime('%a'))
            day4_graphic = str(json_format['data']['weather'][3]['hourly'][4]['weatherCode'])
            day4_conditions = str(json_format['data']['weather'][3]['hourly'][4]['weatherDesc'][0]['value'])
            day4_date = str(json_format['data']['weather'][3]['date'])
            day4_max_temp = str(json_format['data']['weather'][3]['maxtempF'])
            day4_min_temp = str(json_format['data']['weather'][3]['mintempF'])
            day4_day = str(datetime.strptime(day4_date, '%Y-%m-%d').strftime('%a'))
            day5_graphic = str(json_format['data']['weather'][4]['hourly'][4]['weatherCode'])
            day5_conditions = str(json_format['data']['weather'][4]['hourly'][4]['weatherDesc'][0]['value'])
            day5_date = str(json_format['data']['weather'][4]['date'])
            day5_max_temp = str(json_format['data']['weather'][4]['maxtempF'])
            day5_min_temp = str(json_format['data']['weather'][4]['mintempF'])
            day5_day = str(datetime.strptime(day5_date, '%Y-%m-%d').strftime('%a'))
            # print current_graphic, day1_graphic, day2_graphic, day3_graphic, day4_graphic, day5_graphic
            sunrise = datetime.strftime((datetime.strptime(day1_sunrise, "%I:%M %p")), "%H:%M")
            sunset = datetime.strftime((datetime.strptime(day1_sunset, "%I:%M %p")), "%H:%M")
            if current_graphic in partly_cloudy:
                if current_time < sunset and current_time > sunrise:
                    current_graphic = 'partly-cloudy-day'
                elif current_time > sunset or current_time < sunrise:
                    current_graphic = 'partly-cloudy-night'
            elif current_graphic in clear_day:
                if current_time < sunset and current_time > sunrise:
                    current_graphic = 'clear-day'
                elif current_time > sunset or current_time < sunrise:
                    current_graphic = 'clear-night'
            elif current_graphic == '122':
                current_conditions = 'Overcast'
                if current_time < sunset and current_time > sunrise:
                    current_graphic = 'partly-cloudy-day'
                elif current_time > sunset or current_time < sunrise:
                    current_graphic = 'partly-cloudy-night'
            elif current_graphic in fog:
                current_graphic = 'fog'
            elif current_graphic in snow:
                current_graphic = 'snow'
            elif current_graphic in sleet:
                current_graphic = 'sleet'
            elif current_graphic in rain:
                current_conditions = 'Rainy'
                current_graphic = 'rain'
            else:
                pass
            if day1_graphic in partly_cloudy:
                day1_graphic = 'partly-cloudy-day'
            elif day1_graphic in clear_day:
                day1_graphic = 'clear-day'
            elif day1_graphic in fog:
                day1_graphic = 'fog'
            elif day1_graphic in snow:
                day1_graphic = 'snow'
            elif day1_graphic in sleet:
                day1_graphic = 'sleet'
            elif day1_graphic in rain:
                day1_conditions = 'Rainy'
                day1_graphic = 'rain'
            else:
                pass
            if day2_graphic in partly_cloudy:
                day2_graphic = 'partly-cloudy-day'
            elif day2_graphic in clear_day:
                day2_graphic = 'clear-day'
            elif day2_graphic in fog:
                day2_graphic = 'fog'
            elif day2_graphic in snow:
                day2_graphic = 'snow'
            elif day2_graphic in sleet:
                day2_graphic = 'sleet'
            elif day2_graphic in rain:
                day2_conditions = 'Rainy'
                day2_graphic = 'rain'
            else:
                pass
            if day3_graphic in partly_cloudy:
                day3_graphic = 'partly-cloudy-day'
            elif day3_graphic in clear_day:
                day3_graphic = 'clear-day'
            elif day3_graphic in fog:
                day3_graphic = 'fog'
            elif day3_graphic in snow:
                day3_graphic = 'snow'
            elif day3_graphic in sleet:
                day3_graphic = 'sleet'
            elif day3_graphic in rain:
                day3_conditions = 'Rainy'
                day3_graphic = 'rain'
            else:
                pass
            if day4_graphic in partly_cloudy:
                day4_graphic = 'partly-cloudy-day'
            elif day4_graphic in clear_day:
                day4_graphic = 'clear-day'
            elif day4_graphic in fog:
                day4_graphic = 'fog'
            elif day4_graphic in snow:
                day4_graphic = 'snow'
            elif day4_graphic in sleet:
                day4_graphic = 'sleet'
            elif day4_graphic in rain:
                day4_conditions = 'Rainy'
                day4_graphic = 'rain'
            else:
                pass
            if day5_graphic in partly_cloudy:
                day5_graphic = 'partly-cloudy-day'
            elif day5_graphic in clear_day:
                day5_graphic = 'clear-day'
            elif day5_graphic in fog:
                day5_graphic = 'fog'
            elif day5_graphic in snow:
                day5_graphic = 'snow'
            elif day5_graphic in sleet:
                day5_graphic = 'sleet'
            elif day5_graphic in rain:
                day5_conditions = 'Rainy'
                day5_graphic = 'rain'
            else:
                pass
            # print current_graphic, day1_graphic, day2_graphic, day3_graphic, day4_graphic, day5_graphic
            if wind_direction == 'N':
                wind_direction = 'North'
            elif wind_direction == 'NNE':
                wind_direction = 'North-Northeast'
            elif wind_direction == 'NE':
                wind_direction = 'Northeast'
            elif wind_direction == 'ENE':
                wind_direction = 'East-Northeast'
            elif wind_direction == 'E':
                wind_direction = 'East'
            elif wind_direction == 'ESE':
                wind_direction = 'East-Southeast'
            elif wind_direction == 'SE':
                wind_direction = 'Southeast'
            elif wind_direction == 'SSE':
                wind_direction = 'South-Southeast'
            elif wind_direction == 'S':
                wind_direction = 'South'
            elif wind_direction == 'SSW':
                wind_direction = 'South-Southwest'
            elif wind_direction == 'SW':
                wind_direction = 'Southwest'
            elif wind_direction == 'WSW':
                wind_direction = 'West-Southwest'
            elif wind_direction == 'W':
                wind_direction = 'West'
            elif wind_direction == 'WNW':
                wind_direction = 'West-Northwest'
            elif wind_direction == 'NW':
                wind_direction = 'Northwest'
            elif wind_direction == 'NNW':
                wind_direction = 'North-Northwest'
        except urllib2.HTTPError as err:
            if err.code == 503:
                print "Weather Onine Unavailable"
                log_exception(e)
                pass
                continue
            elif err.code == 429:
                log_exception(e)
                pass
                continue
            else:
                raise
                log_exception(e)
                pass
                continue
        except Exception, e:
            log_exception(e)
            return str(e)
            continue
        time.sleep(200)


def read_water_pressure():
    global psi, board, psi_read, wp_sensor_value, port
    try:
        board = Arduino('/dev/ttyACM0', baudrate=57600)
        it = pyfirmata.util.Iterator(board)
        it.start()
        read_sensor = board.get_pin('a:0:i')
        while 1:
            sensor_value = read_sensor.read()
            wp_sensor_min = 0.09
            wp_sensor_max = .95
            psi_min = 0.0
            psi_max = 100.0
            if sensor_value is None:
                time.sleep(1)
                pass
            else:
                wp_sensor_value = sensor_value
                wp_sensor_range = (wp_sensor_max - wp_sensor_min)
                psi_range = (psi_max - psi_min)
                psi_read = int((((wp_sensor_value - wp_sensor_min) * psi_range) / wp_sensor_range) + psi_min)
                psi = str("%.1f" % (psi_read,))
            time.sleep(.5)

    except Exception, e:
        log_exception(e)
        return str(e)
        board.exit()


def current_variable_status():
    global psi, start_psi, psi_read, web_start_psi, pump_status, low_status, high_status, maximum_psi, wp_sensor_value, temperature, wind_direction, wind_speed, api_key, \
        current_conditions, current_graphic, day1_day, day1_graphic, day2_day, day2_graphic, day3_day, day3_graphic, day4_day, \
        day4_graphic, day5_day, day5_graphic, day1_max_temp, day1_min_temp, day2_max_temp, day2_min_temp, \
        day3_max_temp, day3_min_temp, day4_max_temp, day4_min_temp, day5_max_temp, day5_min_temp, current_date, \
        day1_conditions, day2_conditions, day3_conditions, day4_conditions, day5_conditions, pump_hour, sweeper_hour, sweeper_duration
    try:
        while 1:
            # print "Variable psi: ", psi
            # print "Variable psi_read: ", psi_read
            # print "Variable start_psi: ", start_psi
            # print "Variable maximum_psi: ", maximum_psi
            # print "Variable web_start_psi: ", web_start_psi
            print "Variable pump_status: ", pump_status
            print "Variable low_status: ", low_status
            print "Variable high_status: ", high_status
            print "Variable sweeper_status: ", sweeper_status
            print "Variable blower_status: ", blower_status
            # print "Variable water_pressure_value: ", wp_sensor_value
            # print "Temperature: ", temperature
            # print "Wind Speed: ", wind_speed
            # print "Wind Direction: ", wind_direction
            # print "Current Graphic: ", current_graphic
            # print "Day 1 Graphic: ", day1_graphic
            # print "Day 2 Graphic: ", day2_graphic
            # print "Day 3 Graphic: ", day3_graphic
            # print "Day 4 Graphic: ", day4_graphic
            # print "Day 5 Graphic: ", day5_graphic
            # print "Current Date: ", current_date
            # print "Current Conditions: ", current_conditions
            # print "Day 1 Conditions: ", day1_conditions
            # print "Day 2 Conditions: ", day2_conditions
            # print "Day 3 Conditions: ", day3_conditions
            # print "Day 4 Conditions: ", day4_conditions
            # print "Day 5 Conditions: ", day5_conditions
            # print "API Key: ", api_key
            # print "Pump Hour: ", pump_hour
            # print "Sweeper Hour: ", sweeper_hour
            # print "Sweeper Duration: ", sweeper_duration
            time.sleep(1)

    except Exception, e:
        log_exception(e)
        return str(e)


def read_monitor_starting_pressure():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off, psi, start_psi, psi_read, web_start_psi, pump_status, low_status, high_status, maximum_psi, read_start_pressure
    try:
        while 1:
            if pump_status == 1:
                if high_status == 1:
                    read_start_pressure = True
                    start_psi = psi_read
                    web_start_psi = str(start_psi)
                else:
                    pass
            elif pump_status == 0:
                read_start_pressure = False
                start_psi = 0
                web_start_psi = "0"
                pass
            time.sleep(10)
            if pump_status == 1:
                if high_status == 1:
                    if read_start_pressure is True:
                        maximum_psi = start_psi + 10
                        if psi_read > maximum_psi:
                            logging.warning('Turning off Pump.  Max Pressure allowed exceeded')
                            pump_low_high = ""
                            high.write(0)
                            low.write(0)
                            pump.write(0)
                        else:
                            pass

    except Exception, e:
        log_exception(e)
        return str(e)


def run_web_server():
    try:
        cherrypy.tree.graft(app, "/")
        cherrypy.server.unsubscribe()
        server = cherrypy._cpserver.Server()
        server.socket_host = "0.0.0.0"
        server.socket_port = 8000
        server.thread_pool = 1000
        server.ssl_module = 'pyopenssl'
        server.ssl_certificate = 'server.crt'
        server.ssl_private_key = 'server.key'
        server.subscribe()
        cherrypy.engine.start()
        cherrypy.engine.block()

    except Exception, e:
        log_exception(e)
        return str(e)


def wait_for_internet_connection():
    try:
        while True:
            try:
                response = urllib2.urlopen('http://www.google.com', timeout=1)
                return
            except urllib2.URLError:
                log_exception(e)
                pass

    except Exception, e:
        log_exception(e)
        return str(e)


def setup_logging_to_file(filename):
    try:
        logging.handlers.RotatingFileHandler(filename, maxBytes=1024, backupCount=2)
        logging.basicConfig(filename=filename,
                            filemode='ab',
                            level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')

    except Exception, e:
        log_exception(e)
        return str(e)


def extract_function_name():
    try:
        tb = sys.exc_info()[-1]
        stk = traceback.extract_tb(tb, 1)
        fname = stk[0][3]
        return fname

    except Exception, e:
        log_exception(e)
        return str(e)


def log_exception(e):
    try:
        logging.error(
            "Function {function_name} raised {exception_class} ({exception_docstring}): {exception_message}".format(
                function_name=extract_function_name(),
                exception_class=e.__class__,
                exception_docstring=e.__doc__,
                exception_message=e.message))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/')
def index():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off, psi, web_start_psi, pump_status, \
        low_status, high_status, sweeper_status, blower_status, wind_direction, wind_speed, temperature, \
        current_conditions, current_graphic, day1_day, day1_graphic, day2_day, day2_graphic, day3_day, day3_graphic, day4_day, \
        day4_graphic, day5_day, day5_graphic, day1_max_temp, day1_min_temp, day2_max_temp, day2_min_temp, \
        day3_max_temp, day3_min_temp, day4_max_temp, day4_min_temp, day5_max_temp, day5_min_temp, current_date, \
        day1_conditions, day2_conditions, day3_conditions, day4_conditions, day5_conditions
    try:
        pump_status = pump.read()
        low_status = low.read()
        high_status = high.read()
        sweeper_status = sweeper.read()
        blower_status = blower.read()
        if pump_status == 1:
            pump_on_off = "on"
        elif pump_status == 0:
            pump_on_off = ""

        if low_status == 1:
            pump_low_high = ""
        elif high_status == 1:
            pump_low_high = "on"

        if sweeper_status == 1:
            sweeper_on_off = "on"
        elif sweeper_status == 0:
            sweeper_on_off = ""

        if blower_status == 1:
            blower_on_off = "on"
        elif blower_status == 0:
            blower_on_off = ""

        build_index_html = open("./templates/index.html", "wb")
        process_index_html = Markup('''\
<meta charset="UTF-8">
<html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="keywords" content="Smart Ui Kit Responsive web template, Bootstrap Web Templates, Flat Web Templates, Android Compatible web template,
    Smartphone Compatible web template, free webdesigns for Nokia, Samsung, LG, SonyEricsson, Motorola web design" />
    <script type="application/x-javascript"> addEventListener("load", function() { setTimeout(hideURLbar, 0); }, false);
        function hideURLbar(){ window.scrollTo(0,1); } </script>
    <!-- //for-mobile-apps -->
    <link href="static/css/bootstrap.css" rel="stylesheet" type="text/css" media="all" />
    <link href="static/css/style.css" rel="stylesheet" type="text/css" media="all" />
    <!-- js -->
    <script type="text/javascript" src="static/js/jquery-2.1.4.min.js"></script>
    <!-- //js -->
    <!--skycons-icons-->
    <script src="static/js/skycons.js"></script>
    <!--//skycons-icons-->
    <link href='https://fonts.googleapis.com/css?family=Bitter:400,400italic,700' rel='stylesheet' type='text/css'>
    <meta charset="utf-8" />
        <title>Pool Automation</title>
        <link rel="stylesheet" href="">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.0.2/jquery.min.js" type="text/javascript">
        </script>
        <script type="text/javascript">
            window.onload = function () {
                'use strict';
                var millisecondsBeforeRefresh = 5000; //Adjust time here
                window.setTimeout(function () {
                    document.location.reload();
                }, millisecondsBeforeRefresh);
            };
        </script>
        <script type="text/javascript">
            $(document).ready(function(){
                $('#pump').on('click', function(){
                    if($("z").hasClass("on")){
                        $.ajax({
                            type: 'POST',
                            url: '/pump_off',
                        });
                        $(this).toggleClass('on');
                    }
                    else{
                        $.ajax({
                            type: 'POST',
                            url: '/pump_on',
                        });
                        $(this).toggleClass('on');
                    }
                });
            });
        </script>
        <script type="text/javascript">
            $(document).ready(function(){
                $('#lowhigh').on('click', function(){
                    if($("b").hasClass("on")){
                        $.ajax({
                            type: 'POST',
                            url: '/pump_low',
                        });
                        $(this).toggleClass('on');
                    }
                    else{
                        $.ajax({
                            type: 'POST',
                            url: '/pump_high',
                        });
                        $(this).toggleClass('on');
                    }
                });
            });
        </script>
        <script type="text/javascript">
            $(document).ready(function(){
                $('#sweeper').on('click', function(){
                    if($("c").hasClass("on")){
                        $.ajax({
                            type: 'POST',
                            url: '/sweeper_off',
                        });
                        $(this).toggleClass('on');
                    }
                    else{
                        $.ajax({
                            type: 'POST',
                            url: '/sweeper_on',
                        });
                        $(this).toggleClass('on');
                    }
                });
            });
        </script>
        <script type="text/javascript">
            $(document).ready(function(){
                $('#blower').on('click', function(){
                    if($("d").hasClass("on")){
                        $.ajax({
                            type: 'POST',
                            url: '/blower_off',
                        });
                        $(this).toggleClass('on');
                    }
                    else{
                        $.ajax({
                            type: 'POST',
                            url: '/blower_on',
                        });
                        $(this).toggleClass('on');
                    }
                });
            });
        </script>
    </head>
    <style>
    /** Styling the Button **/
    z {
        font-family: "FontAwesome";
        text-shadow: 0px 1px 1px rgba(250,250,250,0.1);
        font-size: 32pt;
        display: block;
        position: relative;
        text-decoration: none;
        box-shadow: 0px 3px 0px 0px rgb(34,34,34),
                    0px 7px 10px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -12px 35px 0px rgba(0, 0, 0, .5);
        width: 70px;
        height: 70px;
        border: 0;
        color: rgb(37,37,37);
        border-radius: 35px;
        text-align: center;
        line-height: 79px;
        background-color: rgb(83,87,93);

        transition: color 350ms ease, text-shadow 350ms;
            -o-transition: color 350ms ease, text-shadow 350ms;
            -moz-transition: color 350ms ease, text-shadow 350ms;
            -webkit-transition: color 350ms ease, text-shadow 350ms;
    }
    z:before {
        content: "";
        width: 80px;
        height: 80px;
        display: block;
        z-index: -2;
        position: absolute;
        background-color: transparent;
        left: -5px;
        top: -2px;
        border-radius: 40px;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                    inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    z:active {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
        top: 3px;
    }
    z.on {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
          top: 3px;
         color: #dbe6ff;
          text-shadow: 0px 0px 3px rgb(250,250,250);
    }
    z:active:before, z.on:before {
        top: -5px;
        background-color: transparent;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                     inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    /* Styling the Indicator light */
    z + span {
        display: block;
        width: 8px;
        height: 8px;
        background-color: rgb(226,0,0);
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(226,0,0,0.5);
         border-radius: 4px;
         clear: both;
         position: absolute;
         bottom: 0;
         left: 42%;
         transition: background-color 350ms, box-shadow 700ms;
        -o-transition: background-color 350ms, box-shadow 700ms;
        -moz-transition: background-color 350ms, box-shadow 700ms;
        -webkit-transition: background-color 350ms, box-shadow 700ms;
    }
    z.on + span {
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(135,187,83,0.5);
        background-color: rgb(135,187,83);
    }
    /** Styling the Button **/
    b {
        font-family: "FontAwesome";
        text-shadow: 0px 1px 1px rgba(250,250,250,0.1);
        font-size: 32pt;
        display: block;
        position: relative;
        text-decoration: none;
        box-shadow: 0px 3px 0px 0px rgb(34,34,34),
                    0px 7px 10px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -12px 35px 0px rgba(0, 0, 0, .5);
        width: 70px;
        height: 70px;
        border: 0;
        color: rgb(37,37,37);
        border-radius: 35px;
        text-align: center;
        line-height: 79px;
        background-color: rgb(83,87,93);

        transition: color 350ms ease, text-shadow 350ms;
            -o-transition: color 350ms ease, text-shadow 350ms;
            -moz-transition: color 350ms ease, text-shadow 350ms;
            -webkit-transition: color 350ms ease, text-shadow 350ms;
    }
    b:before {
        content: "";
        width: 80px;
        height: 80px;
        display: block;
        z-index: -2;
        position: absolute;
        background-color: transparent;
        left: -5px;
        top: -2px;
        border-radius: 40px;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                     inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    b:active {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
          top: 3px;
    }
    b.on {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
          top: 3px;
         color: #dbe6ff;
          text-shadow: 0px 0px 3px rgb(250,250,250);
    }
    b:active:before, b.on:before {
        top: -5px;
        background-color: transparent;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                     inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    /* Styling the Indicator light */
    b + span {
        display: block;
        width: 8px;
        height: 8px;
        background-color: rgb(226,0,0);
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(226,0,0,0.5);
         border-radius: 4px;
         clear: both;
         position: absolute;
         bottom: 0;
         left: 42%;
         transition: background-color 350ms, box-shadow 700ms;
        -o-transition: background-color 350ms, box-shadow 700ms;
        -moz-transition: background-color 350ms, box-shadow 700ms;
        -webkit-transition: background-color 350ms, box-shadow 700ms;
    }
    b.on + span {
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(135,187,83,0.5);
        background-color: rgb(135,187,83);
    }
    /** Styling the Button **/
    c {
        font-family: "FontAwesome";
        text-shadow: 0px 1px 1px rgba(250,250,250,0.1);
        font-size: 32pt;
        display: block;
        position: relative;
        text-decoration: none;
        box-shadow: 0px 3px 0px 0px rgb(34,34,34),
                    0px 7px 10px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -12px 35px 0px rgba(0, 0, 0, .5);
        width: 70px;
        height: 70px;
        border: 0;
        color: rgb(37,37,37);
        border-radius: 35px;
        text-align: center;
        line-height: 79px;
        background-color: rgb(83,87,93);

        transition: color 350ms ease, text-shadow 350ms;
            -o-transition: color 350ms ease, text-shadow 350ms;
            -moz-transition: color 350ms ease, text-shadow 350ms;
            -webkit-transition: color 350ms ease, text-shadow 350ms;
    }
    c:before {
        content: "";
        width: 80px;
        height: 80px;
        display: block;
        z-index: -2;
        position: absolute;
        background-color: transparent;
        left: -5px;
        top: -2px;
        border-radius: 40px;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                     inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    c:active {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
          top: 3px;
    }
    c.on {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
          top: 3px;
         color: #dbe6ff;
          text-shadow: 0px 0px 3px rgb(250,250,250);
    }
    c:active:before, c.on:before {
        top: -5px;
        background-color: transparent;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                     inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    /* Styling the Indicator light */
    c + span {
        display: block;
        width: 8px;
        height: 8px;
        background-color: rgb(226,0,0);
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(226,0,0,0.5);
         border-radius: 4px;
         clear: both;
         position: absolute;
         bottom: 0;
         left: 42%;
         transition: background-color 350ms, box-shadow 700ms;
        -o-transition: background-color 350ms, box-shadow 700ms;
        -moz-transition: background-color 350ms, box-shadow 700ms;
        -webkit-transition: background-color 350ms, box-shadow 700ms;
    }
    c.on + span {
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(135,187,83,0.5);
        background-color: rgb(135,187,83);
    }
    /** Styling the Button **/
    d {
        font-family: "FontAwesome";
        text-shadow: 0px 1px 1px rgba(250,250,250,0.1);
        font-size: 32pt;
        display: block;
        position: relative;
        text-decoration: none;
        box-shadow: 0px 3px 0px 0px rgb(34,34,34),
                    0px 7px 10px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -12px 35px 0px rgba(0, 0, 0, .5);
        width: 70px;
        height: 70px;
        border: 0;
        color: rgb(37,37,37);
        border-radius: 35px;
        text-align: center;
        line-height: 79px;
        background-color: rgb(83,87,93);

        transition: color 350ms ease, text-shadow 350ms;
            -o-transition: color 350ms ease, text-shadow 350ms;
            -moz-transition: color 350ms ease, text-shadow 350ms;
            -webkit-transition: color 350ms ease, text-shadow 350ms;
    }
    d:before {
        content: "";
        width: 80px;
        height: 80px;
        display: block;
        z-index: -2;
        position: absolute;
        background-color: transparent;
        left: -5px;
        top: -2px;
        border-radius: 40px;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                     inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    d:active {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
          top: 3px;
    }
    d.on {
        box-shadow: 0px 0px 0px 0px rgb(34,34,34),
                    0px 3px 7px 0px rgb(17,17,17),
                    inset 0px 1px 1px 0px rgba(250, 250, 250, .2),
                    inset 0px -10px 35px 5px rgba(0, 0, 0, .5);
        background-color: rgb(83,87,93);
          top: 3px;
         color: #dbe6ff;
          text-shadow: 0px 0px 3px rgb(250,250,250);
    }
    d:active:before, d.on:before {
        top: -5px;
        background-color: transparent;
        box-shadow: 0px 1px 0px 0px rgba(250,250,250,0.1),
                     inset 0px 1px 2px rgba(0, 0, 0, 0.5);
    }
    /* Styling the Indicator light */
    d + span {
        display: block;
        width: 8px;
        height: 8px;
        background-color: rgb(226,0,0);
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(226,0,0,0.5);
         border-radius: 4px;
         clear: both;
         position: absolute;
         bottom: 0;
         left: 42%;
         transition: background-color 350ms, box-shadow 700ms;
        -o-transition: background-color 350ms, box-shadow 700ms;
        -moz-transition: background-color 350ms, box-shadow 700ms;
        -webkit-transition: background-color 350ms, box-shadow 700ms;
    }
    d.on + span {
        box-shadow: inset 0px 1px 0px 0px rgba(250,250,250,0.5),
                    0px 0px 3px 2px rgba(135,187,83,0.5);
        background-color: rgb(135,187,83);
    }
    h1 {
      font-family: "Avant Garde", Avantgarde, "Century Gothic", CenturyGothic, "AppleGothic", sans-serif;
      font-size: 23px;
      padding: 5px 3px;
      text-align: center;
      text-rendering: optimizeLegibility;
    }
    h1.elegantshadow {
      color: #212121;
      background-color: transparent;
      letter-spacing: .01em;
      text-shadow: 0px 0px 0 #767676, -1px 2px 1px #737272;
    }
    h9 {
      font-family: "Avant Garde", Avantgarde, "Century Gothic", CenturyGothic, "AppleGothic", sans-serif;
      font-size: 12px;
      padding: 5px 3px;
      text-align: center;
      text-rendering: optimizeLegibility;
    }
    h9.elegantshadow {
      color: #212121;
      background-color: transparent;
      letter-spacing: .01em;
      text-shadow: 0px 0px 0 #767676, -1px 2px 1px #737272;
    }
    h10 {
      font-family: "Avant Garde", Avantgarde, "Century Gothic", CenturyGothic, "AppleGothic", sans-serif;
      font-size: 40px;
      padding: 5px 3px;
      text-align: center;
      text-rendering: optimizeLegibility;
    }
    h10.elegantshadow {
      color: #212121;
      background-color: transparent;
      letter-spacing: .01em;
      text-shadow: 0px 0px 0 #767676, -1px 2px 1px #737272;
    }
    section {
        margin: 7px auto 0;
        width: 75px;
        height: 95px;
        position: relative;
        text-align: center;
    }
    :active, :focus {
        outline: 0;
    }
    /** Font-Face **/
    @font-face {
      font-family: "FontAwesome";
      src: url("/static/fonts/fontawesome-webfont.eot");
      src: url("/static/fonts/fontawesome-webfont.eot?#iefix") format('eot'),
             url("/static/fonts/fontawesome-webfont.woff") format('woff'),
             url("/static/fonts/fontawesome-webfont.ttf") format('truetype'),
             url("/static/fonts/fontawesome-webfont.svg#FontAwesome") format('svg');
      font-weight: normal;
      font-style: normal;
    }
    .box1 {
        margin: auto;
        width: 300px;
        height: 205px;
        border: 0px solid blue;
    }
    .floating-box {
        float: left;
        padding:0px 20px;
        margin: auto 1.25em;
        display: inline-block;
    }
    .menu-box {
        margin: auto;
        width: 100%;
        height: 5%;
        border: 0px solid blue;
    }
    .after-box {
        clear: both;
    }
    body {
        margin:0;
        background-color: #dbe6ff;
        font-weight: bold
    }
    ul.topnav {
      list-style-type: none;
      width: 100%;
      margin: 0;
      padding: 0;
      overflow: hidden;
      height: 10%;
      background-color: transparent;
    }

    ul.topnav li {
      float: left;
    }

    ul.topnav li a {
      display: inline-block;
      color: #212121;
      text-align: center;
      padding: 8px 8px;
      text-decoration: none;
      transition: 0.3s;
      font-size: 20px;
    }

    ul.topnav li a:hover {
      background-color: transparent;
    }

    ul.topnav li.icon {
      display: none;
    }

    @media screen and (max-width:680px) {
      ul.topnav li:not(:first-child) {
        display: none;
      }
      ul.topnav li.icon {
        float: right;
        display: inline-block;
      }
    }
    @media screen and (max-width:680px) {
      ul.topnav.responsive {
        position: relative;
      }
      ul.topnav.responsive li.icon {
        position: absolute;
        right: 0;
        top: 0;
      }
      ul.topnav.responsive li {
        float: none;
        display: inline;
      }
      ul.topnav.responsive li a {
        display: block;
        text-align: left;
      }
    }
    </style>
    <body>
      <ul class="topnav" id="myTopnav", style="position: fixed;">
        <li><a href="/settings">Settings</a></li>
        <li class="icon">
          <a href="/settings" style="font-size:20px;" onclick="myFunction()">&#9776;</a>
        </li>
      </ul>
      <script>
      function myFunction() {
          var x = document.getElementById("myTopnav");
          if (x.className === "topnav") {
              x.className += " responsive";
          } else {
              x.className = "topnav";
          }
      }
      </script>
        <main><br><br>
            <div class='box1' style:"display: inline-table; margin: center;">
                <h9 class='elegantshadow'>
                <div class="floating-box">
                    <section>
                        On/Off
                        <z href="#" id="pump" class="''' + pump_on_off + '''">&#xF011;</z>
                            <span></span>
                    </section>
                </div>
                <div class="floating-box">
                    <section>
                        Low/High
                        <b href="#" id="lowhigh" class="''' + pump_low_high + '''">&#xF011;</b>
                            <span></span>
                    </section>
                </div>
                <div class="floating-box">
                    <section>
                        Sweeper
                        <c href="#" id="sweeper" class="''' + sweeper_on_off + '''">&#xF011;</c>
                            <span></span>
                    </section>
                </div>
                <div class="floating-box">
                    <section>
                        Blower
                        <d href="#" id="blower" class="''' + blower_on_off + '''">&#xF011;</d>
                            <span></span>
                    </section>
                </div>
                <div class="after-box">
                    <h9>Start Pressure ''' + web_start_psi + '''</h9>
                    <h9>Current Pressure ''' + psi + '''</h9>
                </div>
            </div>
        </main>
        <div class="center">
            <div class="climate-icons">
                <div class="climate-icons-left">
                    <div class="strip">
                    </div>
                    <div class="content-top">
                        <div class="content-left">
                            <center>
                                <h9 class='elegantshadow'>''' + current_date + '''</h9>
                                <h10 class='elegantshadow'>''' + temperature + '''&#8457</h10>
                            </center>
                        </div>
                        <div class="content-right">
                            <h9 class='elegantshadow'>Currently</h9>
                                <figure class="icons">
                                    <canvas class="''' + current_graphic + '''" width="45" height="45">
                                    </canvas>
                                </figure>
                            <h9 class='elegantshadow'>''' + current_conditions + '''</h9>
                        </div>
                        <div class="content-last">
                            <h9 class='elegantshadow'>''' + day1_day + '''</h9><br>
                                <figure class="icons">
                                    <canvas class="''' + day1_graphic + '''" width="45" height="45">
                                    </canvas>
                                </figure>
                            <h9 class='elegantshadow'>''' + day1_max_temp + '''/''' + day1_min_temp + '''</h9>
                            <h9 class='elegantshadow'>''' + day1_conditions + '''</h9><br>
                        </div>
                        <div class="content-last">
                            <h9 class='elegantshadow'>''' + day2_day + '''</h9><br>
                                <figure class="icons">
                                    <canvas class="''' + day2_graphic + '''" width="45" height="45">
                                    </canvas>
                                </figure>
                            <h9 class='elegantshadow'>''' + day2_max_temp + '''/''' + day2_min_temp + '''</h9>
                            <h9 class='elegantshadow'>''' + day2_conditions + '''</h9><br>
                        </div>
                        <div class="content-last">
                            <h9 class='elegantshadow'>''' + day3_day + '''</h9><br>
                                <figure class="icons">
                                    <canvas class="''' + day3_graphic + '''" width="45" height="45">
                                    </canvas>
                                </figure>
                            <h9 class='elegantshadow'>''' + day3_max_temp + '''/''' + day3_min_temp + '''</h9>
                            <h9 class='elegantshadow'>''' + day3_conditions + '''</h9><br>
                        </div>
                        <div class="content-last">
                            <h9 class='elegantshadow'>''' + day4_day + '''</h9><br>
                                <figure class="icons">
                                    <canvas class="''' + day4_graphic + '''" width="45" height="45">
                                    </canvas>
                                </figure>
                            <h9 class='elegantshadow'>''' + day4_max_temp + '''/''' + day4_min_temp + '''</h9>
                            <h9 class='elegantshadow'>''' + day4_conditions + '''</h9><br>
                        </div>
                        <div class="content-last">
                            <h9 class='elegantshadow'>''' + day5_day + '''</h9><br>
                                <figure class="icons">
                                    <canvas class="''' + day5_graphic + '''" width="45" height="45">
                                    </canvas>
                                </figure>
                            <h9 class='elegantshadow'>''' + day5_max_temp + '''/''' + day5_min_temp + '''</h9>
                            <h9 class='elegantshadow'>''' + day5_conditions + '''</h9><br>
                        </div>
                        <div class="clearfix">
                        </div>
                            <script>
                                var icons = new Skycons({"color": "#999"}),
                                  list  = [
                                    "clear-night", "partly-cloudy-night"
                                  ],
                                  i;

                                  for(i = list.length; i--; ) {
                                    var weatherType = list[i],
                                        elements = document.getElementsByClassName( weatherType );
                                          console.log(elements);
                                        for (e = elements.length; e--;){
                                            icons.set( elements[e], weatherType );
                                            }
                                        }
                                var icons = new Skycons({"color": "#E8BA0A"}),
                                  list  = [
                                    "clear-day", "partly-cloudy-day",
                                    "cloudy", "rain", "sleet", "snow", "wind",
                                    "fog"
                                  ],
                                  i;

                                  for(i = list.length; i--; ) {
                                    var weatherType = list[i],
                                        elements = document.getElementsByClassName( weatherType );
                                          console.log(elements);
                                        for (e = elements.length; e--;){
                                            icons.set( elements[e], weatherType );
                                            }
                                        }
                                    icons.play();
                            </script>
                    </div>
                </div>
            </div>
        </div>
    </body>
</html>''')
        build_index_html.write(process_index_html + '\n')
        build_index_html.close()
        return render_template('index.html')

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/pump_on', methods=['POST'])
def pump_on():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off, psi, start_psi
    try:
        high.write(0)
        low.write(1)
        pump.write(1)
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/pump_off', methods=['POST'])
def pump_off():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off
    try:
        pump_low_high = ""
        pump_on_off = ""
        high.write(0)
        low.write(0)
        pump.write(0)
        sweeper_on_off = ""
        sweeper.write(0)
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/pump_low', methods=['POST'])
def pump_low():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off
    try:
        pump_status = pump.read()
        if pump_status == 1:
            pump_low_high = ""
            high.write(0)
            low.write(1)
        elif pump_status == 0:
            pump_low_high = ""
            high.write(0)
            low.write(0)
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/pump_high', methods=['POST'])
def pump_high():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off
    try:
        pump_status = pump.read()
        if pump_status == 1:
            pump_low_high = "on"
            low.write(0)
            high.write(1)
        elif pump_status == 0:
            pump_low_high = ""
            low.write(0)
            high.write(0)
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/sweeper_on', methods=['POST'])
def sweeper_on():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off
    try:
        pump_status = pump.read()
        if pump_status == 1:
            sweeper_on_off = "on"
            sweeper.write(1)
        elif pump_status == 0:
            sweeper_on_off = ""
            sweeper.write(0)
            logging.warning('Pump is off.  Turning off Sweeper')
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/sweeper_off', methods=['POST'])
def sweeper_off():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off
    try:
        sweeper_on_off = ""
        sweeper.write(0)
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/blower_on', methods=['POST'])
def blower_on():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off
    try:
        blower_on_off = "on"
        blower.write(1)
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/blower_off', methods=['POST'])
def blower_off():
    global pump_on_off, pump_low_high, sweeper_on_off, blower_on_off
    try:
        blower_on_off = ""
        blower.write(0)
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/settings')
def settings():
    global pump_hour, sweeper_hour, sweeper_duration, check_pump, check_sweeper, check_pump_5, check_pump_6, check_pump_7, check_pump_8, check_pump_9, check_pump_10, \
        check_sweeper_5, check_sweeper_6, check_sweeper_7, check_sweeper_8, check_sweeper_9, check_sweeper_10, sweeper_duration_1, sweeper_duration_2, sweeper_duration_3, \
        sweeper_duration_4, sweeper_duration_5, sweeper_duration_6
    pump_cfg = open('./pump.cfg', 'r')
    sweeper_cfg = open('./sweeper.cfg', 'r')
    duration_cfg = open('./duration.cfg', 'r')
    pump_hour = pump_cfg.read()
    sweeper_hour = sweeper_cfg.read()
    sweeper_duration = duration_cfg.read()
    pump_cfg.close()
    sweeper_cfg.close()
    duration_cfg.close()
    check_pump_5 = ""
    check_pump_6 = ""
    check_pump_7 = ""
    check_pump_8 = ""
    check_pump_9 = ""
    check_pump_10 = ""
    check_sweeper_5 = ""
    check_sweeper_6 = ""
    check_sweeper_7 = ""
    check_sweeper_8 = ""
    check_sweeper_9 = ""
    check_sweeper_10 = ""
    sweeper_duration_1 = ""
    sweeper_duration_2 = ""
    sweeper_duration_3 = ""
    sweeper_duration_4 = ""
    sweeper_duration_5 = ""
    sweeper_duration_6 = ""
    if pump_hour == '5':
        check_pump_5 = "checked"
    if pump_hour == '6':
        check_pump_6 = "checked"
    elif pump_hour == '7':
        check_pump_7 = "checked"
    elif pump_hour == '8':
        check_pump_8 = "checked"
    elif pump_hour == '9':
        check_pump_9 = "checked"
    elif pump_hour == '10':
        check_pump_10 = "checked"
    if sweeper_hour == '5':
        check_sweeper_5 = "checked"
    if sweeper_hour == '6':
        check_sweeper_6 = "checked"
    elif sweeper_hour == '7':
        check_sweeper_7 = "checked"
    elif sweeper_hour == '8':
        check_sweeper_8 = "checked"
    elif sweeper_hour == '9':
        check_sweeper_9 = "checked"
    elif sweeper_hour == '10':
        check_sweeper_10 = "checked"
    if sweeper_duration == '1':
        sweeper_duration_1 = "checked"
    elif sweeper_duration == '2':
        sweeper_duration_2 = "checked"
    elif sweeper_duration == '3':
        sweeper_duration_3 = "checked"
    elif sweeper_duration == '4':
        sweeper_duration_4 = "checked"
    elif sweeper_duration == '5':
        sweeper_duration_5 = "checked"
    elif sweeper_duration == '6':
        sweeper_duration_6 = "checked"
    try:
        build_settings_html = open("./templates/settings.html", "wb")
        process_settings_html = Markup('''\
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="keywords" content="Smart Ui Kit Responsive web template, Bootstrap Web Templates, Flat Web Templates, Android Compatible web template,
        Smartphone Compatible web template, free webdesigns for Nokia, Samsung, LG, SonyEricsson, Motorola web design" />
        <link href="static/css/bootstrap.css" rel="stylesheet" type="text/css" media="all" />
        <link href="static/css/style.css" rel="stylesheet" type="text/css" media="all" />
        <link href='https://fonts.googleapis.com/css?family=Bitter:400,400italic,700' rel='stylesheet' type='text/css'>
        <!-- js -->
        <script type="text/javascript" src="static/js/jquery-2.1.4.min.js"></script>
        <!-- //js -->
        <link rel="stylesheet" type="text/css" href="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.12/themes/dot-luv/jquery-ui.css" />
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.0/jquery.min.js" type="text/javascript"></script>
        <script src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.12/jquery-ui.min.js" type="text/javascript"></script>
        <script src="https://code.jquery.com/ui/1.8.17/jquery-ui.min.js"></script>
        <script src="jquery.ui.touch-punch.min.js"></script>
        <script src="static/js/jquery.ui.timeslider.js"> </script>
          <title>Pool Automation</title>

    </head>
<style>
body {
    margin:0;
    background-color: #dbe6ff;
    font-weight: bold;
}
h1 {
  font-family: "Avant Garde", Avantgarde, "Century Gothic", CenturyGothic, "AppleGothic", sans-serif;
  font-size: 80%;
  padding: 5px 3px;
  text-align: center;
  text-rendering: optimizeLegibility;
}
h1.elegantshadow {
  color: #212121;
  background-color: transparent;
  letter-spacing: .01em;
  text-shadow: 0px 0px 0 #767676, -1px 2px 1px #737272;
}
section {
    margin: 7px auto 0;
    width: 75px;
    height: 95px;
    position: relative;
    text-align: center;
}
:active, :focus {
    outline: 0;
}
/** Font-Face **/
@font-face {
  font-family: "FontAwesome";
  src: url("static/fonts/fontawesome-webfont.eot");
  src: url("static/fonts/fontawesome-webfont.eot?#iefix") format('eot'),
         url("static/fonts/fontawesome-webfont.woff") format('woff'),
         url("static/fonts/fontawesome-webfont.ttf") format('truetype'),
         url("static/fonts/fontawesome-webfont.svg#FontAwesome") format('svg');
  font-weight: normal;
  font-style: normal;
}
.button-box {
    display: inline-block;
    position: relative;
    margin: 1%;
    float: center;
    width: 30%;
    height: 0px;
}
.slider-box {
    margin: auto;
    width: 100%;
    height: 60%;
    border: 0px solid blue;
}
.menu-box {
    margin: auto;
    width: 100%;
    height: 10%;
    border: 0px solid blue;
}
ul.topnav {
  list-style-type: none;
  width: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
  background-color: transparent;
  height: 10%;
}

ul.topnav li {float: left;}

ul.topnav li a {
  display: inline-block;
  color: #212121;
  text-align: center;
  padding: 8px 8px;
  text-decoration: none;
  transition: 0.3s;
  font-size: 20px;
}

ul.topnav li a:hover {background-color: transparent;}

ul.topnav li.icon {display: none;}

@media screen and (max-width:680px) {
  ul.topnav li:not(:first-child) {display: none;}
  ul.topnav li.icon {
    float: right;
    display: inline-block;
  }
}

@media screen and (max-width:680px) {
  ul.topnav.responsive {position: relative;}
  ul.topnav.responsive li.icon {
    position: absolute;
    right: 0;
    top: 0;
  }
  ul.topnav.responsive li {
    float: none;
    display: inline;
  }
  ul.topnav.responsive li a {
    display: block;
    text-align: left;
  }
}
.icon-arrow-right:before{
    content: '';
    background:url(static/images/img-sp.png)no-repeat -117px -304px;
    display: block;
    width: 27px;
    height: 25px;
}
.btn1 {
    border: none;
    font-family: inherit;
    font-size: inherit;
    color: inherit;
    background: none;
    cursor: pointer;
    padding: 25px 80px;
    display: inline-block;
    margin:5px;
    text-transform: uppercase;
    letter-spacing: 1px;
    outline: none;
    position: relative;
    -webkit-transition: all 0.3s;
    -moz-transition: all 0.3s;
    transition: all 0.3s;
}
.btn1:after {
    content: '';
    position: absolute;
    z-index: -1;
    -webkit-transition: all 0.3s;
    -moz-transition: all 0.3s;
    transition: all 0.3s;
}
.btn1:before {
    font-family: 'icomoon';
    speak: none;
    font-style: normal;
    font-weight: normal;
    font-variant: normal;
    text-transform: none;
    line-height: 1;
    position: relative;
    -webkit-font-smoothing: antialiased;
}
.btn-7 {
    background: #17aa56;
    color: #dbe6ff;
    border-radius: 7px;
    box-shadow: 0 5px #119e4d;
    padding: 25px 60px 25px 90px;
}
.btn-7c {
    overflow: hidden;
}

.btn-7c:before {
    color: #dbe6ff;
    z-index: 1;
}
.btn-7c:after {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    z-index: 0;
    width: 0;
    background: #0a833d;
    -webkit-transition: none;
    -moz-transition: none;
    transition: none;
}
.btn-7c.btn-activated:after {
    -webkit-animation: fillToRight 0.7s forwards;
    -moz-animation: fillToRight 0.7s forwards;
    animation: fillToRight 0.7s forwards;
    -o-animation: fillToRight 0.7s forwards;
    -ms-animation: fillToRight 0.7s forwards;
}
@media (max-width: 1080px){
  .btn-7 {
        padding: 25px 36px 25px 70px;
    }
    .btn-icon-only {
        padding: 25px 30px !important;
    }
}
.btn-7c {
    overflow: hidden;
}
.btn-7c:before {
    color: #dbe6ff;
    z-index: 1;
}
.btn-7c:after {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    z-index: 0;
    width: 0;
    background: #0a833d;
    -webkit-transition: none;
    -moz-transition: none;
    transition: none;
}
.btn-7c.btn-activated:after {
    -webkit-animation: fillToRight 0.7s forwards;
    -moz-animation: fillToRight 0.7s forwards;
    animation: fillToRight 0.7s forwards;
    -o-animation: fillToRight 0.7s forwards;
    -ms-animation: fillToRight 0.7s forwards;
}
.btn-icon-only {
    font-size: 0;
    padding: 25px 30px;
}
.btn-icon-only:before {
    position: absolute;
    top: 12px;
    left: 17px;
    width: 100%;
    height: 100%;
    font-size: 26px;
    line-height: 54px;
    -webkit-backface-visibility: hidden;
    -moz-backface-visibility: hidden;
    backface-visibility: hidden;
    -o-backface-visibility: hidden;
    -ms-backface-visibility: hidden;
}
input[type="radio"]{
    width: 30px;
    height: 30px;
    border: 0px solid blue;
}
</style>
    <body>
    <div class="menu-box">
        <ul class="topnav" id="myTopnav" style="position: fixed;">
          <li><a href="/">Home</a></li>
          <li class="icon">
            <a href="/" style="font-size:20px;" onclick="myFunction()">&#9776;</a>
          </li>
        </ul>
        <script>
        function myFunction() {
            var x = document.getElementById("myTopnav");
            if (x.className === "topnav") {
                x.className += " responsive";
            } else {
                x.className = "topnav";
            }
        }
        </script>
    </div>
        <main>
          <div>
              <h1 class='elegantshadow'>
              <form action="/make_changes" method="POST" style=" font-weight: bold;">
                Pump Start Time<br>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="pump_hour" value="5" ''' + check_pump_5 + '''><br>5AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="pump_hour" value="6" ''' + check_pump_6 + '''><br>6AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="pump_hour" value="7" ''' + check_pump_7 + '''><br>7AM
                </div><br>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="pump_hour" value="8" ''' + check_pump_8 + '''><br>8AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="pump_hour" value="9" ''' + check_pump_9 + '''><br>9AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="pump_hour" value="10" ''' + check_pump_10 + '''><br>10AM
                </div><br><br>
                Sweeper Start Time<br>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_hour" value="5" ''' + check_sweeper_5 + '''><br> 5AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_hour" value="6" ''' + check_sweeper_6 + '''><br> 6AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_hour" value="7" ''' + check_sweeper_7 + '''><br> 7AM
                </div><br>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_hour" value="8" ''' + check_sweeper_8 + '''><br> 8AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_hour" value="9" ''' + check_sweeper_9 + '''><br> 9AM
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_hour" value="10" ''' + check_sweeper_10 + '''><br> 10AM
                </div><br><br>
                Sweeper Duration<br>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_duration" value="1" ''' + sweeper_duration_1 + '''><br> 1hr
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_duration" value="2" ''' + sweeper_duration_2 + '''><br> 2hrs
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_duration" value="3" ''' + sweeper_duration_3 + '''><br> 3hrs
                </div><br>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_duration" value="4" ''' + sweeper_duration_4 + '''><br> 4hrs
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_duration" value="5" ''' + sweeper_duration_5 + '''><br> 5hrs
                </div>
                <div class="button-box" style="margin: center;">
                    <input type="radio" name="sweeper_duration" value="6" ''' + sweeper_duration_6 + '''><br> 6hrs
                </div><br><br>
                <input type="submit" value="Ok" href="/">
              </form>
            </div>
      </main>
</body>
</html>''')
        if check_pump_5 == 'checked':
            pump_hour = '5'
        if check_pump_6 == 'checked':
            pump_hour = '6'
        elif check_pump_7 == 'checked':
            pump_hour = '7'
        elif check_pump_8 == 'checked':
            pump_hour = '8'
        elif check_pump_9 == 'checked':
            pump_hour = '9'
        elif check_pump_10 == 'checked':
            pump_hour = '10'
        if check_sweeper_5 == 'checked':
            sweeper_hour = '5'
        if check_sweeper_6 == 'checked':
            sweeper_hour = '6'
        elif check_sweeper_7 == 'checked':
            sweeper_hour = '7'
        elif check_sweeper_8 == 'checked':
            sweeper_hour = '8'
        elif check_sweeper_9 == 'checked':
            sweeper_hour = '9'
        elif check_sweeper_10 == 'checked':
            sweeper_hour = '10'
        if sweeper_duration_1 == 'checked':
            sweeper_duration = '1'
        elif sweeper_duration_2 == 'checked':
            sweeper_duration = '2'
        elif sweeper_duration_3 == 'checked':
            sweeper_duration = '3'
        elif sweeper_duration_4 == 'checked':
            sweeper_duration = '4'
        elif sweeper_duration_5 == 'checked':
            sweeper_duration = '5'
        elif sweeper_duration_6 == 'checked':
            sweeper_duration = '6'
        build_settings_html.write(process_settings_html + '\n')
        build_settings_html.close()
        return render_template('settings.html')

    except Exception, e:
        log_exception(e)
        return str(e)


@app.route('/make_changes', methods=['GET', 'POST'])
def make_changes():
    global pump_hour, sweeper_hour, sweeper_duration, pump_cfg, sweeper_cfg, duration_cfg
    try:
        pump_hour = request.form['pump_hour']
        sweeper_hour = request.form['sweeper_hour']
        sweeper_duration = request.form['sweeper_duration']
        pump_cfg = open("pump.cfg", "wb")
        sweeper_cfg = open("sweeper.cfg", "wb")
        duration_cfg = open("duration.cfg", "wb")
        pump_cfg.write(str(pump_hour))
        sweeper_cfg.write(str(sweeper_hour))
        duration_cfg.write(str(sweeper_duration))
        pump_cfg.close()
        sweeper_cfg.close()
        duration_cfg.close()
        return redirect(url_for('index'))

    except Exception, e:
        log_exception(e)
        return str(e)

t1 = Thread(target=setup_logging_to_file("pool.log"))
t2 = Thread(target=get_weather_loop)
t3 = Thread(target=read_water_pressure)
t4 = Thread(target=read_monitor_starting_pressure)
t5 = Thread(target=run_web_server)
t6 = Thread(target=start_pump_scheduler)
# t7 = Thread(target = current_variable_status)

t1.start()
t2.start()
t3.start()
t4.start()
t5.start()
t6.start()
# t7.start()
