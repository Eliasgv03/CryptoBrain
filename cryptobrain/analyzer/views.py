from django.shortcuts import render
from django.utils import timezone
from functools import reduce
from .fetchers import fetch_bitcoin_price, fetch_bitcoin_historical_price, fetch_bitcoin_news
from .models import BitcoinPriceHistory, BitcoinNews
import asyncio

# Funciones funcionales
def map_price_data(price_data, timestamp):
    return {
        'timestamp': timezone.datetime.fromtimestamp(timestamp / 1000) if timestamp else timezone.now(),
        'price': price_data.get('price', 0),
        'volume_24h': price_data.get('volume_24h', None)
    }

def filter_new_news(existing_urls, news_items):
    return [item for item in news_items if item.get('url') not in existing_urls]

def save_price_history(price_data):
    return BitcoinPriceHistory.objects.update_or_create(
        timestamp=price_data['timestamp'],
        defaults={'price': price_data['price'], 'volume_24h': price_data['volume_24h']}
    )[0]

def save_news_item(news_item):
    return BitcoinNews.objects.update_or_create(
        url=news_item['url'],
        defaults={
            'title': news_item['title'],
            'source': news_item.get('source', 'Unknown'),
            'published_at': timezone.datetime.strptime(news_item['published_at'], '%Y-%m-%dT%H:%M:%SZ')
        }
    )[0]

async def dashboard(request):
    # Recolectar datos asíncronamente
    price_data, historical_data, news = await asyncio.gather(
        fetch_bitcoin_price(),
        fetch_bitcoin_historical_price(days=7),
        fetch_bitcoin_news()
    )

    # Procesar y guardar datos
    if price_data:
        current_data = map_price_data(price_data, None)
        save_price_history(current_data)

    if historical_data:
        historical_entries = [save_price_history(map_price_data({'price': price, 'volume_24h': volume}, ts))
                            for ts, price, volume in historical_data]

    if news:
        existing_urls = set(BitcoinNews.objects.values_list('url', flat=True))
        new_news_items = filter_new_news(existing_urls, news)
        list(map(save_news_item, new_news_items))

    # Obtener datos almacenados para el dashboard
    price_history = list(BitcoinPriceHistory.objects.all().order_by('timestamp')[:100])
    stored_news = BitcoinNews.objects.all().order_by('-published_at')[:5]

    context = {
        'crypto': 'BTC',
        'price_data': price_data,
        'news': stored_news,
        'price_history': price_history,
        'last_updated': timezone.now().strftime('%H:%M:%S')
    }
    return render(request, 'analyzer/dashboard.html', context)