import os
from datetime import datetime
from teams_ru import translate_team

def load_matches():
    matches = []
    files = ['FIN.csv', 'POL.csv', 'TU1.csv', 'SC1.csv', 'B1.csv', 'G1.csv', 'P1.csv']
    
    for fname in files:
        if not os.path.exists(fname): continue
        league = fname.replace('.csv','')
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            f.seek(0)
            
            has_header = 'HomeTeam' in first_line or 'Home' in first_line
            
            for line in f:
                p = line.strip().split(',')
                if len(p) < 10: continue
                
                try:
                    if has_header:
                        idx = {h.strip(): i for i, h in enumerate(first_line.split(','))}
                        hi = idx.get('HomeTeam') or idx.get('Home')
                        ai = idx.get('AwayTeam') or idx.get('Away')
                        ri = idx.get('FTR')
                        di = idx.get('Date')
                        bh = idx.get('B365H')
                        bd = idx.get('B365D')
                        ba = idx.get('B365A')
                        hg_idx = idx.get('FTHG')
                        ag_idx = idx.get('FTAG')
                        
                        if hi is None or ai is None: continue
                        
                        home_orig = p[hi].strip()
                        away_orig = p[ai].strip()
                        
                        if not home_orig or not away_orig: continue
                        
                        date_str = p[di].strip() if di is not None else 'N/A'
                        res = p[ri].strip() if ri is not None and p[ri].strip() else None
                        hg = int(p[hg_idx]) if hg_idx is not None and p[hg_idx] else 0
                        ag = int(p[ag_idx]) if ag_idx is not None and p[ag_idx] else 0
                        h_odd = float(p[bh]) if bh is not None and p[bh] else None
                        d_odd = float(p[bd]) if bd is not None and p[bd] else None
                        a_odd = float(p[ba]) if ba is not None and p[ba] else None
                    else:
                        # Формат без заголовков (G1, RUS)
                        # Пропускаем — слишком сложно парсить кэфы
                        continue
                    
                    # Проверяем валидность кэфов
                    if h_odd and d_odd and a_odd:
                        inv = 1/h_odd + 1/d_odd + 1/a_odd
                        margin = (inv - 1) * 100
                        # Маржа должна быть 0-15%
                        if margin < 0 or margin > 15:
                            h_odd = d_odd = a_odd = None
                    
                    matches.append({
                        'date': date_str,
                        'home': home_orig,
                        'away': away_orig,
                        'home_lower': home_orig.lower(),
                        'away_lower': away_orig.lower(),
                        'res': res,
                        'h_odd': h_odd,
                        'd_odd': d_odd,
                        'a_odd': a_odd,
                        'hg': hg,
                        'ag': ag,
                        'total': hg + ag,
                        'league': league
                    })
                except: pass
    return matches

def normalize_team(name):
    return name.lower().strip()

def analyze_team_form(matches, team, last_n=10):
    team_norm = normalize_team(team)
    team_matches = [m for m in matches if team_norm in m['home_lower'] or team_norm in m['away_lower'] and m['res']][-last_n:]
    
    if not team_matches:
        return None
    
    wins = sum(1 for m in team_matches if (m['home_lower']==team_norm and m['res']=='H') or (m['away_lower']==team_norm and m['res']=='A'))
    draws = sum(1 for m in team_matches if m['res']=='D')
    losses = len(team_matches) - wins - draws
    
    return {
        'matches': len(team_matches),
        'wins': wins,
        'draws': draws,
        'losses': losses,
        'winrate': wins / len(team_matches) * 100,
    }

def analyze_h2h(matches, home, away):
    home_norm = normalize_team(home)
    away_norm = normalize_team(away)
    
    h2h = [m for m in matches if m['res'] and
           ((m['home_lower']==home_norm and m['away_lower']==away_norm) or 
            (m['home_lower']==away_norm and m['away_lower']==home_norm))]
    
    if len(h2h) < 2:
        return None
    
    hw = sum(1 for m in h2h if (m['home_lower']==home_norm and m['res']=='H') or (m['away_lower']==home_norm and m['res']=='A'))
    aw = sum(1 for m in h2h if (m['home_lower']==away_norm and m['res']=='H') or (m['away_lower']==away_norm and m['res']=='A'))
    
    return {
        'matches': len(h2h),
        'home_wins': hw,
        'away_wins': aw,
    }

