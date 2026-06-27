import re
import os
import csv
from datetime import datetime
from itertools import combinations
from teams_ru import translate_team
from predictor import calculate_expected_goals, predict_exact_scores, predict_outcomes, find_value_bets

JUNK = [
    r'^(Live|Основные|Все|Загрузить|Футбол|Теннис|Баскетбол|Хоккей|Киберспорт|Кибер FIFA|Кибер NBA|Кибер NHL|Настольный теннис|Волейбол|Падел|Австралийский футбол|Баскетбол 3x3|Бейсбол|Гандбол|Пляжный волейбол|Регби|Футзал)$',
    r'^(Winline|GGTBET|GGTBET\.com|GGTVER|Удобнее в приложении|Winline в iOS и Android)$',
]

COUNTRIES = ['Австралия', 'Россия', 'Англия', 'Испания', 'Германия', 'Италия', 
             'Франция', 'Польша', 'Финляндия', 'Турция', 'Греция', 'Бельгия', 
             'Шотландия', 'Португалия', 'Нидерланды', 'Украина', 'Бразилия', 
             'Аргентина', 'Мексика', 'США', 'Япония', 'Китай', 'Корея']

def is_junk(line):
    for p in JUNK:
        if re.match(p, line.strip(), re.IGNORECASE):
            return True
    return False

def is_status(line):
    """Статус матча: 1Т 33', +69, Пер., Итог"""
    line = line.strip()
    if line in ('-', 'Пер.', 'Итог'):
        return True
    if re.match(r'^\dТ \d+', line):
        return True
    if re.match(r'^\+\d+$', line):
        return True
    return False

def is_score(line):
    """Слитные счёта (10, 00, 21) и маленькие числа"""
    line = line.strip()
    if re.match(r'^\d{2}$', line):
        return True
    try:
        v = int(line)
        return 0 <= v <= 9
    except:
        return False

def is_odds(val):
    """Настоящий кэф — с точкой, 1.01-100"""
    val = val.strip().replace(',', '.')
    try:
        v = float(val)
        if '.' not in val and v >= 10:
            return False
        return 1.01 <= v <= 100
    except:
        return False

def is_total_line(line):
    """М3.5Б, Б2.5М, ТБ2.5, ТМ1.5"""
    line = line.strip()
    m = re.match(r'^([МБТ])(\d+\.?\d*)([МБ]?)$', line)
    if m:
        return m.group(1), float(m.group(2)), m.group(3)
    return None

def is_league(line):
    """Лига содержит запятую или слова Лига/Премьер/Кубок/Дивизион"""
    line = line.strip()
    if ',' in line:
        return True
    if any(w in line for w in ['Лига', 'Премьер', 'Кубок', 'Дивизион', 'Серия', 'Чемпионат']):
        return True
    return False

def is_team_name(line):
    """Название команды"""
    line = line.strip()
    if not line or len(line) < 3:
        return False
    if is_status(line) or is_score(line) or is_odds(line) or is_total_line(line):
        return False
    if re.match(r'^\d+$', line):
        return False
    if line in ('1', '2'):
        return False
    return True

