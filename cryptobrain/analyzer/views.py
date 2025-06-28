import json
from django.shortcuts import render
from django.utils import timezone
from django.core.cache import cache
from .fetchers import fetch_bitcoin_price, fetch_bitcoin_historical_price, fetch_bitcoin_news
from .models import BitcoinPriceHistory, BitcoinNews
import asyncio
from asgiref.sync import sync_to_async
from datetime import timedelta, datetime
from .processor import calculate_moving_average, calculate_price_trend
from .agent import agent_orchestrator, APIQuotaExceededError


@sync_to_async
def save_price_history_bulk(price_data_list):
    """
    Saves a list of historical price data points in a single bulk operation,
    avoiding duplicates by checking existing timestamps.

    Args:
        price_data_list (list[dict]): A list of price data dictionaries.
    """
    timestamps = [p['timestamp'] for p in price_data_list]
    existing_timestamps = set(
        BitcoinPriceHistory.objects.filter(timestamp__in=timestamps).values_list('timestamp', flat=True)
    )
    new_prices = [
        BitcoinPriceHistory(**p) for p in price_data_list if p['timestamp'] not in existing_timestamps
    ]
    if new_prices:
        BitcoinPriceHistory.objects.bulk_create(new_prices)

@sync_to_async
def save_single_price_history(price_data):
    """
    Saves a single, most recent price data point.

    Args:
        price_data (dict): The price data to save.
    """
    BitcoinPriceHistory.objects.update_or_create(
        timestamp=price_data['timestamp'],
        defaults={'price': price_data['price'], 'volume_24h': price_data['volume_24h']}
    )

@sync_to_async
def save_news_items(news_items):
    """
    Saves a list of news items, ignoring duplicates based on the unique URL field.

    Args:
        news_items (list[dict]): A list of news item dictionaries.
    """
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
        BitcoinPriceHistory.objects.bulk_create(news_to_create, ignore_conflicts=True)

@sync_to_async
def get_price_history_from_db():
    """Fetches price history from the last 7 days from the database."""
    seven_days_ago = timezone.now() - timedelta(days=7)
    return list(BitcoinPriceHistory.objects.filter(timestamp__gte=seven_days_ago).order_by('timestamp'))

@sync_to_async
def get_latest_news_from_db(limit=10):
    """Fetches the most recent news items from the database."""
    return list(BitcoinNews.objects.all().order_by('-published_at')[:limit])

@sync_to_async
def purge_old_price_data():
    """Removes price data older than 7 days to keep the database clean."""
    seven_days_ago = timezone.now() - timedelta(days=7)
    BitcoinPriceHistory.objects.filter(timestamp__lt=seven_days_ago).delete()

@sync_to_async
def get_latest_price_from_db():
    """Fetches the most recent price data point from the database."""
    return BitcoinPriceHistory.objects.order_by('-timestamp').first()


def map_price_data(price_data, timestamp):
    """Maps raw price data to a structured dictionary with a timezone-aware datetime."""
    dt = datetime.fromtimestamp(timestamp / 1000) if timestamp else timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return {'timestamp': dt, 'price': price_data.get('price', 0), 'volume_24h': price_data.get('volume_24h')}


async def dashboard(request):
    """Renders the main dashboard page."""
    return render(request, 'dashboard.html', {'crypto': 'BTC'})


async def market_data(request):
    """
    Renders the market data partial view, serving from cache if available
    or fetching fresh data from the CoinGecko API.
    """
    cache_key = 'market_data'
    context = cache.get(cache_key)
    if context:
        return render(request, 'partials/market_data.html', context)

    try:
        price_data = await fetch_bitcoin_price()
        if not price_data:
            return render(request, 'partials/market_data.html', {'error': 'Could not fetch market data.'})

        context = {
            'price_data': price_data,
            'last_updated': timezone.now().strftime('%H:%M:%S')
        }
        cache.set(cache_key, context, timeout=60)  # Cache for 1 minute
        return render(request, 'partials/market_data.html', context)
    except Exception:
        return render(request, 'partials/market_data.html', {'error': 'An unexpected error occurred.'})

async def latest_news(request):
    """
    Renders the latest news partial view, serving from cache or fetching from the DB.
    """
    cache_key = 'latest_news'
    context = cache.get(cache_key)
    if context:
        return render(request, 'partials/latest_news.html', context)

    try:
        news_items = await get_latest_news_from_db(limit=20)
        if not news_items:
            return render(request, 'partials/latest_news.html', {'news': []})

        context = {
            'news': news_items,
            'last_updated': timezone.now().strftime('%H:%M:%S')
        }
        cache.set(cache_key, context, timeout=900)  # Cache for 15 minutes
        return render(request, 'partials/latest_news.html', context)
    except Exception:
        return render(request, 'partials/latest_news.html', {'error': 'Could not load news.'})

async def analysis(request):
    """
    Renders the AI analysis partial view. It gathers data from the database,
    calculates technical indicators, and invokes the AI agent to get a
    comprehensive market analysis.
    """
    cache_key = 'analysis_data'
    context = cache.get(cache_key)
    if context:
        return render(request, 'partials/analysis.html', context)

    try:
        latest_price_data, price_history_db, news_items = await asyncio.gather(
            get_latest_price_from_db(),
            get_price_history_from_db(),
            get_latest_news_from_db()
        )

        if not all([latest_price_data, price_history_db, news_items]):
            return render(request, 'partials/analysis.html', {'error': 'Not enough data for analysis. Please refresh in a moment.'})

        price_trend, moving_average = await asyncio.gather(
            sync_to_async(calculate_price_trend)(price_history_db),
            sync_to_async(calculate_moving_average)(price_history_db)
        )
    except Exception:
        return render(request, 'partials/analysis.html', {'error': 'Could not retrieve market data for analysis.'})

    try:
        analysis_result = await agent_orchestrator.get_comprehensive_analysis(
            current_price=latest_price_data.price,
            volume_24h=latest_price_data.volume_24h or 0,
            price_trend=price_trend,
            moving_average=moving_average,
            news_titles=[news.title for news in news_items]
        )

        if not analysis_result:
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

    except APIQuotaExceededError as e:
        context = {'error': str(e)}
    except Exception:
        context = {'error': 'AI analysis is temporarily unavailable.'}

    return render(request, 'partials/analysis.html', context)

async def price_chart(request):
    """
    Renders the price chart partial view, fetching historical data and
    formatting it for Chart.js.
    """
    try:
        prices = await get_price_history_from_db()
        if not prices:
            return render(request, 'partials/price_chart.html', {'error': 'No price data available.'})

        chart_data = {
            'labels': [p.timestamp.strftime('%b %d') for p in prices],
            'prices': [float(p.price) for p in prices]
        }

        context = {'chart_data': json.dumps(chart_data)}
        return render(request, 'partials/price_chart.html', context)
    except Exception:
        return render(request, 'partials/price_chart.html', {'error': 'Could not load chart data.'})