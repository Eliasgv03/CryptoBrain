from functools import reduce
from statistics import mean
from .models import BitcoinPriceHistory
import numpy as np

def calculate_moving_average(price_history, window=7):
    prices = [p.price for p in price_history]
    if len(prices) < window:
        return mean(prices) if prices else 0
    return np.convolve(prices, np.ones(window)/window, mode='valid').tolist()[-1]

def calculate_price_trend(price_history):
    if len(price_history) < 2:
        return {'trend': 'neutral', 'confidence': 0.5}
    prices = [p.price for p in price_history]
    trend = 'bullish' if prices[-1] > prices[0] else 'bearish' if prices[-1] < prices[0] else 'neutral'
    confidence = min(abs(prices[-1] - prices[0]) / prices[0], 1.0) if prices[0] != 0 else 0.5
    return {'trend': trend, 'confidence': round(confidence, 2)}

def prepare_chart_data(price_history):
    return [[p.timestamp.timestamp() * 1000, float(p.price)] for p in price_history]

def preprocess_news_titles(news_titles):
    return [title.strip() for title in news_titles if title and isinstance(title, str)]