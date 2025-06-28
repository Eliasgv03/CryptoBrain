import aiohttp
import os
import logging

# Configure logger
logger = logging.getLogger(__name__)

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
                    logger.info("Successfully fetched comprehensive Bitcoin price data.")
                    return price_data
                else:
                    logger.error("Essential price or volume data missing in CoinGecko API response.")
                    return None

    except aiohttp.ClientError as e:
        # Log status and body for HTTP errors
        if hasattr(e, 'status'):
            logger.error(f"HTTP error fetching price: Status {e.status}, Message: {e.message}")
        else:
            logger.error(f"Network error fetching price: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching price: {e}", exc_info=True)
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
                    logger.warning("Historical price or volume data is empty.")
                    return []

                # Use a dictionary for efficient volume lookup to handle potential data misalignment
                volume_map = {v[0]: v[1] for v in volumes}
                
                historical_data = [
                    (p[0], p[1], volume_map.get(p[0])) 
                    for p in prices if p[0] in volume_map
                ]
                logger.info(f"Successfully fetched {len(historical_data)} historical data points.")
                return historical_data

    except aiohttp.ClientError as e:
        if hasattr(e, 'status'):
            logger.error(f"HTTP error fetching historical data: Status {e.status}, Message: {e.message}")
        else:
            logger.error(f"Network error fetching historical data: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching historical data: {e}", exc_info=True)
        return []

async def fetch_bitcoin_news():
    """Fetches the latest Bitcoin news from CryptoPanic with enhanced logging."""
    api_key = os.getenv('CRYPTOPANIC_API_KEY')
    if not api_key:
        logger.error("CRITICAL: CRYPTOPANIC_API_KEY is not set. News fetching will fail.")
        return []

    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}&currencies=bitcoin"
    logger.info("Attempting to fetch news from CryptoPanic API.")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                logger.info(f"CryptoPanic API response status: {response.status}")
                response_text = await response.text()

                if response.status != 200:
                    logger.error(f"CryptoPanic API returned non-200 status. Body: {response_text[:500]}")
                    response.raise_for_status() # Trigger exception for handling below

                try:
                    # Try to parse JSON, be lenient with content type
                    data = await response.json(content_type=None)
                except aiohttp.ContentTypeError:
                    logger.error(f"Failed to decode JSON from CryptoPanic. Response text: {response_text[:500]}", exc_info=True)
                    return []

                news_items = []
                results = data.get('results')
                if results is None:
                    logger.warning(f"CryptoPanic response missing 'results' key. Full response: {data}")
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
                
                logger.info(f"Successfully fetched and processed {len(news_items)} news items.")
                return news_items

    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching news: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching news: {e}", exc_info=True)
        return []