import re
import os
import csv
from datetime import datetime
from teams_ru import translate_team

def parse_bookmaker_text(text):
    matches = []
    blocks = re.split(r'\n\s*\n', text.strip())
    
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 5:
            continue
        
        odds_indices = []
        for i, line in enumerate(lines):
            try:
                val = float(line.replace(',', '.'))
                if 1.01 <= val <= 100:
                    odds_indices.append(i)
            except:
                pass
        
        odds = []
        odds_start = None
        for i in range(len(odds_indices) - 2):
            if odds_indices[i+1] == odds_indices[i] + 1 and odds_indices[i+2] == odds_indices[i] + 2:
                odds_start = odds_indices[i]
                odds = [
                    float(lines[odds_indices[i]].replace(',', '.')),
                    float(lines[odds_indices[i+1]].replace(',', '.')),
                    float(lines[odds_indices[i+2]].replace(',', '.'))
                ]
                break
        
        if not odds or len(odds) < 3:
            continue
        
        h_odd, d_odd, a_odd = odds
        before_odds = lines[:odds_start]
        
        text_lines = []
        for line in before_odds:
            if re.match(r'^\d+$', line): continue
            if re.match(r'^(\dТ|Live|\+|Основн|Футбол)', line, re.IGNORECASE): continue
            text_lines.append(line)
        
        if len(text_lines) < 3:
            continue
        
        league_line = text_lines[0]
        home = text_lines[1] if len(text_lines) > 1 else ''
        away = text_lines[2] if len(text_lines) > 2 else ''
        
        league = league_line
        for country in ['Австралия', 'Россия', 'Англия', 'Испания', 'Германия', 'Италия', 'Франция', 'Польша', 'Финляндия', 'Турция', 'Греция', 'Бельгия', 'Шотландия', 'Португалия']:
            league = league.replace(country, '').strip().rstrip(',')
        
        if not home or not away:
            continue
        
        matches.append({
            'home': home, 'away': away,
            'h_odd': h_odd, 'd_odd': d_odd, 'a_odd': a_odd,
            'league': league,
            'date': datetime.now().strftime('%d.%m.%Y'),
            'time': datetime.now().strftime('%H:%M')
        })
    
    return matches

