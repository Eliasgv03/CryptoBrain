from django.shortcuts import render
from django.utils import timezone
from .fetchers import fetch_bitcoin_price, fetch_bitcoin_historical_price, fetch_bitcoin_news
from .models import BitcoinPriceHistory, BitcoinNews, AnalysisCache
import asyncio
from asgiref.sync import sync_to_async
from datetime import timedelta

# --- Database Interaction Functions ---

@sync_to_async
def save_price_history(price_data):
    BitcoinPriceHistory.objects.update_or_create(
        timestamp=price_data['timestamp'],
        defaults={'price': price_data['price'], 'volume_24h': price_data['volume_24h']}
    )

@sync_to_async
def save_news_items(news_items):
    existing_urls = set(BitcoinNews.objects.values_list('url', flat=True))
    new_news = [item for item in news_items if item['url'] not in existing_urls]
    
    news_to_create = []
    for item in new_news:
        published_at = timezone.make_aware(
            timezone.datetime.strptime(item['published_at'], '%Y-%m-%dT%H:%M:%SZ'),
            timezone.get_current_timezone()
        )
        news_to_create.append(
            BitcoinNews(
                url=item['url'],
                title=item['title'],
                source=item.get('source', 'Unknown'),
                published_at=published_at
            )
        )
    if news_to_create:
        BitcoinNews.objects.bulk_create(news_to_create)

@sync_to_async
def get_price_history_from_db():
    seven_days_ago = timezone.now() - timedelta(days=7)
    return list(BitcoinPriceHistory.objects.filter(timestamp__gte=seven_days_ago).order_by('timestamp'))

@sync_to_async
def get_latest_news_from_db():
    return list(BitcoinNews.objects.all().order_by('-published_at')[:5])

@sync_to_async
def get_latest_analysis_cache():
    cache = AnalysisCache.objects.first()
    if cache and (timezone.now() - cache.created_at < timedelta(minutes=15)):
        return cache
    return None

@sync_to_async
def save_analysis_to_cache(sentiment, trend):
    return AnalysisCache.objects.create(sentiment_response=sentiment, trend_response=trend)

@sync_to_async
def purge_old_price_data():
    seven_days_ago = timezone.now() - timedelta(days=7)
    BitcoinPriceHistory.objects.filter(timestamp__lt=seven_days_ago).delete()

# --- Data Processing & Mapping ---

def map_price_data(price_data, timestamp):
    dt = timezone.datetime.fromtimestamp(timestamp / 1000) if timestamp else timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return {'timestamp': dt, 'price': price_data.get('price', 0), 'volume_24h': price_data.get('volume_24h')}

# --- Main Views ---

from .processor import calculate_moving_average, calculate_price_trend, prepare_chart_data
from .agent import agent_coordinator, APIQuotaExceededError

async def dashboard(request):
    await purge_old_price_data() # Clean up old data on dashboard load
    return render(request, 'dashboard.html', {'crypto': 'BTC'})

# --- HTMX Partial Views ---

async def market_data(request):
    price_data = await fetch_bitcoin_price()
    if price_data:
        await save_price_history(map_price_data(price_data, None))
    context = {
        'price_data': price_data,
        'last_updated': timezone.now().strftime('%H:%M:%S')
    }
    return render(request, 'partials/market_data.html', context)

async def latest_news(request):
    latest_from_db = await get_latest_news_from_db()
    if not latest_from_db or (timezone.now() - latest_from_db[0].created_at > timedelta(minutes=15)):
        news_from_api = await fetch_bitcoin_news()
        if news_from_api:
            await save_news_items(news_from_api)
    
    stored_news = await get_latest_news_from_db()
    return render(request, 'partials/latest_news.html', {'news': stored_news})

async def analysis(request):
    context = {}
    try:
        cached_analysis = await get_latest_analysis_cache()
        if cached_analysis:
            sentiment = cached_analysis.sentiment_response
            trend_prediction = cached_analysis.trend_response
        else:
            price_history = await get_price_history_from_db()
            stored_news = await get_latest_news_from_db()
            news_titles = [n.title for n in stored_news]

            if not news_titles or not price_history:
                raise ValueError("Not enough data for analysis.")

            moving_average = calculate_moving_average(price_history)
            price_trend = calculate_price_trend(price_history)
            
            sentiment, trend_prediction = await asyncio.gather(
                agent_coordinator.analyze_sentiment(news_titles),
                agent_coordinator.predict_trend(news_titles, price_trend, moving_average)
            )
            await save_analysis_to_cache(sentiment, trend_prediction)

        # Pre-calculate confidence for template
        sentiment['confidence_percentage'] = round(sentiment.get('confidence', 0.5) * 100)
        trend_prediction['confidence_percentage'] = round(trend_prediction.get('confidence', 0.5) * 100)
        context = {'sentiment': sentiment, 'trend_prediction': trend_prediction}

    except APIQuotaExceededError as e:
        context['error'] = str(e)
    except Exception as e:
        context['error'] = "An unexpected error occurred while generating the analysis."
        print(f"Error in analysis view: {e}")

    return render(request, 'partials/analysis.html', context)

async def price_chart(request):
    price_history = await get_price_history_from_db()
    # Fetch new data if the last entry is older than 15 minutes
    if not price_history or (timezone.now() - price_history[-1].timestamp > timedelta(minutes=15)):
        historical_data = await fetch_bitcoin_historical_price(days=7)
        if historical_data:
            # The historical data contains timestamps and prices
            tasks = [save_price_history(map_price_data({'price': p[1], 'volume_24h': None}, p[0])) for p in historical_data]
            await asyncio.gather(*tasks)
        price_history = await get_price_history_from_db()

    chart_data = prepare_chart_data(price_history)
    return render(request, 'partials/price_chart.html', {'chart_data': chart_data})