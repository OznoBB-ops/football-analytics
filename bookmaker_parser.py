import re
import os
import csv
from datetime import datetime
from itertools import combinations
from teams_ru import translate_team

JUNK_PATTERNS = [
    r'^(Live|Основные|Все|Загрузить|Футбол|Теннис|Баскетбол|Хоккей|Киберспорт|Кибер FIFA|Кибер NBA|Кибер NHL|Настольный теннис|Волейбол|Падел|Австралийский футбол|Баскетбол 3x3|Бейсбол|Гандбол|Пляжный волейбол|Регби|Футзал)$',
    r'^(Winline|Удобнее в приложении|Winline в iOS и Android)$',
]

COUNTRIES = ['Австралия', 'Россия', 'Англия', 'Испания', 'Германия', 'Италия', 
             'Франция', 'Польша', 'Финляндия', 'Турция', 'Греция', 'Бельгия', 
             'Шотландия', 'Португалия', 'Нидерланды', 'Украина', 'Бразилия', 
             'Аргентина', 'Мексика', 'США', 'Япония', 'Китай', 'Корея']

def is_junk(line):
    line = line.strip()
    for pattern in JUNK_PATTERNS:
        if re.match(pattern, line, re.IGNORECASE):
            return True
    return False

def is_score_or_status(line):
    line = line.strip()
    if line in ('-', 'Пер.', 'Итог'):
        return True
    if re.match(r'^\dТ \d+\'?$', line):
        return True
    if re.match(r'^\+\d+$', line):
        return True
    try:
        int(line)
        return True
    except:
        pass
    return False

def is_odds(val):
    try:
        v = float(val.replace(',', '.'))
        return 1.01 <= v <= 100
    except:
        return False

def parse_bookmaker_text(text):
    matches = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    lines = [l for l in lines if not is_junk(l)]
    
    i = 0
    while i < len(lines) - 2:
        # Ищем 3 основных кэфа 1X2
        if is_odds(lines[i]) and is_odds(lines[i+1]) and is_odds(lines[i+2]):
            h_odd = float(lines[i].replace(',', '.'))
            d_odd = float(lines[i+1].replace(',', '.'))
            a_odd = float(lines[i+2].replace(',', '.'))
            
            # Идём назад за командами
            j = i - 1
            while j >= 0 and is_score_or_status(lines[j]):
                j -= 1
            
            if j >= 2:
                away = lines[j]
                home = lines[j-1]
                
                league_idx = j - 2
                if league_idx >= 0 and lines[league_idx] in ('1', '2'):
                    league_idx -= 1
                
                league = lines[league_idx] if league_idx >= 0 else ''
                league_clean = league
                for country in COUNTRIES:
                    league_clean = league_clean.replace(country, '').strip().rstrip(',')
                
                if (home and away and league_clean and 
                    len(home) >= 3 and len(away) >= 3 and
                    home != away and
                    not re.match(r'^\d+$', home) and
                    not re.match(r'^\d+$', away)):
                    
                    # Парсим дополнительные рынки (тоталы, форы) после основных кэфов
                    extra_markets = parse_extra_markets(lines, i+3)
                    
                    matches.append({
                        'home': home, 'away': away,
                        'h_odd': h_odd, 'd_odd': d_odd, 'a_odd': a_odd,
                        'league': league_clean,
                        'date': datetime.now().strftime('%d.%m.%Y'),
                        'time': datetime.now().strftime('%H:%M'),
                        'markets': extra_markets
                    })
            
            i += 3
            continue
        
        i += 1
    
    return matches

