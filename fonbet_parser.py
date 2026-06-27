import re
import requests

def extract_event_id(url):
    """Извлекает ID события из URL Fonbet"""
    match = re.search(r'/(\d{7,})(?:\?|$)', url)
    return match.group(1) if match else None

def fetch_fonbet_data(url):
    """Получает данные события через API Fonbet"""
    event_id = extract_event_id(url)
    if not event_id:
        return None
    
    endpoints = [
        f"https://line.fon.bet/feed/1_0/ru/Event/{event_id}.zip",
        f"https://fon.bet/api/sports/football/events/{event_id}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://fon.bet/'
    }
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            continue
    
    return None

def parse_fonbet_url(url):
    """Парсит URL Fonbet"""
    data = fetch_fonbet_data(url)
    if not data:
        return None
    
    try:
        result = {
            'home': data.get('home', {}).get('name', ''),
            'away': data.get('away', {}).get('name', ''),
            'h_odd': None,
            'd_odd': None,
            'a_odd': None
        }
        
        markets = data.get('markets', [])
        for market in markets:
            if market.get('type') == 'Winner':
                for outcome in market.get('outcomes', []):
                    if outcome.get('type') == 'Home':
                        result['h_odd'] = outcome.get('odd')
                    elif outcome.get('type') == 'Draw':
                        result['d_odd'] = outcome.get('odd')
                    elif outcome.get('type') == 'Away':
                        result['a_odd'] = outcome.get('odd')
        
        return result
    except:
        return None
