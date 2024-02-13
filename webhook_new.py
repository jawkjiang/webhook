from flask import Flask, request
from pybit.unified_trading import HTTP
import os
import pickle
import logging


# initialize
# save log to file
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

filehandler = logging.FileHandler('log.log', encoding='utf-8')
filehandler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
filehandler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(filehandler)

# open .env file if exists
try:
    with open('.env', 'r') as f:
        for line in f:
            key, value = line.strip().split('=')
            os.environ[key] = value
except FileNotFoundError:
    logging.error('没有找到.env环境变量。')

# get environment variables
api_key1 = os.environ.get('API_KEY1')
api_secret1 = os.environ.get('API_SECRET1')
api_key2 = os.environ.get('API_KEY2')
api_secret2 = os.environ.get('API_SECRET2')
testnet = True if os.environ.get('TESTNET') == 'y' else False


session1 = HTTP(testnet=testnet, api_key=api_key1, api_secret=api_secret1)
session2 = HTTP(testnet=testnet, api_key=api_key2, api_secret=api_secret2)

'''
balance1_init = float(session1.get_wallet_balance(accountType="UNIFIED", coin="USDT")['result']['list']['coin'][0]
                      ['walletBalance'])
balance2_init = float(session2.get_wallet_balance(accountType="UNIFIED", coin="USDT")['result']['list']['coin'][0]
                      ['walletBalance'])
'''

balance1_init = 1000
balance2_init = 1000

loss_balance1 = balance1_init * 0.8
loss_balance2 = balance2_init * 0.8

coin1 = ['TIAUSDT', 'ORDIUSDT', 'AUCTIONUSDT']
coin2 = ['BTCUSDT']
coin1_index = 0
coin2_index = 0
# save template pickle file
with open('temp.pkl', 'wb') as f:
    pickle.dump(loss_balance1, f)
    pickle.dump(loss_balance2, f)
    pickle.dump(coin1_index, f)
    pickle.dump(coin2_index, f)
logging.info("初始化完成。")

app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # load temp from pickle file
    with open('temp.pkl', 'rb') as f:
        loss_balance1 = pickle.load(f)
        loss_balance2 = pickle.load(f)
        coin1_index = pickle.load(f)
        coin2_index = pickle.load(f)
    try:
        if data['symbol'] == coin1[coin1_index] or data['symbol'][:-2] == coin1[coin1_index]:
            if data['action'] == 'buy':
                session1.place_order(catagory="linear", symbol=coin1[coin1_index], side="Buy", orderType="MARKET", qty=0, reduceOnly='true')

            elif data['action'] == 'sell':
                session1.place_order(catagory="linear", symbol=coin1[coin1_index], side="Sell", orderType="MARKET", qty=0, reduceOnly='true')

            balance1 = float(session1.get_wallet_balance(accountType="UNIFIED", coin="USDT")['result']['list']['coin'][0]['walletBalance']) - 1
            logging.info(f"已平仓{coin1[coin1_index]}，当前账户余额为{balance1}")

            if balance1 < loss_balance1:
                logging.info(f"账户1余额低于止损线，已强平，当前账户余额为{balance1}")
                coin1_index += 1
                loss_balance1 = balance1 * 0.8

            current_price = float(session1.get_tickers(catagory='linear', symbol=coin1[coin1_index])['result']['list'][0]['lastPrice'])

            if data['action'] == 'buy':
                loss_price = loss_balance1 / balance1 * current_price
                session1.place_order(catagory="linear", symbol=coin1[coin1_index], side="Buy", orderType="MARKET", qty=float(balance1/current_price), stopLoss=loss_price)
                logging.info(f"已开多头{coin1[coin1_index]}，当前账户余额为{balance1}")

            elif data['action'] == 'sell':
                loss_price = balance1 / loss_balance1 * current_price
                session1.place_order(catagory="linear", symbol=coin1[coin1_index], side="Sell", orderType="MARKET", qty=float(balance1/current_price), stopLoss=loss_price)
                logging.info(f"已开空头{coin1[coin1_index]}，当前账户余额为{balance1}")

    except Exception as e:
        logging.error(e)
        logging.error("交易失败。")

    try:
        if data['symbol'] == coin2[coin2_index] or data['symbol'][:-2] == coin2[coin2_index]:
            if data['action'] == 'buy':
                session2.place_order(catagory="linear", symbol=coin2[coin2_index], side="Buy", orderType="MARKET", qty=0, reduceOnly='true')

            elif data['action'] == 'sell':
                session2.place_order(catagory="linear", symbol=coin2[coin2_index], side="Sell", orderType="MARKET", qty=0, reduceOnly='true')

            balance2 = float(session2.get_wallet_balance(accountType="UNIFIED", coin="USDT")['result']['list']['coin'][0]['walletBalance']) - 1
            logging.info(f"已平仓{coin2[coin2_index]}，当前账户余额为{balance2}")

            if balance2 < loss_balance2:
                logging.info(f"账户2余额低于止损线，已强平，当前账户余额为{balance2}")
                coin2_index += 1
                loss_balance2 = balance2 * 0.8

            current_price = float(session2.get_tickers(catagory='linear', symbol=coin2[coin2_index])['result']['list'][0]['lastPrice'])

            if data['action'] == 'buy':
                loss_price = loss_balance2 / balance2 * current_price
                session2.place_order(catagory="linear", symbol=coin2[coin2_index], side="Buy", orderType="MARKET", qty=float(balance2/current_price), stopLoss=loss_price)
                logging.info(f"已开多头{coin2[coin2_index]}，当前账户余额为{balance2}")

            elif data['action'] == 'sell':
                loss_price = balance2 / loss_balance2 * current_price
                session2.place_order(catagory="linear", symbol=coin2[coin2_index], side="Sell", orderType="MARKET", qty=float(balance2/current_price), stopLoss=loss_price)
                logging.info(f"已开空头{coin2[coin2_index]}，当前账户余额为{balance2}")

    except Exception as e:
        logging.error(e)
        logging.error("交易失败。")

    # save temp to pickle file
    with open('temp.pkl', 'wb') as f:
        pickle.dump(loss_balance1, f)
        pickle.dump(loss_balance2, f)
        pickle.dump(coin1_index, f)
        pickle.dump(coin2_index, f)

    return 'success'


@app.route('/test', methods=['POST'])
def test_link():
    return 'success'


if __name__ == '__main__':
    app.run(port=80)
