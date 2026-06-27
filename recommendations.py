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
            header = f.readline().strip().split(',')
            if not header: continue
            idx = {h.strip(): i for i, h in enumerate(header)}
            
            if 'HomeTeam' in idx:
                hi, ai, ri = idx.get('HomeTeam'), idx.get('AwayTeam'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
                hg_idx, ag_idx = idx.get('FTHG'), idx.get('FTAG')
                di = idx.get('Date')
            elif 'Home' in idx:
                hi, ai, ri = idx.get('Home'), idx.get('Away'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
                hg_idx, ag_idx = idx.get('FTHG'), idx.get('FTAG')
                di = idx.get('Date')
            else:
                hi, ai, ri, di = 5, 6, 9, 3
                bh, bd, ba = 10, 11, 12
                hg_idx, ag_idx = 7, 8
            
            if hi is None or ai is None: continue
            
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai): continue
                try:
                    hg = int(p[hg_idx]) if hg_idx is not None and len(p) > hg_idx and p[hg_idx] else 0
                    ag = int(p[ag_idx]) if ag_idx is not None and len(p) > ag_idx and p[ag_idx] else 0
                    date_str = p[di].strip() if di is not None and len(p) > di else 'N/A'
                    res = p[ri].strip() if ri is not None and len(p) > ri and p[ri].strip() else None
                    h_odd = float(p[bh]) if bh is not None and len(p) > bh and p[bh] else None
                    d_odd = float(p[bd]) if bd is not None and len(p) > bd and p[bd] else None
                    a_odd = float(p[ba]) if ba is not None and len(p) > ba and p[ba] else None
                    
                    matches.append({
                        'date': date_str,
                        'home': p[hi].strip().lower(),
                        'away': p[ai].strip().lower(),
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
    name = name.lower().strip()
    return name

def analyze_team_form(matches, team, last_n=10):
    team_norm = normalize_team(team)
    team_matches = [m for m in matches if team_norm in normalize_team(m['home']) or team_norm in normalize_team(m['away'])][-last_n:]
    
    if not team_matches:
        return None
    
    wins = sum(1 for m in team_matches if (normalize_team(m['home'])==team_norm and m['res']=='H') or (normalize_team(m['away'])==team_norm and m['res']=='A'))
    draws = sum(1 for m in team_matches if m['res']=='D')
    losses = len(team_matches) - wins - draws
    
    goals_for = sum(m['hg'] if normalize_team(m['home'])==team_norm else m['ag'] for m in team_matches)
    goals_against = sum(m['ag'] if normalize_team(m['home'])==team_norm else m['hg'] for m in team_matches)
    
    return {
        'matches': len(team_matches),
        'wins': wins,
        'draws': draws,
        'losses': losses,
        'winrate': wins / len(team_matches) * 100,
        'goals_for': goals_for,
        'goals_against': goals_against,
        'avg_goals_for': goals_for / len(team_matches),
        'avg_goals_against': goals_against / len(team_matches)
    }

def analyze_h2h(matches, home, away):
    home_norm = normalize_team(home)
    away_norm = normalize_team(away)
    
    h2h = [m for m in matches 
           if (normalize_team(m['home'])==home_norm and normalize_team(m['away'])==away_norm) or 
              (normalize_team(m['home'])==away_norm and normalize_team(m['away'])==home_norm)]
    
    if len(h2h) < 2:
        return None
    
    hw = sum(1 for m in h2h if (normalize_team(m['home'])==home_norm and m['res']=='H') or (normalize_team(m['away'])==home_norm and m['res']=='A'))
    aw = sum(1 for m in h2h if (normalize_team(m['home'])==away_norm and m['res']=='H') or (normalize_team(m['away'])==away_norm and m['res']=='A'))
    dr = sum(1 for m in h2h if m['res']=='D')
    
    total_goals = sum(m['total'] for m in h2h)
    over25 = sum(1 for m in h2h if m['total'] > 2.5)
    btts = sum(1 for m in h2h if m['hg'] > 0 and m['ag'] > 0)
    
    return {
        'matches': len(h2h),
        'home_wins': hw,
        'away_wins': aw,
        'draws': dr,
        'avg_goals': total_goals / len(h2h),
        'over25_pct': over25 / len(h2h) * 100,
        'btts_pct': btts / len(h2h) * 100
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
            patterns.append({'range':(h,d,a),'bet':'П1','odds':h,'edge':hw-fh,'roi':(hw/100*h-1)*100})
        if dw - fd >= min_edge:
            patterns.append({'range':(h,d,a),'bet':'Ничья','odds':d,'edge':dw-fd,'roi':(dw/100*d-1)*100})
        if aw - fa >= min_edge:
            patterns.append({'range':(h,d,a),'bet':'П2','odds':a,'edge':aw-fa,'roi':(aw/100*a-1)*100})
    
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

def generate_recommendation(match, matches, patterns, debug=False):
    home_form = analyze_team_form(matches, match['home'], last_n=10)
    away_form = analyze_team_form(matches, match['away'], last_n=10)
    h2h = analyze_h2h(matches, match['home'], match['away'])
    value = check_value_match(match, patterns)
    
    if not home_form or not away_form:
        if debug:
            print(f"   ⚠️ Нет данных о форме команд")
        return None
    
    score = 0
    reasons = []
    bet = "Пропустить"
    
    if value:
        score += min(40, value['roi'] * 2)
        reasons.append(f"💰 Валуй {value['bet']} (ROI {value['roi']:+.0f}%)")
        bet = f"{value['bet']} @ {value['odds']:.2f}"
    
    if home_form['winrate'] > 60:
        score += 20
        reasons.append(f"🏠 Хозяева в форме ({home_form['winrate']:.0f}% побед)")
        if not value and match['h_odd']:
            bet = f"П1 @ {match['h_odd']:.2f}"
    elif home_form['winrate'] > 40:
        score += 10
    
    if away_form['winrate'] > 60:
        score += 20
        reasons.append(f"✈️ Гости в форме ({away_form['winrate']:.0f}% побед)")
        if not value and home_form['winrate'] <= 40 and match['a_odd']:
            bet = f"П2 @ {match['a_odd']:.2f}"
    elif away_form['winrate'] > 40:
        score += 10
    
    if h2h and h2h['matches'] >= 3:
        if h2h['home_wins'] > h2h['away_wins'] * 1.5:
            score += 15
            reasons.append(f"⚔️ Хозяева доминируют в H2H ({h2h['home_wins']}:{h2h['away_wins']})")
            if not value and home_form['winrate'] <= 40 and match['h_odd']:
                bet = f"П1 @ {match['h_odd']:.2f}"
        elif h2h['away_wins'] > h2h['home_wins'] * 1.5:
            score += 15
            reasons.append(f"⚔️ Гости доминируют в H2H ({h2h['away_wins']}:{h2h['home_wins']})")
            if not value and away_form['winrate'] <= 40 and match['a_odd']:
                bet = f"П2 @ {match['a_odd']:.2f}"
    
    if score >= 60:
        confidence = "🟢 ВЫСОКАЯ"
    elif score >= 40:
        confidence = "🟡 СРЕДНЯЯ"
    elif score >= 20:
        confidence = "🔵 НИЗКАЯ"
    else:
        confidence = "⚪ ОТСУТСТВУЕТ"
    
    # Переводим названия команд
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
        'home_form': home_form,
        'away_form': away_form,
        'h2h': h2h
    }

def main():
    print("🔍 Загрузка базы...")
    matches = load_matches()
    print(f"✅ {len(matches)} матчей\n")
    
    print("📊 Поиск валуйных паттернов...")
    patterns = find_value_patterns(matches, min_sample=30, min_edge=10)
    print(f"✅ {len(patterns)} паттернов\n")
    
    future = [m for m in matches if not m['res']]
    
    if future:
        print(f"🎯 Анализ {len(future)} будущих матчей...\n")
        to_analyze = future[:50]
    else:
        print("⚠️ Будущих матчей нет. Анализирую последние 50 сыгранных...\n")
        to_analyze = [m for m in matches if m['res']][-50:]
    
    recommendations = []
    
    for m in to_analyze:
        rec = generate_recommendation(m, matches, patterns, debug=False)
        if rec and rec['score'] >= 20:
            recommendations.append(rec)
    
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    print("=" * 90)
    print("🏆 ТОП РЕКОМЕНДАЦИЙ")
    print("=" * 90)
    
    if not recommendations:
        print("❌ Рекомендаций не найдено")
    else:
        for i, rec in enumerate(recommendations[:15], 1):
            print(f"\n{i}. {rec['confidence']} | Score: {rec['score']}/100")
            print(f"   📅 {rec['date']} | {rec['league']}")
            print(f"   ⚽ {rec['match']}")
            print(f"   💡 Ставка: {rec['bet']}")
            if rec['reasons']:
                print(f"   📊 Причины:")
                for r in rec['reasons']:
                    print(f"      • {r}")
    
    print("\n" + "=" * 90)
    
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
