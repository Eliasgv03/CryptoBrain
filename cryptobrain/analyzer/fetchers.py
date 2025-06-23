import aiohttp

async def fetch_bitcoin_price():
    async with aiohttp.ClientSession() as session:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'price': data['market_data']['current_price']['usd'],
                    'volume_24h': data['market_data']['total_volume']['usd']
                }
            return None

async def fetch_bitcoin_historical_price(days=7):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # Combine prices and volumes by timestamp
                prices = data.get('prices', [])
                volumes = data.get('total_volumes', [])
                return [(p[0], p[1], v[1]) for p, v in zip(prices, volumes) if p[0] == v[0]]
            return []

async def fetch_bitcoin_news():
    async with aiohttp.ClientSession() as session:
        url = "https://cryptopanic.com/api/v1/posts/?auth_token={}&currencies=bitcoin".format(os.getenv('CRYPTOPANIC_API_KEY', ''))
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return [
                    {
                        'title': post['title'],
                        'source': post.get('source', {}).get('title'),
                        'published_at': post['published_at'],
                        'url': post['url']
                    }
                    for post in data.get('results', [])[:5]
                ]
            return []