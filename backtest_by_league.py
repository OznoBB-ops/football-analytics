import os

def load_matches():
    matches = []
    files = ['RUS.csv','FIN.csv','POL.csv','P1.csv','E0.csv','E1.csv',
             'D1.csv','SP1.csv','I1.csv','N1.csv','B1.csv','TU1.csv','SC1.csv','G1.csv']
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
            elif 'Home' in idx:
                hi, ai, ri = idx.get('Home'), idx.get('Away'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
            else:
                hi, ai, ri = 5, 6, 9
                bh, bd, ba = 10, 11, 12
            if hi is None or ai is None or ri is None: continue
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai, ri): continue
                try:
                    matches.append({
                        'home': p[hi].strip().lower(),
                        'away': p[ai].strip().lower(),
                        'res': p[ri].strip() if p[ri].strip() else None,
                        'h_odd': float(p[bh]) if bh is not None and len(p) > bh and p[bh] else None,
                        'd_odd': float(p[bd]) if bd is not None and len(p) > bd and p[bd] else None,
                        'a_odd': float(p[ba]) if ba is not None and len(p) > ba and p[ba] else None,
                        'league': league
                    })
                except: pass
    return matches

def find_patterns(matches, min_sample=30, min_edge=10):
    ranges = {}
    for m in matches:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1 and m['res']:
            key = (round(m['h_odd'],1), round(m['d_odd'],1), round(m['a_odd'],1))
            if key not in ranges: ranges[key] = []
            ranges[key].append(m)
    patterns = {}
    for (h,d,a), group in ranges.items():
        if len(group) < min_sample: continue
        inv = 1/h + 1/d + 1/a
        fh,fd,fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
        hw = sum(1 for m in group if m['res']=='H')/len(group)*100
        dw = sum(1 for m in group if m['res']=='D')/len(group)*100
        aw = sum(1 for m in group if m['res']=='A')/len(group)*100
        if hw - fh >= min_edge: patterns[(h,d,a)] = ('П1', 'H', hw, fh, (hw/100*h-1)*100, len(group))
        if dw - fd >= min_edge: patterns[(h,d,a)] = ('Ничья', 'D', dw, fd, (dw/100*d-1)*100, len(group))
        if aw - fa >= min_edge: patterns[(h,d,a)] = ('П2', 'A', aw, fa, (aw/100*a-1)*100, len(group))
    return patterns

def backtest_league(league_matches, patterns, tolerance=0.15, stake=100):
    bank = 10000
    bets = 0
    wins = 0
    peak = bank
    max_dd = 0
    
    for m in league_matches:
        if not m['res'] or not m['h_odd'] or not m['d_odd'] or not m['a_odd']:
            continue
        h, d, a = m['h_odd'], m['d_odd'], m['a_odd']
        for (ph,pd,pa), (bet_name, bet_res, real_pct, fair_pct, roi, sample) in patterns.items():
            if abs(h-ph) <= tolerance and abs(d-pd) <= tolerance and abs(a-pa) <= tolerance:
                odds = {'П1': h, 'Ничья': d, 'П2': a}[bet_name]
                won = m['res'] == bet_res
                profit = stake * (odds - 1) if won else -stake
                bank += profit
                bets += 1
                if won: wins += 1
                if bank > peak: peak = bank
                dd = (peak - bank) / peak * 100
                if dd > max_dd: max_dd = dd
                break
    
    if bets == 0:
        return None
    
    return {
        'bets': bets,
        'wins': wins,
        'winrate': wins/bets*100,
        'profit': bank - 10000,
        'roi': (bank - 10000) / (bets * stake) * 100,
        'bank': bank,
        'max_dd': max_dd
    }

def main():
    print("🔍 Загрузка базы...")
    matches = load_matches()
    print(f"✅ {len(matches)} матчей\n")
    
    patterns = find_patterns(matches, min_sample=30, min_edge=10)
    print(f"📊 {len(patterns)} паттернов (edge >= 10%)\n")
    
    # Группируем по лигам
    leagues = {}
    for m in matches:
        if m['league'] not in leagues:
            leagues[m['league']] = []
        leagues[m['league']].append(m)
    
    print("=" * 80)
    print(f"{'Лига':<8} {'Ставок':>8} {'Win%':>8} {'ROI':>10} {'Прибыль':>12} {'Просадка':>10}")
    print("=" * 80)
    
    results = []
    for league, league_matches in sorted(leagues.items()):
        r = backtest_league(league_matches, patterns, tolerance=0.15, stake=100)
        if r:
            results.append((league, r))
            icon = "🟢" if r['roi'] > 5 else ("🟡" if r['roi'] > 0 else "❌")
            print(f"{icon} {league:<8} {r['bets']:>8} {r['winrate']:>7.1f}% {r['roi']:>+9.1f}% {r['profit']:>+11.0f}₽ {r['max_dd']:>9.1f}%")
    
    print("=" * 80)
    
    # Топ-3 лиги
    results.sort(key=lambda x: x[1]['roi'], reverse=True)
    print("\n🏆 ТОП-3 ЛИГИ:")
    for i, (league, r) in enumerate(results[:3], 1):
        print(f"  {i}. {league}: ROI {r['roi']:+.1f}%, {r['bets']} ставок, прибыль {r['profit']:+.0f}₽")
    
    print("\n❌ ХУДШИЕ ЛИГИ:")
    for league, r in results[-3:]:
        print(f"  • {league}: ROI {r['roi']:+.1f}%, {r['bets']} ставок")

if __name__ == "__main__":
    main()
