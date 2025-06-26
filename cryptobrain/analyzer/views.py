import json
from django.shortcuts import render
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

from .fetchers import fetch_bitcoin_price, fetch_bitcoin_historical_price, fetch_bitcoin_news
from .models import BitcoinPriceHistory, BitcoinNews
import asyncio
from asgiref.sync import sync_to_async
from datetime import timedelta, datetime

# --- Database Interaction Functions (Async-safe) ---

@sync_to_async
def save_price_history_bulk(price_data_list):
    """Saves a list of price data points in a single bulk operation."""
    logger.info(f"Saving {len(price_data_list)} price history records in bulk.")
    timestamps = [p['timestamp'] for p in price_data_list]
    existing_timestamps = set(
        BitcoinPriceHistory.objects.filter(timestamp__in=timestamps).values_list('timestamp', flat=True)
    )
    
    new_prices = [
        BitcoinPriceHistory(**p) for p in price_data_list if p['timestamp'] not in existing_timestamps
    ]
    
    if new_prices:
        logger.info(f"Bulk creating {len(new_prices)} new price history records.")
        BitcoinPriceHistory.objects.bulk_create(new_prices)

@sync_to_async
def save_single_price_history(price_data):
    """Saves a single price data point."""
    logger.info(f"Updating or creating single price history for timestamp {price_data['timestamp']}.")
    BitcoinPriceHistory.objects.update_or_create(
        timestamp=price_data['timestamp'],
        defaults={'price': price_data['price'], 'volume_24h': price_data['volume_24h']}
    )

@sync_to_async
def save_news_items(news_items):
    """Saves a list of news items, ignoring duplicates based on the unique URL field."""
    news_to_create = [
        BitcoinNews(
            url=item['url'],
            title=item['title'],
            published_at=item['published_at'],
            source=item['source']
        )
        for item in news_items
    ]
    if news_to_create:
        logger.info(f"Bulk creating {len(news_to_create)} new news items.")
        BitcoinNews.objects.bulk_create(news_to_create, ignore_conflicts=True)

@sync_to_async
def get_price_history_from_db():
    seven_days_ago = timezone.now() - timedelta(days=7)
    logger.info(f"Fetching price history from DB for the last 7 days.")
    return list(BitcoinPriceHistory.objects.filter(timestamp__gte=seven_days_ago).order_by('timestamp'))

@sync_to_async
def get_latest_news_from_db():
    logger.info("Fetching latest news from DB.")
    return list(BitcoinNews.objects.all().order_by('-published_at')[:5])

@sync_to_async
def purge_old_price_data():
    seven_days_ago = timezone.now() - timedelta(days=7)
    logger.info(f"Purging price data older than {seven_days_ago}.")
    deleted_count, _ = BitcoinPriceHistory.objects.filter(timestamp__lt=seven_days_ago).delete()
    logger.info(f"Deleted {deleted_count} old price records.")

@sync_to_async
def get_latest_price_from_db():
    """Fetches the most recent price data point from the database."""
    logger.info("Fetching latest price from DB.")
    return BitcoinPriceHistory.objects.order_by('-timestamp').first()

# --- Data Processing & Mapping ---

def map_price_data(price_data, timestamp):
    dt = datetime.fromtimestamp(timestamp / 1000) if timestamp else timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return {'timestamp': dt, 'price': price_data.get('price', 0), 'volume_24h': price_data.get('volume_24h')}

# --- Main Views ---

from .processor import calculate_moving_average, calculate_price_trend, prepare_chart_data
from .agent import agent_coordinator, APIQuotaExceededError

async def dashboard(request):
    logger.info("--- Dashboard view requested ---")
    return render(request, 'dashboard.html', {'crypto': 'BTC'})

# --- HTMX Partial Views ---

async def market_data(request):
    logger.info("--- Market data partial view requested ---")
    cache_key = 'market_data'
    context = cache.get(cache_key)
    
    if not context:
        logger.info("Market data not in cache, fetching fresh data.")
        try:
            price_data = await fetch_bitcoin_price()
            if price_data:
                logger.info(f"Fetched price data: {price_data}")
                await save_single_price_history(map_price_data(price_data, None))
            else:
                logger.warning("Failed to fetch price data.")
            
            context = {
                'price_data': price_data,
                'last_updated': timezone.now().strftime('%H:%M:%S')
            }
            cache.set(cache_key, context, timeout=60)
            logger.info("Market data cached.")
        except Exception as e:
            logger.error(f"Error in market_data view: {e}", exc_info=True)
            context = {'error': 'Could not fetch market data.'}
    else:
        logger.info("Serving market data from cache.")
        
    return render(request, 'partials/market_data.html', context)

async def latest_news(request):
    logger.info("--- Latest news partial view requested ---")
    cache_key = 'latest_news'
    stored_news = cache.get(cache_key)

    if not stored_news:
        logger.info("News not in cache, fetching fresh data.")
        try:
            news_from_api = await fetch_bitcoin_news()
            if news_from_api:
                logger.info(f"Fetched {len(news_from_api)} news items from API.")
                await save_news_items(news_from_api)
            else:
                logger.warning("Failed to fetch news from API.")
            
            stored_news = await get_latest_news_from_db()
            logger.info(f"Fetched {len(stored_news)} news items from DB.")
            cache.set(cache_key, stored_news, timeout=300)
            logger.info("News data cached.")
        except Exception as e:
            logger.error(f"Error in latest_news view: {e}", exc_info=True)
            stored_news = [] # Ensure stored_news is a list
            context = {'error': 'Could not fetch news.'}
            return render(request, 'partials/latest_news.html', context)
    else:
        logger.info("Serving news from cache.")

    return render(request, 'partials/latest_news.html', {'news': stored_news})

