import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def calculate_moving_average(price_history, window=7):
    """Calculates the moving average for a given price history."""
    logger.info(f"Calculating moving average for {len(price_history)} data points with window {window}.")
    prices = [float(entry.price) for entry in price_history]
    if len(prices) < window:
        logger.warning(f"Not enough data points ({len(prices)}) to calculate moving average for window size {window}. Returning 0.0")
        return 0.0
    result = np.convolve(prices, np.ones(window) / window, mode='valid').tolist()[-1]
    logger.info(f"Moving average result: {result}")
    return result

def calculate_price_trend(price_history):
    """Calculates the price trend using linear regression and provides a qualitative description."""
    logger.info(f"Calculating price trend for {len(price_history)} data points.")
    prices = [float(entry.price) for entry in price_history]
    if len(prices) < 2:
        logger.warning(f"Not enough data points ({len(prices)}) to calculate trend. Returning Neutral.")
        return {"slope": 0.0, "description": "Neutral"}

    x = np.arange(len(prices))
    slope, _ = np.polyfit(x, prices, 1)

    mean_price = np.mean(prices)
    normalized_slope = (slope / mean_price) * 100 if mean_price > 0 else 0
    logger.info(f"Calculated slope: {slope}, normalized slope: {normalized_slope:.4f}%")

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
    logger.info(f"Price trend result: {result}")
    return result

def prepare_chart_data(price_history):
    """Prepares data for Chart.js, formatting timestamps for readability."""
    logger.info(f"Preparing chart data for {len(price_history)} data points.")
    if not price_history:
        logger.warning("No price history to prepare for chart. Returning empty data.")
        return {'labels': [], 'prices': []}
        
    labels = [entry.timestamp.strftime('%b-%d %H:%M') for entry in price_history]
    prices = [float(entry.price) for entry in price_history]
    
    chart_data = {
        'labels': labels,
        'prices': prices
    }
    logger.info(f"Prepared chart data with {len(labels)} labels.")
    return chart_data

def preprocess_news_titles(news_titles):
    """Cleans and deduplicates a list of news titles."""
    logger.info(f"Preprocessing {len(news_titles)} news titles.")
    processed = []
    seen = set()
    for title in news_titles:
        cleaned_title = title.strip()
        if cleaned_title and cleaned_title.lower() not in seen:
            processed.append(cleaned_title)
            seen.add(cleaned_title.lower())
    logger.info(f"Returning {len(processed)} unique news titles after preprocessing.")
    return processed