def parse_bookmaker_text(text):
    """Парсер: разбивает текст на блоки по статусам матчей"""
    matches = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    lines = [l for l in lines if not is_junk(l)]
    
    # Разбиваем на блоки по статусам матчей
    # Блок = всё между двумя статусами (или от начала до статуса, от статуса до конца)
    blocks = []
    current_block = []
    
    for line in lines:
        current_block.append(line)
        if is_status(line):
            blocks.append(current_block)
            current_block = []
    
    if current_block:
        blocks.append(current_block)
    
    # Парсим каждый блок
    for block in blocks:
        if len(block) < 3:
            continue
        
        # Ищем в блоке: [лига?] [1/2?] команда1 команда2 [счёт...] [кэфы...]
        teams = []
        odds = []
        totals = {}
        league = 'N/A'
        
        i = 0
        # Пропускаем статусы в начале блока (они от предыдущего матча)
        while i < len(block) and is_status(block[i]):
            i += 1
        
        # Ищем лигу (если есть)
        if i < len(block) and is_league(block[i]):
            league = block[i]
            for c in COUNTRIES:
                league = league.replace(c, '').strip().rstrip(',')
            i += 1
        
        # Пропускаем маркер "1" или "2"
        if i < len(block) and block[i] in ('1', '2'):
            i += 1
        
        # Ищем две команды подряд
        while i < len(block) - 1 and len(teams) < 2:
            if is_team_name(block[i]) and is_team_name(block[i+1]):
                teams = [block[i], block[i+1]]
                i += 2
                break
            i += 1
        
        if len(teams) != 2:
            continue
        
        # Парсим остальное: счёта, кэфы, тоталы
        while i < len(block):
            line = block[i]
            
            # Статус — конец блока
            if is_status(line):
                break
            
            # Тотал М3.5Б
            total_info = is_total_line(line)
            if total_info:
                prefix, value, suffix = total_info
                if i+1 < len(block) and is_odds(block[i+1]):
                    odd = float(block[i+1].replace(',', '.'))
                    key = str(value)
                    if key not in totals:
                        totals[key] = {}
                    if prefix == 'М' or suffix == 'М':
                        totals[key]['under'] = odd
                    elif prefix == 'Б' or suffix == 'Б':
                        totals[key]['over'] = odd
                    i += 2
                    continue
            
            # Кэф
            if is_odds(line):
                odds.append(float(line.replace(',', '.')))
                i += 1
                continue
            
            # Счёт или прочерк — пропускаем
            if is_score(line) or line == '-':
                i += 1
                continue
            
            i += 1
        
        # Определяем кэфы 1X2
        h_odd = d_odd = a_odd = None
        if len(odds) >= 3:
            h_odd, d_odd, a_odd = odds[0], odds[1], odds[2]
        elif len(odds) == 1:
            h_odd = odds[0]
        
        home, away = teams
        
        matches.append({
            'home': home, 'away': away,
            'h_odd': h_odd, 'd_odd': d_odd, 'a_odd': a_odd,
            'league': league,
            'date': datetime.now().strftime('%d.%m.%Y'),
            'time': datetime.now().strftime('%H:%M'),
            'markets': {'totals': totals, 'foras': {}, 'btts': {}, 'exact_scores': {}}
        })
    
    return matches

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
        'recommendations': [],
        'xg': None,
        'predictions': None,
        'value_bets': []
    }
    
    form_home = form_away = None
    if home_in_base:
        form_home = analyze_team_form(all_matches, home_in_base, last_n=10)
        result['form_home'] = form_home
    if away_in_base:
        form_away = analyze_team_form(all_matches, away_in_base, last_n=10)
        result['form_away'] = form_away
    if home_in_base and away_in_base:
        result['h2h'] = analyze_h2h(all_matches, home_in_base, away_in_base)
    
    if form_home or form_away:
        xg = calculate_expected_goals(form_home, form_away, result['h2h'])
        result['xg'] = xg
        predictions = predict_outcomes(xg['home_xg'], xg['away_xg'])
        result['predictions'] = predictions
        result['exact_scores'] = predict_exact_scores(xg['home_xg'], xg['away_xg'])[:5]
        
        market_odds = {
            'h_odd': match['h_odd'], 'd_odd': match['d_odd'], 'a_odd': match['a_odd'],
            'markets': match.get('markets', {})
        }
        result['value_bets'] = find_value_bets(predictions, market_odds)
    
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
    
    for vb in result.get('value_bets', [])[:3]:
        recs.append({
            'bet': vb['bet'],
            'reason': f"🎯 Edge {vb['edge']:+.0f}% (fair {vb['fair_odd']:.2f})",
            'score': min(45, vb['edge'] * 2),
            'odd': float(vb['bet'].split('@')[1].strip())
        })
    
    for p in found[:2]:
        if p['type'] == '1X2':
            recs.append({'bet': f"{p['bet']} @ {p['odds']:.2f}", 'reason': f"💰 ROI {p['roi']:+.0f}%", 'score': min(40, p['roi'] * 2), 'odd': p['odds']})
        elif p['type'] == 'totals':
            recs.append({'bet': p['bet'], 'reason': f"📊 {p['real']:.0f}%", 'score': min(35, p['roi'] * 1.5), 'odd': 1.9})
        elif p['type'] == 'btts':
            recs.append({'bet': p['bet'], 'reason': f"📊 {p['real']:.0f}%", 'score': min(35, p['roi'] * 1.5), 'odd': 1.9})
    
    if result.get('form_home') and result['form_home']['winrate'] > 60:
        recs.append({'bet': f"П1 @ {match['h_odd']:.2f}" if match['h_odd'] else "П1", 'reason': f"🏠 Форма {result['form_home']['winrate']:.0f}%", 'score': 20, 'odd': match['h_odd'] or 1.5})
    if result.get('form_away') and result['form_away']['winrate'] > 60:
        recs.append({'bet': f"П2 @ {match['a_odd']:.2f}" if match['a_odd'] else "П2", 'reason': f"✈️ Форма {result['form_away']['winrate']:.0f}%", 'score': 20, 'odd': match['a_odd'] or 1.5})
    
    markets = match.get('markets', {})
    if result.get('h2h'):
        if '2.5' in markets.get('totals', {}):
            t = markets['totals']['2.5']
            if result['h2h']['over25_pct'] > 65 and 'over' in t:
                recs.append({'bet': f"ТБ 2.5 @ {t['over']:.2f}", 'reason': f"⚔️ H2H ТБ {result['h2h']['over25_pct']:.0f}%", 'score': 25, 'odd': t['over']})
            elif result['h2h']['over25_pct'] < 40 and 'under' in t:
                recs.append({'bet': f"ТМ 2.5 @ {t['under']:.2f}", 'reason': f"⚔️ H2H ТМ {100-result['h2h']['over25_pct']:.0f}%", 'score': 25, 'odd': t['under']})
    
    recs.sort(key=lambda x: x['score'], reverse=True)
    result['recommendations'] = recs[:5]
    return result

