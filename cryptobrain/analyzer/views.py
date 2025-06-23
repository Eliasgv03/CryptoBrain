from django.shortcuts import render
from django.utils import timezone
from functools import reduce
from .fetchers import fetch_bitcoin_price, fetch_bitcoin_historical_price, fetch_bitcoin_news
from .models import BitcoinPriceHistory, BitcoinNews
import asyncio

# Funciones funcionales importadas
from .processor import map_price_data, filter_new_news, save_price_history, save_news_item
from .processor import calculate_moving_average, calculate_price_trend, prepare_chart_data, preprocess_news_titles
from .agent import agent_coordinator

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
        historical_entries = [
            save_price_history(map_price_data({'price': price, 'volume_24h': volume}, ts))
            for ts, price, volume in historical_data
        ]

    if news:
        existing_urls = set(BitcoinNews.objects.values_list('url', flat=True))
        new_news_items = filter_new_news(existing_urls, news)
        list(map(save_news_item, new_news_items))

    # Obtener datos almacenados para el dashboard
    price_history = BitcoinPriceHistory.objects.all().order_by('timestamp')[:100]
    stored_news = BitcoinNews.objects.all().order_by('-published_at')[:5]
    news_titles = [n.title for n in stored_news]

    # Calcular métricas y predicciones
    moving_average = calculate_moving_average(price_history)
    price_trend = calculate_price_trend(price_history)
    sentiment = await agent_coordinator.analyze_sentiment(news_titles)
    trend_prediction = await agent_coordinator.predict_trend(news_titles, price_trend, moving_average)
    chart_data = prepare_chart_data(price_history)

    # Preparar contexto para la plantilla
    context = {
        'crypto': 'BTC',
        'price_data': price_data,
        'news': stored_news,
        'sentiment': sentiment,
        'trend_prediction': trend_prediction,
        'chart_data': chart_data,
        'last_updated': timezone.now().strftime('%H:%M:%S')
    }
    return render(request, 'analyzer/dashboard.html', context)