import requests
import time
import json
import numpy as np


def get_ticker(symbol):
    url = f"https://www.mexc.com/open/api/v2/market/ticker?symbol={symbol}"
    response = requests.get(url)
    data = response.json()
    if data['code'] == 200:
        ticker_info = data['data'][0]
        ohlcv = {
            "open": float(ticker_info['open']),
            "high": float(ticker_info['high']),
            "low": float(ticker_info['low']),
            "close": float(ticker_info['last']),
            "volume": float(ticker_info['volume'])
        }
        return ohlcv
    else:
        print(f"Failed to fetch data: {data['code']}")
        return None


def calculate_atr(candles):
    tr_list = []
    for i in range(1, len(candles)):
        try:
            high_low = candles[i]["ha_high"] - candles[i]["ha_low"]
            high_close = abs(candles[i]["ha_high"] - candles[i-1]["ha_close"])
            low_close = abs(candles[i]["ha_low"] - candles[i-1]["ha_close"])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        except KeyError as e:
            print(f"KeyError for candle index {i}: Missing key {e}")
            print(f"Current candle data: {candles[i]}")
            continue  # Skip this iteration and continue with the next
    return np.mean(tr_list) if tr_list else 0  # Return 0 if tr_list is empty


def heiken_ashi(previous_candle, current_candle):
    if previous_candle is None:
        ha_close = (current_candle['open'] + current_candle['high'] +
                    current_candle['low'] + current_candle['close']) / 4
        ha_open = (current_candle['open'] + current_candle['close']) / 2
        ha_high = current_candle['high']
        ha_low = current_candle['low']
    else:
        ha_close = (current_candle['open'] + current_candle['high'] +
                    current_candle['low'] + current_candle['close']) / 4
        ha_open = (previous_candle['ha_open'] +
                   previous_candle['ha_close']) / 2
        ha_high = max(current_candle['high'], ha_open, ha_close)
        ha_low = min(current_candle['low'], ha_open, ha_close)
    return {
        "ha_open": ha_open, "ha_high": ha_high, "ha_low": ha_low, "ha_close": ha_close
    }


def main():
    previous_candle = None
    candles = []
    last_signal = None
    chandelier_multiplier = 0.8  # Updated multiplier
    atr_length = 2  # Updated length for ATR and highest high calculation

    try:
        while True:
            current_candle = get_ticker("ETH_USDT")
            if current_candle:
                ha_candle = heiken_ashi(previous_candle, current_candle)
                previous_candle = ha_candle
                candles.append(ha_candle)
                if len(candles) > atr_length:
                    # Use last 'atr_length' candles for ATR
                    atr = calculate_atr(candles[-(atr_length+1):])
                    # Use last 'atr_length' candles for highest high
                    highest_high = max(candle['ha_high']
                                       for candle in candles[-atr_length:])
                    chandelier_exit = highest_high - \
                        chandelier_multiplier * atr  # Use updated multiplier

                    if ha_candle['ha_close'] > chandelier_exit and (last_signal != "BUY"):
                        print("BUY signal generated.")
                        last_signal = "BUY"
                    elif ha_candle['ha_close'] < chandelier_exit and (last_signal != "SELL"):
                        print("SELL signal generated.")
                        last_signal = "SELL"

                    # print(f"Chandelier Exit: {chandelier_exit}")
                # print(json.dumps(ha_candle, indent=4))
            time.sleep(1)  # Sleep for one second
    except KeyboardInterrupt:
        print("Stopped by user.")


if __name__ == "__main__":
    main()