def parse_extra_markets(lines, start_idx):
    """Парсит тоталы и форы после основных кэфов"""
    markets = {'totals': {}, 'foras': {}, 'btts': {}}
    
    # Ищем пары кэфов в следующих 30 строках
    i = start_idx
    last_label = None
    limit = min(start_idx + 30, len(lines))
    
    while i < limit - 1:
        line = lines[i].strip()
        
        # Определяем тип рынка по лейблу
        if 'Тотал' in line or 'Total' in line:
            # Ищем значение тотала (2.5, 1.5, 3.5 и т.д.)
            match = re.search(r'(\d+\.5)', line)
            if match:
                total_val = match.group(1)
                # Следующие 2 строки — кэфы ТБ и ТМ
                if i+2 < len(lines) and is_odds(lines[i+1]) and is_odds(lines[i+2]):
                    over = float(lines[i+1].replace(',', '.'))
                    under = float(lines[i+2].replace(',', '.'))
                    markets['totals'][total_val] = {'over': over, 'under': under}
                    i += 3
                    continue
        elif 'Фора' in line or 'F1' in line or 'Ф1' in line:
            # Ищем гандикап (-1, +1.5, -0.5 и т.д.)
            match = re.search(r'([+-]?\d+\.?\d*)', line)
            if match:
                handicap = match.group(1)
                if i+2 < len(lines) and is_odds(lines[i+1]) and is_odds(lines[i+2]):
                    f1 = float(lines[i+1].replace(',', '.'))
                    f2 = float(lines[i+2].replace(',', '.'))
                    markets['foras'][handicap] = {'f1': f1, 'f2': f2}
                    i += 3
                    continue
        elif 'Обе забьют' in line or 'ОЗ' in line:
            if i+2 < len(lines) and is_odds(lines[i+1]) and is_odds(lines[i+2]):
                yes = float(lines[i+1].replace(',', '.'))
                no = float(lines[i+2].replace(',', '.'))
                markets['btts'] = {'yes': yes, 'no': no}
                i += 3
                continue
        
        i += 1
    
    return markets

def save_to_base(matches, filename='live_matches.csv'):
    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'time', 'home', 'away', 'h_odd', 'd_odd', 'a_odd', 'league', 'parsed_at'])
        if not file_exists:
            writer.writeheader()
        for m in matches:
            row = {k: v for k, v in m.items() if k != 'markets'}
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
    
    # 1X2 рекомендации
    for p in found[:3]:
        if p['type'] == '1X2':
            recs.append({'bet': f"{p['bet']} @ {p['odds']:.2f}", 'reason': f"💰 ROI {p['roi']:+.0f}%", 'score': min(40, p['roi'] * 2), 'odd': p['odds']})
        elif p['type'] == 'totals':
            recs.append({'bet': p['bet'], 'reason': f"📊 {p['real']:.0f}%", 'score': min(35, p['roi'] * 1.5), 'odd': 1.9})
        elif p['type'] == 'btts':
            recs.append({'bet': p['bet'], 'reason': f"📊 {p['real']:.0f}%", 'score': min(35, p['roi'] * 1.5), 'odd': 1.9})
    
    # Тоталы из парсера
    markets = match.get('markets', {})
    if '2.5' in markets.get('totals', {}) and result.get('h2h'):
        t = markets['totals']['2.5']
        if result['h2h']['over25_pct'] > 65:
            recs.append({'bet': f"ТБ 2.5 @ {t['over']:.2f}", 'reason': f"⚔️ H2H ТБ {result['h2h']['over25_pct']:.0f}%", 'score': 25, 'odd': t['over']})
        elif result['h2h']['over25_pct'] < 40:
            recs.append({'bet': f"ТМ 2.5 @ {t['under']:.2f}", 'reason': f"⚔️ H2H ТМ {100-result['h2h']['over25_pct']:.0f}%", 'score': 25, 'odd': t['under']})
    
    # Форы из парсера
    if result.get('form_home') and result.get('form_away'):
        diff = result['form_home']['winrate'] - result['form_away']['winrate']
        if diff > 30 and '-1' in markets.get('foras', {}):
            f = markets['foras']['-1']
            recs.append({'bet': f"Ф1(-1) @ {f['f1']:.2f}", 'reason': f"📈 Разница формы {diff:.0f}%", 'score': 20, 'odd': f['f1']})
        elif diff < -30 and '-1' in markets.get('foras', {}):
            f = markets['foras']['-1']
            recs.append({'bet': f"Ф2(-1) @ {f['f2']:.2f}", 'reason': f"📈 Разница формы {-diff:.0f}%", 'score': 20, 'odd': f['f2']})
    
    # Форма
    if result.get('form_home') and result['form_home']['winrate'] > 60:
        recs.append({'bet': f"П1 @ {match['h_odd']:.2f}", 'reason': f"🏠 Форма {result['form_home']['winrate']:.0f}%", 'score': 20, 'odd': match['h_odd']})
    if result.get('form_away') and result['form_away']['winrate'] > 60:
        recs.append({'bet': f"П2 @ {match['a_odd']:.2f}", 'reason': f"✈️ Форма {result['form_away']['winrate']:.0f}%", 'score': 20, 'odd': match['a_odd']})
    
    # H2H
    if result['h2h'] and result['h2h']['matches'] >= 3:
        if result['h2h']['btts_pct'] > 65 and 'yes' in markets.get('btts', {}):
            recs.append({'bet': f"ОЗ Да @ {markets['btts']['yes']:.2f}", 'reason': f"⚔️ H2H ОЗ {result['h2h']['btts_pct']:.0f}%", 'score': 20, 'odd': markets['btts']['yes']})
    
    recs.sort(key=lambda x: x['score'], reverse=True)
    result['recommendations'] = recs[:5]
    return result

