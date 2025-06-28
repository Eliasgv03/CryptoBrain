import aiohttp
import os

async def fetch_bitcoin_price():
    """Fetches comprehensive Bitcoin market data from CoinGecko."""
    url = "https://api.coingecko.com/api/v3/coins/bitcoin"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()

                market_data = data.get('market_data', {})
                price_data = {
                    'price': market_data.get('current_price', {}).get('usd'),
                    'total_volume': market_data.get('total_volume', {}).get('usd'),
                    'price_change_percentage_24h': market_data.get('price_change_percentage_24h'),
                    'high_24h': market_data.get('high_24h', {}).get('usd'),
                    'low_24h': market_data.get('low_24h', {}).get('usd'),
                    'market_cap': market_data.get('market_cap', {}).get('usd'),
                }
                if price_data['price'] is not None and price_data['total_volume'] is not None:
                    return price_data
                else:
                    return None
    except Exception:
        return None

async def fetch_bitcoin_historical_price(days=7):
    """Fetches historical market data for Bitcoin for a given number of days."""
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()
                prices = data.get('prices', [])
                volumes = data.get('total_volumes', [])
                if not prices or not volumes:
                    return []
                volume_map = {v[0]: v[1] for v in volumes}
                historical_data = [
                    (p[0], p[1], volume_map.get(p[0]))
                    for p in prices if p[0] in volume_map
                ]
                return historical_data
    except Exception:
        return []

async def fetch_bitcoin_news():
    """Fetches the latest Bitcoin news from CryptoPanic."""
    api_key = os.getenv('CRYPTOPANIC_API_KEY')
    if not api_key:
        return []
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}&currencies=bitcoin"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response_text = await response.text()
                if response.status != 200:
                    response.raise_for_status()
                try:
                    data = await response.json(content_type=None)
                except aiohttp.ContentTypeError:
                    return []
                news_items = []
                results = data.get('results')
                if results is None:
                    return []
                for post in results[:20]:
                    slug = post.get('slug')
                    if post and slug:
                        news_items.append({
                            'title': post.get('title', 'No Title'),
                            'source': post.get('source', {}).get('title'),
                            'published_at': post.get('published_at'),
                            'url': f"https://cryptopanic.com/news/{slug}"
                        })
                return news_items
    except Exception:
        return []