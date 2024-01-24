import time
import requests
import json
import pandas as pd
from dotenv import load_dotenv
import os
import numpy as np
import yfinance as yf

from analyzers.informants.ema import EMA
from analyzers.utils import IndicatorUtils


# Load environment variables from .env file
load_dotenv()

# Define constants
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
OPEN_ID = os.getenv("OPEN_ID")
template_id = os.getenv("TEMP_ID")

# Define a function to get the access token for WeChat API


def get_access_token():
    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}'
    response = requests.get(url).json()
    access_token = response.get('access_token')
    return access_token

# Define a function to send a message to the user via WeChat API


def send_message(message, current_price):
    access_token = get_access_token()
    body = {
        "touser": OPEN_ID,
        "template_id": template_id.strip(),
        "url": "https://weixin.qq.com",
        "data": {
            "message": {
                "value": message
            },
            "current_price": {
                "value": f"${current_price:.2f}"
            }
        }
    }
    url = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}'.format(
        access_token)
    response = requests.post(url, json.dumps(body)).json()
    if response['errcode'] != 0:
        print(f'Failed to send message: {response["errmsg"]}')

# Define a function to generate trading signals based on technical analysis


def generate_signal(data):
    # Calculate the 12-day and 26-day moving averages using pandas
    data['MA_12'] = data['Close'].rolling(window=12).mean()
    data['MA_26'] = data['Close'].rolling(window=26).mean()

    # Generate a buy signal if the 12-day moving average crosses above the 26-day moving average
    data['Buy_Signal'] = np.where(data['MA_12'] > data['MA_26'], 1, 0)
    # Reset buy signal after it's triggered
    data['Buy_Signal'][data['Buy_Signal'].shift() == 1] = 0

    # Generate a sell signal if the 12-day moving average crosses below the 26-day moving average
    data['Sell_Signal'] = np.where(data['MA_12'] < data['MA_26'], -1, 0)
    # Reset sell signal after it's triggered
    data['Sell_Signal'][data['Sell_Signal'].shift() == -1] = 0

    # Combine the buy and sell signals into a single signal column
    data['Signal'] = data['Buy_Signal'] - data['Sell_Signal']

    # Return the latest signal
    return data['Signal'][len(data) - 1]

# Define a function to generate a message based on the latest signal


def generate_signal_message(signal, current_price):
    if signal > 0:
        message = f'Buy signal for TSLA! Current price: ${current_price:.2f}'
    elif signal < 0:
        message = f'Sell signal for TSLA! Current price: ${current_price:.2f}'
    else:
        message = 'No signal for TSLA.'
    return message


# Download historical data and get the latest price
data = yf.download('TSLA', start='2022-01-01', end=None)
current_price = data['Close'][len(data) - 1]

# Create an instance of the EMA class with a period of 12
ema = EMA()
ema_short = ema.analyze(data.values, period_count=12)

# Create an instance of the EMA class with a period of 26
ema_long = ema.analyze(data.values, period_count=26)

# Merge the short-term and long-term EMA dataframes
ema_data = pd.merge(ema_short, ema_long, how='left',
                    left_index=True, right_index=True)

# Generate EMA signals
ema_data['Buy_Signal'] = np.where(ema_data['ema_x'] > ema_data['ema_y'], 1, 0)
ema_data['Sell_Signal'] = np.where(
    ema_data['ema_x'] < ema_data['ema_y'], -1, 0)
ema_data['Signal'] = ema_data['Buy_Signal'] - ema_data['Sell_Signal']

# Return the latest signal
signal = ema_data['Signal'][len(ema_data) - 1]

# Generate a message based on the latest signal
message = generate_signal_message(signal, current_price)

# Send message via WeChat API
send_message(message, current_price)

#
