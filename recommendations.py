import os
from datetime import datetime
from teams_ru import translate_team

# ВСЕ 14 лиг
LEAGUE_FILES = [
    'FIN.csv', 'POL.csv', 'TU1.csv', 'SC1.csv', 'B1.csv', 'G1.csv', 'P1.csv',
    'E0.csv', 'E1.csv', 'D1.csv', 'SP1.csv', 'I1.csv', 'N1.csv', 'RUS.csv'
]

LEAGUE_NAMES = {
    'FIN': 'Финляндия', 'POL': 'Польша', 'TU1': 'Турция',
    'SC1': 'Шотландия Ч', 'B1': 'Бельгия', 'G1': 'Греция', 'P1': 'Португалия',
    'E0': 'АПЛ', 'E1': 'Чемпионшип', 'D1': 'Бундеслига',
    'SP1': 'Ла Лига', 'I1': 'Серия А', 'N1': 'Эредивизи', 'RUS': 'РПЛ'
}

def load_matches():
    matches = []
    for fname in LEAGUE_FILES:
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
                        ftr_pos = None
                        for i, val in enumerate(p):
                            v = val.strip()
                            if v in ('H', 'D', 'A') and i >= 5:
                                try:
                                    int(p[i-2]); int(p[i-1])
                                    ftr_pos = i
                                    break
                                except:
                                    continue
                        if ftr_pos is None: continue
                        hg = int(p[ftr_pos-2]) if p[ftr_pos-2] else 0
                        ag = int(p[ftr_pos-1]) if p[ftr_pos-1] else 0
                        res = p[ftr_pos].strip()
                        home_orig = p[ftr_pos-4].strip()
                        away_orig = p[ftr_pos-3].strip()
                        if not home_orig or not away_orig: continue
                        date_str = p[ftr_pos-6].strip() if ftr_pos >= 6 else 'N/A'
                        h_odd = d_odd = a_odd = None
                        for i in range(ftr_pos+1, min(len(p)-2, ftr_pos+30)):
                            try:
                                h_val = float(p[i]) if p[i] else 0
                                d_val = float(p[i+1]) if p[i+1] else 0
                                a_val = float(p[i+2]) if p[i+2] else 0
                                if 1.01 <= h_val <= 50 and 1.01 <= d_val <= 50 and 1.01 <= a_val <= 50:
                                    h_odd = h_val; d_odd = d_val; a_odd = a_val
                                    break
                            except:
                                continue
                    
                    matches.append({
                        'date': date_str, 'home': home_orig, 'away': away_orig,
                        'home_lower': home_orig.lower(), 'away_lower': away_orig.lower(),
                        'res': res,
                        'h_odd': h_odd, 'd_odd': d_odd, 'a_odd': a_odd,
                        'hg': hg, 'ag': ag, 'total': hg + ag,
                        'league': league
                    })
                except: pass
    return matches

def normalize_team(name):
    return name.lower().strip()

def analyze_team_form(matches, team, last_n=10):
    team_norm = normalize_team(team)
    team_matches = [m for m in matches if (team_norm in m['home_lower'] or team_norm in m['away_lower']) and m['res']][-last_n:]
    if not team_matches: return None
    wins = sum(1 for m in team_matches if (m['home_lower']==team_norm and m['res']=='H') or (m['away_lower']==team_norm and m['res']=='A'))
    draws = sum(1 for m in team_matches if m['res']=='D')
    losses = len(team_matches) - wins - draws
    goals_for = sum(m['hg'] if m['home_lower']==team_norm else m['ag'] for m in team_matches)
    goals_against = sum(m['ag'] if m['home_lower']==team_norm else m['hg'] for m in team_matches)
    return {
        'matches': len(team_matches), 'wins': wins, 'draws': draws, 'losses': losses,
        'winrate': wins / len(team_matches) * 100,
        'avg_gf': goals_for / len(team_matches),
        'avg_ga': goals_against / len(team_matches),
    }

def analyze_h2h(matches, home, away):
    home_norm = normalize_team(home)
    away_norm = normalize_team(away)
    h2h = [m for m in matches if m['res'] and
           ((m['home_lower']==home_norm and m['away_lower']==away_norm) or 
            (m['home_lower']==away_norm and m['away_lower']==home_norm))]
    if len(h2h) < 2: return None
    hw = sum(1 for m in h2h if (m['home_lower']==home_norm and m['res']=='H') or (m['away_lower']==home_norm and m['res']=='A'))
    aw = sum(1 for m in h2h if (m['home_lower']==away_norm and m['res']=='H') or (m['away_lower']==away_norm and m['res']=='A'))
    dr = sum(1 for m in h2h if m['res']=='D')
    totals = [m['total'] for m in h2h]
    over25 = sum(1 for t in totals if t > 2.5)
    btts = sum(1 for m in h2h if m['hg'] > 0 and m['ag'] > 0)
    return {
        'matches': len(h2h), 'home_wins': hw, 'away_wins': aw, 'draws': dr,
        'over25_pct': over25 / len(h2h) * 100,
        'btts_pct': btts / len(h2h) * 100,
        'avg_total': sum(totals) / len(totals),
    }