def save_to_base(matches, filename='live_matches.csv'):
    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'time', 'home', 'away', 'h_odd', 'd_odd', 'a_odd', 'league', 'parsed_at'])
        if not file_exists:
            writer.writeheader()
        for m in matches:
            row = m.copy()
            row['parsed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            writer.writerow(row)
    return len(matches)

def analyze_match(match, all_matches, patterns):
    from recommendations import analyze_team_form, analyze_h2h, check_patterns
    
    home_norm = match['home'].lower()
    away_norm = match['away'].lower()
    
    home_in_base = away_in_base = None
    for m in all_matches:
        if home_norm in m['home_lower'] or m['home_lower'] in home_norm:
            home_in_base = m['home']
        if away_norm in m['away_lower'] or m['away_lower'] in away_norm:
            away_in_base = m['away']
    
    result = {
        'match': match,
        'in_base': home_in_base is not None or away_in_base is not None,
        'h2h': None,
        'recommendations': []
    }
    
    if home_in_base:
        result['form_home'] = analyze_team_form(all_matches, home_in_base, last_n=10)
    if away_in_base:
        result['form_away'] = analyze_team_form(all_matches, away_in_base, last_n=10)
    if home_in_base and away_in_base:
        result['h2h'] = analyze_h2h(all_matches, home_in_base, away_in_base)
    
    synthetic = {
        'home': home_in_base or match['home'],
        'away': away_in_base or match['away'],
        'home_lower': (home_in_base or match['home']).lower(),
        'away_lower': (away_in_base or match['away']).lower(),
        'h_odd': match['h_odd'], 'd_odd': match['d_odd'], 'a_odd': match['a_odd'],
        'res': None
    }
    
    found = check_patterns(synthetic, patterns)
    recs = []
    
    for p in found[:3]:
        if p['type'] == '1X2':
            recs.append({'bet': f"{p['bet']} @ {p['odds']:.2f}", 'reason': f"💰 Валуй ROI {p['roi']:+.0f}%", 'score': min(40, p['roi'] * 2)})
        elif p['type'] == 'totals':
            recs.append({'bet': p['bet'], 'reason': f"📊 {p['real']:.0f}%", 'score': min(35, p['roi'] * 1.5)})
        elif p['type'] == 'btts':
            recs.append({'bet': p['bet'], 'reason': f"📊 {p['real']:.0f}%", 'score': min(35, p['roi'] * 1.5)})
    
    if result.get('form_home') and result['form_home']['winrate'] > 60:
        recs.append({'bet': f"П1 @ {match['h_odd']:.2f}", 'reason': f"🏠 Форма {result['form_home']['winrate']:.0f}%", 'score': 20})
    if result.get('form_away') and result['form_away']['winrate'] > 60:
        recs.append({'bet': f"П2 @ {match['a_odd']:.2f}", 'reason': f"✈️ Форма {result['form_away']['winrate']:.0f}%", 'score': 20})
    
    if result['h2h'] and result['h2h']['matches'] >= 3:
        if result['h2h']['over25_pct'] > 65:
            recs.append({'bet': 'ТБ 2.5', 'reason': f"⚔️ H2H ТБ {result['h2h']['over25_pct']:.0f}%", 'score': 15})
        if result['h2h']['btts_pct'] > 65:
            recs.append({'bet': 'ОЗ Да', 'reason': f"⚔️ H2H ОЗ {result['h2h']['btts_pct']:.0f}%", 'score': 15})
    
    recs.sort(key=lambda x: x['score'], reverse=True)
    result['recommendations'] = recs[:5]
    return result

def format_for_telegram(analyses):
    """Компактный формат без таблиц"""
    lines = []
    
    for i, a in enumerate(analyses, 1):
        m = a['match']
        home_ru = translate_team(m['home'])
        away_ru = translate_team(m['away'])
        
        inv = 1/m['h_odd'] + 1/m['d_odd'] + 1/m['a_odd']
        margin = (inv - 1) * 100
        fh = (1/m['h_odd']/inv)*100
        fd = (1/m['d_odd']/inv)*100
        fa = (1/m['a_odd']/inv)*100
        
        lines.append(f"<b>{i}. {home_ru} vs {away_ru}</b>")
        lines.append(f"🏆 {m['league']}")
        lines.append(f"💰 П1: {m['h_odd']:.2f} | Х: {m['d_odd']:.2f} | П2: {m['a_odd']:.2f} | Маржа: {margin:.1f}%")
        lines.append(f"🎯 Fair: П1 {fh:.0f}% | Х {fd:.0f}% | П2 {fa:.0f}%")
        
        if a.get('form_home'):
            fh = a['form_home']
            lines.append(f"🏠 Форма: {fh['wins']}W {fh['draws']}D {fh['losses']}L ({fh['winrate']:.0f}%) | xG {fh['avg_gf']:.1f}")
        if a.get('form_away'):
            fa = a['form_away']
            lines.append(f"✈️ Форма: {fa['wins']}W {fa['draws']}D {fa['losses']}L ({fa['winrate']:.0f}%) | xG {fa['avg_gf']:.1f}")
        
        if a.get('h2h') and a['h2h']['matches'] >= 2:
            h = a['h2h']
            lines.append(f"⚔️ H2H: {h['matches']} матчей | ТБ2.5: {h['over25_pct']:.0f}% | ОЗ: {h['btts_pct']:.0f}%")
        elif not a['in_base']:
            lines.append("⚠️ Команды не найдены в базе")
        
        if a['recommendations']:
            lines.append("")
            lines.append("💡 <b>Рекомендации:</b>")
            for r in a['recommendations']:
                lines.append(f"  • <b>{r['bet']}</b> — {r['reason']}")
        
        lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    test_text = """Live

Основные
Футбол
Квинсленд, Премьер ЛигаАвстралия
1
Пенинсула Пауэр
Брисбен Роар (мол)
0
0
0
0
1.47
3.65
6.50
1Т 44'
+42"""
    
    matches = parse_bookmaker_text(test_text)
    print(f"✅ Найдено {len(matches)} матчей:\n")
    for m in matches:
        inv = 1/m['h_odd'] + 1/m['d_odd'] + 1/m['a_odd']
        margin = (inv - 1) * 100
        print(f"🏆 {m['league']}")
        print(f"⚽ {m['home']} vs {m['away']}")
        print(f"💰 {m['h_odd']}/{m['d_odd']}/{m['a_odd']} | Маржа: {margin:.1f}%\n")