def generate_express(analyses, min_matches=2, max_matches=4):
    express_candidates = []
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
    for size in range(min_matches, min(max_matches+1, len(express_candidates)+1)):
        sorted_cands = sorted(express_candidates, key=lambda x: x['score'], reverse=True)[:size+3]
        for combo in combinations(sorted_cands, size):
            total_odd = 1
            total_score = 0
            for c in combo:
                total_odd *= c['odd']
                total_score += c['score']
            avg_score = total_score / size
            if avg_score >= 30: risk = "🟢 Умеренный"
            elif avg_score >= 20: risk = "🟡 Средний"
            else: risk = "🔴 Высокий"
            express_list.append({
                'matches': [c['match'] for c in combo],
                'bets': [c['bet'] for c in combo],
                'total_odd': total_odd,
                'avg_score': avg_score,
                'risk': risk,
                'size': size
            })
    
    express_list.sort(key=lambda x: (x['total_odd'] * x['avg_score'] / 100), reverse=True)
    return express_list[:3]

def generate_systems(analyses):
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
    system_configs = [(2, 3), (2, 4), (3, 4), (3, 5), (4, 5)]
    
    for k, m in system_configs:
        if m > n: continue
        top_m = sorted(candidates, key=lambda x: x['score'], reverse=True)[:m]
        total_combos = 0
        total_cost = 0
        total_payout = 0
        for combo in combinations(top_m, k):
            total_combos += 1
            combo_odd = 1
            for c in combo:
                combo_odd *= c['odd']
            total_cost += 1
            total_payout += combo_odd
        avg_odd_per_combo = total_payout / total_combos
        expected_roi = (avg_odd_per_combo - total_combos) / total_combos * 100
        systems.append({
            'name': f"Система {k} из {m}",
            'events': [c['match'] for c in top_m],
            'bets': [c['bet'] for c in top_m],
            'combos': total_combos,
            'cost': total_cost,
            'max_payout': max(prod([c['odd'] for c in combo]) for combo in combinations(top_m, k)),
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
    
    for i, a in enumerate(analyses, 1):
        m = a['match']
        home_ru = translate_team(m['home'])
        away_ru = translate_team(m['away'])
        
        lines.append(f"<b>{i}. {home_ru} vs {away_ru}</b>")
        if m['league'] and m['league'] != 'N/A':
            lines.append(f"🏆 {m['league']}")
        
        if m['h_odd'] and m['d_odd'] and m['a_odd']:
            inv = 1/m['h_odd'] + 1/m['d_odd'] + 1/m['a_odd']
            margin = (inv - 1) * 100
            fh = (1/m['h_odd']/inv)*100
            fd = (1/m['d_odd']/inv)*100
            fa = (1/m['a_odd']/inv)*100
            lines.append(f"💰 П1: {m['h_odd']:.2f} | Х: {m['d_odd']:.2f} | П2: {m['a_odd']:.2f} | Маржа: {margin:.1f}%")
            lines.append(f"🎯 Fair: П1 {fh:.0f}% | Х {fd:.0f}% | П2 {fa:.0f}%")
        elif m['h_odd']:
            lines.append(f"💰 Кэф: {m['h_odd']:.2f}")
        
        if a.get('xg'):
            xg = a['xg']
            lines.append(f"⚽ <b>xG:</b> {xg['home_xg']} - {xg['away_xg']} (Тотал: {xg['total_xg']})")
        
        if a.get('predictions'):
            pred = a['predictions']
            lines.append(f"📊 Прогноз: П1 {pred['П1']:.0f}% | Х {pred['Х']:.0f}% | П2 {pred['П2']:.0f}%")
            lines.append(f"📈 ТБ 2.5: {pred['ТБ 2.5']:.0f}% | ОЗ: {pred['ОЗ Да']:.0f}%")
        
        if a.get('exact_scores'):
            scores_str = " | ".join([f"{s}: {d['probability']:.0f}%" for s, d in a['exact_scores'][:3]])
            lines.append(f"🎯 Точный счёт: {scores_str}")
        
        markets = m.get('markets', {})
        if markets.get('totals'):
            parts = []
            for v, d in list(markets['totals'].items())[:2]:
                over_s = f"ТБ {d.get('over', 0):.2f}" if 'over' in d else ""
                under_s = f"ТМ {d.get('under', 0):.2f}" if 'under' in d else ""
                parts.append(f"Т{v}: {'/'.join(filter(None, [over_s, under_s]))}")
            if parts:
                lines.append(f"📊 Тоталы: {' | '.join(parts)}")
        
        if markets.get('foras'):
            foras_str = " | ".join([f"Ф{k}: {d['f1']:.2f}/{d['f2']:.2f}" for k, d in list(markets['foras'].items())[:2]])
            lines.append(f"📈 Форы: {foras_str}")
        
        if markets.get('btts'):
            btts = markets['btts']
            lines.append(f"⚽ ОЗ: Да {btts.get('yes', 0):.2f} / Нет {btts.get('no', 0):.2f}")
        
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
    
    if express_list:
        lines.append("=" * 40)
        lines.append("🎰 <b>ЭКСПРЕССЫ</b>")
        lines.append("=" * 40)
        for i, exp in enumerate(express_list, 1):
            lines.append(f"\n<b>Экспресс #{i}</b> ({exp['size']} событий) | {exp['risk']}")
            lines.append(f"💰 Итоговый кэф: <b>{exp['total_odd']:.2f}</b>")
            for j, (match, bet) in enumerate(zip(exp['matches'], exp['bets']), 1):
                lines.append(f"  {j}. {match} → {bet}")
            lines.append("")
    
    if systems_list:
        lines.append("=" * 40)
        lines.append("🎯 <b>СИСТЕМЫ</b>")
        lines.append("=" * 40)
        for sys in systems_list[:3]:
            lines.append(f"\n<b>{sys['name']}</b>")
            lines.append(f"📋 Комбинаций: {sys['combos']} | Стоимость: {sys['cost']} ед.")
            lines.append(f"💰 Макс. выплата: {sys['max_payout']:.2f}")
            lines.append(f"📈 Ожидаемый ROI: {sys['expected_roi']:+.0f}%")
            lines.append("События:")
            for j, (match, bet) in enumerate(zip(sys['events'], sys['bets']), 1):
                lines.append(f"  {j}. {match} → {bet}")
            lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    test_text = """Нортерн Тайгерс
Далвич Хилл
10
10
1.48
М3.5Б
2.39
1Т 33'
+69
Кантербери Банкстоун
Централ Коаст Маринерс (мол)
00
00
1.70
М3.5Б
2.00
1Т 1'
+69
Херствиль
Хиллс Юнайтед Брамбис
00
00
1.95
М2.5Б
1.75
1Т 7'
+69
Интер Лайонс
Ньюкасл Джетс (мол)
00
00
1.54
М3.5Б
2.26"""
    
    matches = parse_bookmaker_text(test_text)
    print(f"\n✅ Найдено {len(matches)} матчей:\n")
    print("=" * 60)
    for m in matches:
        print(f"🏆 {m['league']}")
        print(f"⚽ {m['home']} vs {m['away']}")
        if m['h_odd'] and m['d_odd'] and m['a_odd']:
            print(f"💰 1X2: {m['h_odd']}/{m['d_odd']}/{m['a_odd']}")
        elif m['h_odd']:
            print(f"💰 Кэф: {m['h_odd']}")
        totals = m.get('markets', {}).get('totals', {})
        if totals:
            for v, d in totals.items():
                parts = []
                if "over" in d: parts.append(f"ТБ {d['over']:.2f}")
                if "under" in d: parts.append(f"ТМ {d['under']:.2f}")
                print(f"📊 Тотал {v}: {' | '.join(parts)}")
        print("-" * 60)