def find_patterns(matches, min_sample=30, min_edge=10):
    patterns = {'1X2': [], 'totals': [], 'btts': []}
    ranges_1x2 = {}
    for m in matches:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1 and m['res']:
            key = (round(m['h_odd'],1), round(m['d_odd'],1), round(m['a_odd'],1))
            if key not in ranges_1x2: ranges_1x2[key] = []
            ranges_1x2[key].append(m)
    
    for (h,d,a), group in ranges_1x2.items():
        if len(group) < min_sample: continue
        inv = 1/h + 1/d + 1/a
        fh,fd,fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
        hw = sum(1 for m in group if m['res']=='H')/len(group)*100
        dw = sum(1 for m in group if m['res']=='D')/len(group)*100
        aw = sum(1 for m in group if m['res']=='A')/len(group)*100
        if hw - fh >= min_edge:
            patterns['1X2'].append({'range':(h,d,a),'bet':'П1','odds':h,'fair':fh,'real':hw,'edge':hw-fh,'roi':(hw/100*h-1)*100,'n':len(group)})
        if dw - fd >= min_edge:
            patterns['1X2'].append({'range':(h,d,a),'bet':'Ничья','odds':d,'fair':fd,'real':dw,'edge':dw-fd,'roi':(dw/100*d-1)*100,'n':len(group)})
        if aw - fa >= min_edge:
            patterns['1X2'].append({'range':(h,d,a),'bet':'П2','odds':a,'fair':fa,'real':aw,'edge':aw-fa,'roi':(aw/100*a-1)*100,'n':len(group)})
    
    for (h,d,a), group in ranges_1x2.items():
        if len(group) < min_sample: continue
        totals = [m['total'] for m in group]
        over25 = sum(1 for t in totals if t > 2.5) / len(group) * 100
        btts = sum(1 for m in group if m['hg']>0 and m['ag']>0) / len(group) * 100
        if over25 > 55:
            patterns['totals'].append({'range':(h,d,a),'bet':'ТБ 2.5','real':over25,'n':len(group),'roi':(over25/100*1.9-1)*100})
        if over25 < 45:
            patterns['totals'].append({'range':(h,d,a),'bet':'ТМ 2.5','real':100-over25,'n':len(group),'roi':((100-over25)/100*1.9-1)*100})
        if btts > 55:
            patterns['btts'].append({'range':(h,d,a),'bet':'ОЗ Да','real':btts,'n':len(group),'roi':(btts/100*1.9-1)*100})
        if btts < 45:
            patterns['btts'].append({'range':(h,d,a),'bet':'ОЗ Нет','real':100-btts,'n':len(group),'roi':((100-btts)/100*1.9-1)*100})
    
    for key in patterns:
        patterns[key].sort(key=lambda x: x['roi'], reverse=True)
    return patterns

def check_patterns(match, patterns, tolerance=0.15):
    if not match['h_odd'] or not match['d_odd'] or not match['a_odd']: return []
    h, d, a = match['h_odd'], match['d_odd'], match['a_odd']
    found = []
    for ptype, plist in patterns.items():
        for p in plist:
            ph, pd, pa = p['range']
            if abs(h-ph) <= tolerance and abs(d-pd) <= tolerance and abs(a-pa) <= tolerance:
                found.append({**p, 'type': ptype})
    return found

if __name__ == "__main__":
    print("🔍 Загрузка базы (ВСЕ 14 лиг)...")
    matches = load_matches()
    print(f"✅ {len(matches)} матчей\n")
    
    leagues = {}
    for m in matches:
        if m['league'] not in leagues: leagues[m['league']] = 0
        leagues[m['league']] += 1
    
    print("📈 Матчей по лигам:")
    for league, count in sorted(leagues.items(), key=lambda x: x[1], reverse=True):
        name = LEAGUE_NAMES.get(league, league)
        print(f"  {league} ({name}): {count}")
    
    print("\n📊 Поиск паттернов...")
    patterns = find_patterns(matches, min_sample=30, min_edge=10)
    total = len(patterns['1X2']) + len(patterns['totals']) + len(patterns['btts'])
    print(f"✅ {total} паттернов (1X2: {len(patterns['1X2'])}, Тоталы: {len(patterns['totals'])}, ОЗ: {len(patterns['btts'])})")

def get_strategy_for_league(league):
    """Возвращает стратегию для лиги"""
    # Лиги, где работают паттерны по кэфам
    pattern_leagues = ['FIN', 'POL', 'TU1', 'SC1', 'B1', 'G1', 'P1']
    
    if league in pattern_leagues:
        return 'patterns'
    else:
        return 'xg'

def analyze_match_smart(match, all_matches, patterns=None):
    """Умный анализ — выбирает стратегию в зависимости от лиги"""
    league = match['league']
    strategy = get_strategy_for_league(league)
    
    if strategy == 'patterns' and patterns:
        # Используем паттерны
        from bookmaker_parser import analyze_match
        return analyze_match(match, all_matches, patterns)
    else:
        # Используем xG-стратегию
        from xg_strategy import analyze_match_xg
        return analyze_match_xg(match, all_matches)
