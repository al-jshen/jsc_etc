#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json
import time
import numpy as np
import os
import pprint


# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="TEAMKAWHI"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = False

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index=0
prod_exchange_hostname="production"

port=25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

# ~~~~~============== NETWORKING CODE ==============~~~~~
def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)

def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")

def read_from_exchange(exchange):
    return json.loads(exchange.readline())


prices = {}

def getprices(exchange):
    nxlf = 0
    while True:
        nl = read_from_exchange(exchange)
        if 'type' in nl.keys() and nl['type'] == 'book':
            if len(nl['buy']) > 0 and len(nl['sell']) > 0:
                prices[nl['symbol']] = (nl['buy'][0], nl['sell'][0], (nl['buy'][0][0] + nl['sell'][0][0]) / 2)
            if all(x in prices.keys() for x in ['BOND', 'GS', 'MS', 'WFC', 'VALBZ', 'VALE']):
                nxlf += xlfprice(exchange, nxlf)
                strat_pairs(exchange)
        pprint.pprint(prices)
        time.sleep(0.001)

def strat_pairs(exchange):
    valbz_b_price = prices['VALBZ'][0][0]
    valbz_b_vol = prices['VALBZ'][0][1]
    vale_s_price = prices['VALE'][1][0]
    vale_s_vol = prices['VALE'][1][1]
    vale_b_price = prices['VALE'][0][0]
    vale_b_vol = prices['VALE'][0][1]
    valbz_s_price = prices['VALBZ'][1][0]
    valbz_s_vol = prices['VALBZ'][1][1]
    if valbz_s_price + 10 < vale_b_price:
        write_to_exchange(exchange, trade('buy', 'valbz', valbz_s_price, min(valbz_s_vol, vale_b_vol)))
        write_to_exchange(exchange, convert('sell', 'valbz', min(valbz_s_vol, vale_b_vol)))
        write_to_exchange(exchange, trade('sell', 'vale', vale_b_price, min(valbz_s_vol, vale_b_vol)))
    if vale_s_price + 10 < valbz_b_price:
        write_to_exchange(exchange, trade('buy', 'vale', vale_s_price, min(vale_s_vol, valbz_b_vol)))
        write_to_exchange(exchange, convert('sell', 'vale', min(vale_s_vol, valbz_b_vol)))
        write_to_exchange(exchange, trade('sell', 'valbz', valbz_b_price, min(vale_s_vol, valbz_b_vol)))


def xlfprice(exchange, nxlf):
    xlf_fair = prices['BOND'][2] * 3 + prices['GS'][2] * 2 + prices['MS'][2] * 3 + prices['WFC'][2] * 2
    prices['XLF2'] = xlf_fair / 10
    # if sum of underlying is greater than the etf then buy the etf
    if prices['XLF'][1][0] < prices['XLF2']:
        write_to_exchange(exchange, trade('buy', 'XLF', prices['XLF'][1][0], prices['XLF'][1][1]))
        print(read_from_exchange(exchange))
        print("BOUGHT #################################")
        nxlf += 1
        if nxlf != 0 and nxlf % 10 == 0:
            write_to_exchange(exchange, convert('sell', 'xlf', 10))
            write_to_exchange(exchange, trade('sell', 'bond', prices['BOND'][2], 3))
            write_to_exchange(exchange, trade('sell', 'gs', prices['GS'][2], 2))
            write_to_exchange(exchange, trade('sell', 'ms', prices['MS'][2], 3))
            write_to_exchange(exchange, trade('sell', 'wfc', prices['WFC'][2], 2))

    elif prices['XLF'][0][0] > prices['XLF2']:
        write_to_exchange(exchange, trade('sell', 'XLF', prices['XLF'][0][0], prices['XLF'][0][1]))
        print(read_from_exchange(exchange))
        print("SOLD ##################################")
        nxlf -= 1
        if nxlf != 0 and nxlf % 10 == 0:
            write_to_exchange(exchange, trade('buy', 'bond', prices['BOND'][2], 3))
            write_to_exchange(exchange, trade('buy', 'gs', prices['GS'][2], 2))
            write_to_exchange(exchange, trade('buy', 'ms', prices['MS'][2], 3))
            write_to_exchange(exchange, trade('buy', 'wfc', prices['WFC'][2], 2))
            write_to_exchange(exchange, convert('buy', 'xlf', 10))

    return nxlf

# ~~~~~============== MAIN LOOP ==============~~~~~

def main():
    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)
    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)

    getprices(exchange)

if __name__ == "__main__":
    main()
