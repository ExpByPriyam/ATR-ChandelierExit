import ccxt.pro
import asyncio
import pandas as pd
import numpy as np


class TradingBot:
    def __init__(self, symbol, timeframe='5m', periods=22, multiplier=3):
        self.symbol = symbol
        self.timeframe = timeframe
        self.periods = periods
        self.multiplier = multiplier
        self.exchange = ccxt.pro.bybit({
            'apiKey': '7jxxxErLE6f2tk1VTr',  # Replace with your API key
            'secret': 'l7uKVAR9rViizSe38t9Lt7f6peied7HWYIUq',  # Replace with your API secret
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        self.df = pd.DataFrame()

    def calculate_atr(self, data):
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(window=self.periods).mean()
        return atr

    def chandelier_exit(self, data):
        atr = self.calculate_atr(data)
        data['ATR'] = atr
        data['Highest High'] = data['high'].rolling(window=self.periods).max()
        data['Chandelier Exit'] = data['Highest High'] - \
            self.multiplier * data['ATR']
        return data

    async def fetch_candles(self):
        while True:
            try:
                candle = await self.exchange.watch_ohlcv(self.symbol, self.timeframe)
                if not candle:
                    print("Received empty data")
                    continue

                # Unwrap the nested list
                candle = candle[0] if candle and len(candle[0]) == 6 else None
                if candle:
                    # Log the received candle for debugging
                    print(f"Received candle: {candle}")
                    latest_candle = {
                        'timestamp': candle[0],
                        'open': candle[1],
                        'high': candle[2],
                        'low': candle[3],
                        'close': candle[4],
                        'volume': candle[5]
                    }
                    self.df = self.df.append(latest_candle, ignore_index=True)

                    if len(self.df) >= self.periods:
                        self.df = self.chandelier_exit(self.df)
                        self.df.dropna(inplace=True)
                        self.print_signals()
                else:
                    print(f"Incomplete data received: {candle}")

            except Exception as e:
                print(f"Error processing data: {e}")

            # Sleep based on exchange's rate limit
            await asyncio.sleep(self.exchange.rateLimit / 1000)

    def print_signals(self):
        last_row = self.df.iloc[-1]
        signal = 'Hold'
        if last_row['close'] > last_row['Chandelier Exit']:
            signal = 'Buy'
        elif last_row['close'] < last_row['Chandelier Exit']:
            signal = 'Sell'

        print(
            f"Time: {pd.to_datetime(last_row['timestamp'], unit='ms')}, Close: {last_row['close']}, Chandelier Exit: {last_row['Chandelier Exit']}, Signal: {signal}")

    async def run(self):
        await self.fetch_candles()
        await self.exchange.close()  # Ensure to close the connection properly


if __name__ == "__main__":
    symbol = 'ETH/USDT'
    bot = TradingBot(symbol)
    asyncio.run(bot.run())