def generate_express(analyses, min_matches=2, max_matches=5):
    """Генерирует экспрессы из топ-рекомендаций"""
    express_candidates = []
    
    # Берём топ-рекомендацию из каждого матча
    for a in analyses:
        if a['recommendations']:
            best = a['recommendations'][0]
            express_candidates.append({
                'match': f"{translate_team(a['match']['home'])} vs {translate_team(a['match']['away'])}",
                'bet': best['bet'],
                'odd': best.get('odd', 1.5),
                'score': best['score'],
                'reason': best['reason']
            })
    
    if len(express_candidates) < 2:
        return []
    
    express_list = []
    
    # Генерируем экспрессы разного размера
    for size in range(min_matches, min(max_matches+1, len(express_candidates)+1)):
        # Сортируем по score, берём топ-N
        sorted_cands = sorted(express_candidates, key=lambda x: x['score'], reverse=True)[:size+3]
        
        # Все комбинации размера size
        for combo in combinations(sorted_cands, size):
            total_odd = 1
            total_score = 0
            for c in combo:
                total_odd *= c['odd']
                total_score += c['score']
            
            # Оценка риска
            avg_score = total_score / size
            if avg_score >= 30:
                risk = "🟢 Умеренный"
            elif avg_score >= 20:
                risk = "🟡 Средний"
            else:
                risk = "🔴 Высокий"
            
            express_list.append({
                'matches': [c['match'] for c in combo],
                'bets': [c['bet'] for c in combo],
                'total_odd': total_odd,
                'avg_score': avg_score,
                'risk': risk,
                'size': size
            })
    
    # Сортируем по соотношению риск/прибыль
    express_list.sort(key=lambda x: (x['total_odd'] * x['avg_score'] / 100), reverse=True)
    return express_list[:5]

def generate_systems(analyses):
    """Генерирует системы (2 из 3, 3 из 4 и т.д.)"""
    candidates = []
    for a in analyses:
        if a['recommendations']:
            best = a['recommendations'][0]
            candidates.append({
                'match': f"{translate_team(a['match']['home'])} vs {translate_team(a['match']['away'])}",
                'bet': best['bet'],
                'odd': best.get('odd', 1.5),
                'score': best['score']
            })
    
    if len(candidates) < 3:
        return []
    
    systems = []
    n = len(candidates)
    
    # Системы: 2 из 3, 2 из 4, 3 из 4, 3 из 5, 4 из 5
    system_configs = [(2, 3), (2, 4), (3, 4), (3, 5), (4, 5)]
    
    for k, m in system_configs:
        if m > n:
            continue
        
        # Берём топ-m событий
        top_m = sorted(candidates, key=lambda x: x['score'], reverse=True)[:m]
        
        # Все комбинации по k
        total_combos = 0
        win_combos = 0
        total_cost = 0
        total_payout = 0
        
        for combo in combinations(top_m, k):
            total_combos += 1
            combo_odd = 1
            for c in combo:
                combo_odd *= c['odd']
            total_cost += 1  # 1 единица ставки на комбинацию
            total_payout += combo_odd
        
        # Ожидаемый ROI (упрощённо)
        avg_odd_per_combo = total_payout / total_combos
        expected_roi = (avg_odd_per_combo - total_combos) / total_combos * 100
        
        systems.append({
            'name': f"Система {k} из {m}",
            'events': [c['match'] for c in top_m],
            'bets': [c['bet'] for c in top_m],
            'combos': total_combos,
            'cost': total_cost,
            'max_payout': max(combo_odd for combo_odd in [1] + [
                prod([c['odd'] for c in combo]) for combo in combinations(top_m, k)
            ]),
            'avg_payout': avg_odd_per_combo,
            'expected_roi': expected_roi
        })
    
    return systems