async def analysis(request):
    logger.info("--- Analysis partial view requested ---")
    cache_key = 'analysis_data'
    context = cache.get(cache_key)

    if context:
        logger.info("Analysis data found in cache. Rendering from cache.")
        return render(request, 'partials/analysis.html', context)

    logger.info("No cache found. Starting fresh data gathering for analysis.")
    try:
        logger.info("Fetching latest price, history, and news from DB...")
        latest_price_data, price_history_db, news_items = await asyncio.gather(
            get_latest_price_from_db(),
            get_price_history_from_db(),
            get_latest_news_from_db()
        )
        logger.info(f"DB Fetch Results: LatestPrice={latest_price_data is not None}, HistoryCount={len(price_history_db)}, NewsCount={len(news_items)}")

        if not all([latest_price_data, price_history_db, news_items]):
            logger.warning("Not enough data for analysis. Waiting for data to be fetched.")
            return render(request, 'partials/analysis.html', {'error': 'Not enough data for analysis. Please refresh in a moment.'})

        latest_price = latest_price_data.price
        volume_24h = latest_price_data.volume_24h
        news_headlines = [news.title for news in news_items]
        logger.info("Data successfully gathered.")

        logger.info("Calculating technical indicators...")
        price_trend, moving_average = await asyncio.gather(
            sync_to_async(calculate_price_trend)(price_history_db),
            sync_to_async(calculate_moving_average)(price_history_db)
        )
        logger.info(f"Calculated Indicators: Trend={price_trend}, MA={moving_average}")

    except Exception as e:
        logger.error(f"Error gathering data for analysis: {e}", exc_info=True)
        return render(request, 'partials/analysis.html', {'error': 'Could not retrieve market data for analysis.'})

    try:
        logger.info("Requesting comprehensive analysis from AI agent...")
        analysis_result = await agent_coordinator.get_comprehensive_analysis(
            current_price=latest_price,
            volume_24h=volume_24h,
            price_trend=price_trend,
            moving_average=moving_average,
            news_titles=news_headlines
        )
        logger.info(f"AI analysis raw result: {analysis_result}")

        if not analysis_result:
            logger.error("AI analysis returned an empty or invalid result.")
            context = {'error': 'AI analysis returned no data.'}
        else:
            context = {
                'sentiment_prediction': {
                    'sentiment': analysis_result.get('market_sentiment'),
                    'confidence_percentage': round(analysis_result.get('confidence_score', 0.0) * 100)
                },
                'trend_prediction': {
                    'prediction': analysis_result.get('trend_prediction'),
                    'confidence_percentage': round(analysis_result.get('confidence_score', 0.0) * 100),
                    'reasoning': analysis_result.get('detailed_reasoning')
                },
                'analysis_summary': analysis_result.get('analysis_summary'),
                'last_updated': timezone.now().strftime('%H:%M:%S')
            }
            cache.set(cache_key, context, timeout=900)
            logger.info(f"AI analysis context cached: {context}")

    except APIQuotaExceededError as e:
        logger.warning(f"API Quota Exceeded. Serving fallback data. Error: {e}")
        context = {'error': str(e)}

    except Exception as e:
        logger.error(f"An unexpected error occurred in AI analysis: {e}", exc_info=True)
        context = {'error': 'AI analysis is temporarily unavailable.'}

    logger.debug(f"Final context for analysis partial: {context}")
    return render(request, 'partials/analysis.html', context)

async def price_chart(request):
    logger.info("--- Price chart partial view requested ---")
    cache_key = 'price_chart_data'
    chart_data = cache.get(cache_key)

    if not chart_data:
        logger.info("Price chart data not in cache, fetching fresh data.")
        try:
            historical_data = await fetch_bitcoin_historical_price(days=7)
            if historical_data:
                logger.info(f"Fetched {len(historical_data)} historical data points.")
                price_list = [map_price_data({'price': p[1], 'volume_24h': p[2]}, p[0]) for p in historical_data]
                await save_price_history_bulk(price_list)
            else:
                logger.warning("Failed to fetch historical data for chart.")
            
            price_history = await get_price_history_from_db()
            logger.info(f"Fetched {len(price_history)} price history points from DB for chart.")
            chart_data = prepare_chart_data(price_history)
            cache.set(cache_key, chart_data, timeout=900)
            logger.info("Price chart data cached.")
        except Exception as e:
            logger.error(f"Error in price_chart view: {e}", exc_info=True)
            chart_data = {'labels': [], 'prices': []}
            context = {'error': 'Could not fetch chart data.'}
            return render(request, 'partials/price_chart.html', context)
    else:
        logger.info("Serving price chart data from cache.")

    chart_data_json = json.dumps(chart_data)
    return render(request, 'partials/price_chart.html', {'chart_data': chart_data_json})