def find_value_patterns(matches, min_sample=30, min_edge=10):
    ranges = {}
    for m in matches:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1 and m['res']:
            key = (round(m['h_odd'],1), round(m['d_odd'],1), round(m['a_odd'],1))
            if key not in ranges: ranges[key] = []
            ranges[key].append(m)
    
    patterns = []
    for (h,d,a), group in ranges.items():
        if len(group) < min_sample: continue
        inv = 1/h + 1/d + 1/a
        fh,fd,fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
        hw = sum(1 for m in group if m['res']=='H')/len(group)*100
        dw = sum(1 for m in group if m['res']=='D')/len(group)*100
        aw = sum(1 for m in group if m['res']=='A')/len(group)*100
        
        if hw - fh >= min_edge:
            patterns.append({'range':(h,d,a),'bet':'П1','odds':h,'edge':hw-fh,'roi':(hw/100*h-1)*100,'n':len(group)})
        if dw - fd >= min_edge:
            patterns.append({'range':(h,d,a),'bet':'Ничья','odds':d,'edge':dw-fd,'roi':(dw/100*d-1)*100,'n':len(group)})
        if aw - fa >= min_edge:
            patterns.append({'range':(h,d,a),'bet':'П2','odds':a,'edge':aw-fa,'roi':(aw/100*a-1)*100,'n':len(group)})
    
    patterns.sort(key=lambda x: x['roi'], reverse=True)
    return patterns

def check_value_match(match, patterns, tolerance=0.15):
    if not match['h_odd'] or not match['d_odd'] or not match['a_odd']:
        return None
    
    h, d, a = match['h_odd'], match['d_odd'], match['a_odd']
    
    for p in patterns:
        ph, pd, pa = p['range']
        if abs(h-ph) <= tolerance and abs(d-pd) <= tolerance and abs(a-pa) <= tolerance:
            return p
    
    return None

def generate_recommendation(match, matches, patterns):
    home_form = analyze_team_form(matches, match['home'], last_n=10)
    away_form = analyze_team_form(matches, match['away'], last_n=10)
    h2h = analyze_h2h(matches, match['home'], match['away'])
    value = check_value_match(match, patterns)
    
    if not home_form or not away_form:
        return None
    
    score = 0
    reasons = []
    bet = "Пропустить"
    
    if value:
        score += min(40, value['roi'] * 2)
        reasons.append(f"💰 Валуй {value['bet']} (ROI {value['roi']:+.0f}%, N={value['n']})")
        bet = f"{value['bet']} @ {value['odds']:.2f}"
    
    if home_form['winrate'] > 60:
        score += 20
        reasons.append(f"🏠 Хозяева в форме ({home_form['winrate']:.0f}%)")
        if not value and match['h_odd']:
            bet = f"П1 @ {match['h_odd']:.2f}"
    elif home_form['winrate'] > 40:
        score += 10
    
    if away_form['winrate'] > 60:
        score += 20
        reasons.append(f"✈️ Гости в форме ({away_form['winrate']:.0f}%)")
        if not value and home_form['winrate'] <= 40 and match['a_odd']:
            bet = f"П2 @ {match['a_odd']:.2f}"
    elif away_form['winrate'] > 40:
        score += 10
    
    if h2h and h2h['matches'] >= 3:
        if h2h['home_wins'] > h2h['away_wins'] * 1.5:
            score += 15
            reasons.append(f"⚔️ H2H хозяева ({h2h['home_wins']}:{h2h['away_wins']})")
        elif h2h['away_wins'] > h2h['home_wins'] * 1.5:
            score += 15
            reasons.append(f"⚔️ H2H гости ({h2h['away_wins']}:{h2h['home_wins']})")
    
    score = round(score, 1)  # Округляем score
    
    if score >= 60: confidence = "🟢 ВЫСОКАЯ"
    elif score >= 40: confidence = "🟡 СРЕДНЯЯ"
    elif score >= 20: confidence = "🔵 НИЗКАЯ"
    else: confidence = "⚪ ОТСУТСТВУЕТ"
    
    home_ru = translate_team(match['home'])
    away_ru = translate_team(match['away'])
    
    return {
        'match': f"{home_ru} vs {away_ru}",
        'date': match['date'],
        'league': match['league'],
        'score': score,
        'confidence': confidence,
        'bet': bet,
        'reasons': reasons,
        'result': match['res']
    }