def prod(iterable):
    result = 1
    for x in iterable:
        result *= x
    return result

def format_for_telegram(analyses, express_list=None, systems_list=None):
    lines = []
    
    # Основные матчи
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
        
        # Тоталы из парсера
        markets = m.get('markets', {})
        if markets.get('totals'):
            totals_str = " | ".join([f"Т{v}: ТБ {d['over']:.2f}/ТМ {d['under']:.2f}" for v, d in list(markets['totals'].items())[:2]])
            lines.append(f"📊 Тоталы: {totals_str}")
        
        # Форы из парсера
        if markets.get('foras'):
            foras_str = " | ".join([f"Ф{k}: {d['f1']:.2f}/{d['f2']:.2f}" for k, d in list(markets['foras'].items())[:2]])
            lines.append(f"📈 Форы: {foras_str}")
        
        # ОЗ
        if markets.get('btts'):
            btts = markets['btts']
            lines.append(f"⚽ ОЗ: Да {btts['yes']:.2f} / Нет {btts['no']:.2f}")
        
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
    
    # Экспрессы
    if express_list:
        lines.append("=" * 40)
        lines.append("🎰 <b>ЭКСПРЕССЫ</b>")
        lines.append("=" * 40)
        for i, exp in enumerate(express_list[:3], 1):
            lines.append(f"\n<b>Экспресс #{i}</b> ({exp['size']} событий) | {exp['risk']}")
            lines.append(f"💰 Итоговый кэф: <b>{exp['total_odd']:.2f}</b>")
            lines.append(f"📊 Средний score: {exp['avg_score']:.0f}")
            for j, (match, bet) in enumerate(zip(exp['matches'], exp['bets']), 1):
                lines.append(f"  {j}. {match}")
                lines.append(f"     → {bet}")
            lines.append("")
    
    # Системы
    if systems_list:
        lines.append("=" * 40)
        lines.append("🎯 <b>СИСТЕМЫ</b>")
        lines.append("=" * 40)
        for sys in systems_list[:3]:
            lines.append(f"\n<b>{sys['name']}</b>")
            lines.append(f"📋 Комбинаций: {sys['combos']} | Стоимость: {sys['cost']} ед.")
            lines.append(f"💰 Макс. выплата: {sys['max_payout']:.2f}")
            lines.append(f"📊 Средняя выплата: {sys['avg_payout']:.2f}")
            lines.append(f"📈 Ожидаемый ROI: {sys['expected_roi']:+.0f}%")
            lines.append("События:")
            for j, (match, bet) in enumerate(zip(sys['events'], sys['bets']), 1):
                lines.append(f"  {j}. {match} → {bet}")
            lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    test_text = """Live

Основные
Футбол
Квинсленд, Премьер Лига 1Австралия
1
Сент-Джордж Уиллавонг
Норд Стар
0
0
0
0
2.70
3.40
2.35
Тотал 2.5
1.85
1.95
Фора1(-1)
4.50
1.35
Обе забьют
1.75
2.05
1Т 19'
+69"""
    
    matches = parse_bookmaker_text(test_text)
    print(f"✅ Найдено {len(matches)} матчей:\n")
    for m in matches:
        inv = 1/m['h_odd'] + 1/m['d_odd'] + 1/m['a_odd']
        margin = (inv - 1) * 100
        print(f"🏆 {m['league']}")
        print(f"⚽ {m['home']} vs {m['away']}")
        print(f"💰 1X2: {m['h_odd']}/{m['d_odd']}/{m['a_odd']} | Маржа: {margin:.1f}%")
        print(f"📊 Рынки: {m.get('markets', {})}\n")
