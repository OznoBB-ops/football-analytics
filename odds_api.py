import requests
import os
from datetime import datetime

API_KEY = os.environ.get('ODDS_API_KEY', '1107443fb49542d985d4648059f3ff69')
SPORT = 'soccer_russia_epl'  # РПЛ. Список: the-odds-api.com/sports-odds-data/sports-apis.html

SPORTS = [
    'soccer_russia_epl',      # РПЛ
    'soccer_epl',             # Англия
    'soccer_spain_la_liga',   # Испания
    'soccer_germany_bundesliga',  # Германия
    'soccer_italy_serie_a',   # Италия
    'soccer_france_ligue_one', # Франция
    'soccer_uefa_champs_league', # ЛЧ
]

def get_odds(sport_key):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
    params = {
        'apiKey': API_KEY,
        'regions': 'eu,uk',
        'markets': 'h2h',
        'oddsFormat': 'decimal'
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"❌ {sport_key}: {r.status_code} {r.text[:100]}")
            return []
    except Exception as e:
        print(f"❌ {sport_key}: {e}")
        return []

def find_best_odds(events):
    """Находит лучшие кэфы среди всех БК для каждого матча"""
    results = []
    for event in events:
        home = event['home_team']
        away = event['away_team']
        commence = event['commence_time']
        
        best_h = {'odds': 0, 'book': ''}
        best_d = {'odds': 0, 'book': ''}
        best_a = {'odds': 0, 'book': ''}
        
        for bm in event.get('bookmakers', []):
            for market in bm.get('markets', []):
                if market['key'] != 'h2h': continue
                for outcome in market['outcomes']:
                    name, odds = outcome['name'], outcome['price']
                    if outcome['name'] == home and odds > best_h['odds']:
                        best_h = {'odds': odds, 'book': bm['title']}
                    elif outcome['name'] == away and odds > best_a['odds']:
                        best_a = {'odds': odds, 'book': bm['title']}
                    elif outcome['name'] == 'Draw' and odds > best_d['odds']:
                        best_d = {'odds': odds, 'book': bm['title']}
        
        if best_h['odds'] and best_d['odds'] and best_a['odds']:
            # Fair odds без маржи
            inv = 1/best_h['odds'] + 1/best_d['odds'] + 1/best_a['odds']
            margin = (inv - 1) * 100
            fh = (1/best_h['odds']/inv)*100
            fd = (1/best_d['odds']/inv)*100
            fa = (1/best_a['odds']/inv)*100
            
            results.append({
                'home': home, 'away': away,
                'time': commence,
                'h': best_h['odds'], 'h_book': best_h['book'],
                'd': best_d['odds'], 'd_book': best_d['book'],
                'a': best_a['odds'], 'a_book': best_a['book'],
                'margin': margin,
                'fair_h': fh, 'fair_d': fd, 'fair_a': fa
            })
    return results

def main():
    print(f"🔍 Загрузка кэфов {datetime.now().strftime('%H:%M')}\n")
    
    all_events = []
    for sport in SPORTS:
        events = get_odds(sport)
        print(f"  {sport}: {len(events)} матчей")
        all_events.extend(events)
    
    print(f"\n✅ Всего: {len(all_events)} матчей\n")
    
    best = find_best_odds(all_events)
    
    print("=" * 90)
    for m in best[:15]:
        print(f"⚽ {m['home']} vs {m['away']}")
        print(f"   П1: {m['h']:.2f} ({m['h_book']}) | Х: {m['d']:.2f} ({m['d_book']}) | П2: {m['a']:.2f} ({m['a_book']})")
        print(f"   Fair: П1 {m['fair_h']:.0f}% | Х {m['fair_d']:.0f}% | П2 {m['fair_a']:.0f}% | Маржа {m['margin']:.1f}%")
        print("-" * 90)

if __name__ == "__main__":
    main()
