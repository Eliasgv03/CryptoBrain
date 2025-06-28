import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def calculate_moving_average(price_history, window=7):
    """Calculates the moving average for a given price history."""
    prices = list(map(lambda entry: float(entry.price), price_history))
    if len(prices) < window:
        return 0.0
    result = np.convolve(prices, np.ones(window) / window, mode='valid').tolist()[-1]
    return result

def calculate_price_trend(price_history):
    """Calculates the price trend using linear regression and provides a qualitative description."""
    prices = list(map(lambda entry: float(entry.price), price_history))
    if len(prices) < 2:
        return {"slope": 0.0, "description": "Neutral"}

    x = np.arange(len(prices))
    slope, _ = np.polyfit(x, prices, 1)

    mean_price = np.mean(prices)
    normalized_slope = (slope / mean_price) * 100 if mean_price > 0 else 0

    if normalized_slope > 0.5:
        description = "Strongly Bullish"
    elif normalized_slope > 0.1:
        description = "Bullish"
    elif normalized_slope < -0.5:
        description = "Strongly Bearish"
    elif normalized_slope < -0.1:
        description = "Bearish"
    else:
        description = "Neutral"
    
    result = {"slope": slope, "description": description}
    return result

def prepare_chart_data(price_history):
    """Prepares data for Chart.js, formatting timestamps for readability."""
    if not price_history:
        return {'labels': [], 'prices': []}
    
    # Using map to apply a transformation function to each item in the lists
    labels = list(map(lambda entry: entry.timestamp.strftime('%b-%d %H:%M'), price_history))
    prices = list(map(lambda entry: float(entry.price), price_history))
    
    chart_data = {
        'labels': labels,
        'prices': prices
    }
    return chart_data

def preprocess_news_titles(news_titles):
    """Cleans and deduplicates a list of news titles."""
    processed = []
    seen = set()
    for title in news_titles:
        cleaned_title = title.strip()
        if cleaned_title and cleaned_title.lower() not in seen:
            processed.append(cleaned_title)
            seen.add(cleaned_title.lower())
    return processed