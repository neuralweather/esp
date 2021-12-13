# The MIT License (MIT)
#
# Copyright (C) 2021 Simon Meins
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


from machine import Pin, SoftI2C, deepsleep, UART
from network import WLAN, STA_IF
from http import get, post, HTTPResponse
from ads1x15 import ADS1115
from bme280 import BME280
from time import sleep
from config import WLAN_SSID, WLAN_PASSWORD, DESTINATION_URL, DEEPSLEEP_TIME, ERROR_RETRY_TIME

def connect_wlan(ssid: str, password: str):

    """
    Connect to a WLAN network.
    parameter ssid: SSID (name) of the WLAN network
    parameter password: WLAN password
    """

    wlan = WLAN(STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print(f"Connecting to WLAN network {ssid} ...")
        wlan.connect(ssid, password)

        while not wlan.isconnected():
            pass
        
        # Configure MAC address
        wlan.config("mac")

    print(f"Connected to {ssid}\n")


# I2C instance to communicate with all I2C devices (slaves) 
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)

# BME280 instance to read the temperature, humidity, and pressure from the BME280 sensor via I2C
bme_sensor = BME280(i2c=i2c)

# ADS1115 instance to communicate with the Analog/Digital converter via I2C
# Channel 0: Anemometer
# Channel 1: Rain/water sensor
ad_sensor = ADS1115(i2c, 0x48)

# UART (Universal Asynchronous Receiver Transmitter) instance for serial communication on pin 33 (Tx) and pin 32 (Rx)
# The serial interface is used for debugging purposes only!
serial = UART(1, baudrate=9600, tx=33, rx=32)

connect_wlan(WLAN_SSID, WLAN_PASSWORD)

def read_wind_speed():

    """
    Read the current wind speed of the anemometer.
    returns: Absolute wind speed
    """

    return abs(ad_sensor.read(channel1=0))

def read_rain():

    """
    Read the current rain/water level of the rain/water sensor.
    returns: Absolute rain/water level
    """

    return abs(ad_sensor.read(channel1=1))

def send_data(url: str, http_body_json_data: dict) -> HTTPResponse:

    """
    Send the weather data to the server via HTTP POST request.
    parameter url [string]: Destination URL to send the weather data to
    parameter http_body_json_data [dictionary]: Weather data encoded as JSON
    returns: HTTPResponse from the server
    """

    return post(url=url, json=http_body_json_data)

def debug_message(message: str):

    """
    Prints a debug message to the screen and transmits it via the serial (UART) interface.
    parameter message [string]: Debug message to be displayed
    """

    print(message)
    serial.write(message)

def http_debug_message(http_response: HTTPResponse):

    """
    Prints a HTTP debug message to the screen and transmits it via the serial (UART) interface.
    parameter http_response [HTTPResponse]: HTTP response from the server (for status code and response content)
    """
    
    if http_response.status_code == 200:
        debug_message(f"Successfully sent HTTP POST request to: {DESTINATION_URL}")

    debug_message(f"Received response from {DESTINATION_URL}\nStatus code: {http_response.status_code}\nContent: {http_response.text}\n")

while True:
    try:

        # Measure weather data (temperature, humidity, pressure, wind speed, rain/water level)
        temperature, humidity, pressure = bme_sensor.temperature, bme_sensor.humidity, bme_sensor.pressure
        wind_speed = read_wind_speed()
        rain       = read_rain()

        # 'Print' weather data debug message 
        debug_message(f"Temperature: {temperature}\nHumidity: {humidity}\nPressure: {pressure}\nWind speed: {wind_speed}\nRain: {rain}\n")

        # Create dictionary (JSON) object containing the weather data
        http_body_json_data = {
            "temperature": temperature,
            "humidity"   : humidity,
            "pressure"   : pressure,
            "windspeed"  : wind_speed,
            "rain"       : rain
        }

        # Send the weather data to the server
        http_response = send_data(DESTINATION_URL, http_body_json_data)

        # 'Print' HTTP debug message
        http_debug_message(http_response)

        # Go into deepsleep mode for DEEPSLEEP_TIME microseconds
        deepsleep(DEEPSLEEP_TIME)

    except Exception as e:

        # Catch all occurring errors (exceptions) and 'print' debug message
        # After ERROR_RETRY_TIME seconds try again to measure and send the weather data
        debug_message(f"Error occurred, retry in {ERROR_RETRY_TIME} seconds ...")
        sleep(ERROR_RETRY_TIME)