def main():
    print("🔍 Загрузка базы...")
    matches = load_matches()
    print(f"✅ {len(matches)} матчей\n")
    
    print("📊 Поиск валуйных паттернов...")
    patterns = find_value_patterns(matches, min_sample=30, min_edge=10)
    print(f"✅ {len(patterns)} паттернов\n")
    
    print("🎯 ТОП-5 РАБОЧИХ ПАТТЕРНОВ:")
    print("-" * 70)
    for i, p in enumerate(patterns[:5], 1):
        print(f"  {i}. {p['bet']} @ {p['odds']:.1f} | ROI {p['roi']:+.0f}% | N={p['n']} | Кэфы: {p['range'][0]}/{p['range'][1]}/{p['range'][2]}")
    print()
    
    future = [m for m in matches if not m['res'] and m['home'] and m['h_odd']]
    
    if future:
        print(f"🎯 АНАЛИЗ {len(future)} БУДУЩИХ МАТЧЕЙ")
        print("=" * 90)
        to_analyze = future[:50]
    else:
        print("⚠️ Будущих матчей с кэфами нет.")
        print("📋 Анализирую последние 20 сыгранных матчей...\n")
        to_analyze = [m for m in matches if m['res'] and m['h_odd']][-20:]
    
    recommendations = []
    
    for m in to_analyze:
        rec = generate_recommendation(m, matches, patterns)
        if rec and rec['score'] >= 20:
            recommendations.append(rec)
    
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    print("=" * 90)
    print("🏆 РЕКОМЕНДАЦИИ")
    print("=" * 90)
    
    if not recommendations:
        print("❌ Рекомендаций не найдено")
    else:
        for i, rec in enumerate(recommendations[:15], 1):
            result_str = f" | Результат: {rec['result']}" if rec['result'] else ""
            print(f"\n{i}. {rec['confidence']} | Score: {rec['score']}/100")
            print(f"   📅 {rec['date']} | {rec['league']}{result_str}")
            print(f"   ⚽ {rec['match']}")
            print(f"   💡 Ставка: {rec['bet']}")
            if rec['reasons']:
                for r in rec['reasons']:
                    print(f"      • {r}")
    
    print("\n" + "=" * 90)
    
    # Статистика
    played = [m for m in matches if m['res'] and m['h_odd']][-100:]
    value_wins = 0
    value_total = 0
    for m in played:
        value = check_value_match(m, patterns)
        if value:
            value_total += 1
            bet_res = {'П1': 'H', 'Ничья': 'D', 'П2': 'A'}[value['bet']]
            if m['res'] == bet_res:
                value_wins += 1
    
    if value_total > 0:
        print(f"\n📊 Проверка на последних 100 матчах:")
        print(f"   Валуйных ставок: {value_total}")
        print(f"   Выигрышей: {value_wins} ({value_wins/value_total*100:.0f}%)")
    
    with open('recommendations.txt', 'w', encoding='utf-8') as f:
        f.write(f"Рекомендации {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
        f.write("=" * 90 + "\n\n")
        for rec in recommendations:
            f.write(f"{rec['confidence']} | Score: {rec['score']}/100\n")
            f.write(f"{rec['date']} | {rec['league']} | {rec['match']}\n")
            f.write(f"Ставка: {rec['bet']}\n")
            if rec['reasons']:
                f.write("Причины:\n")
                for r in rec['reasons']:
                    f.write(f"  • {r}\n")
            f.write("\n")
    
    print(f"💾 Результаты в recommendations.txt")

if __name__ == "__main__":
    main()
