import os
from datetime import datetime

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

def find_patterns(matches, min_sample=30, min_edge=7):
    """Ищет паттерны с edge >= min_edge%"""
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

def backtest(matches, patterns, tolerance=0.15, stake=100):
    bank = 10000
    start_bank = bank
    bets = []
    bank_history = [bank]
    
    for m in matches:
        if not m['res'] or not m['h_odd'] or not m['d_odd'] or not m['a_odd']:
            continue
        
        h, d, a = m['h_odd'], m['d_odd'], m['a_odd']
        
        for (ph,pd,pa), (bet_name, bet_res, real_pct, fair_pct, roi, sample) in patterns.items():
            if abs(h-ph) <= tolerance and abs(d-pd) <= tolerance and abs(a-pa) <= tolerance:
                odds = {'П1': h, 'Ничья': d, 'П2': a}[bet_name]
                won = m['res'] == bet_res
                profit = stake * (odds - 1) if won else -stake
                bank += profit
                
                bets.append({
                    'match': f"{m['home']} vs {m['away']}",
                    'league': m['league'],
                    'bet': f"{bet_name} @ {odds:.2f}",
                    'result': m['res'],
                    'won': won,
                    'profit': profit,
                    'bank': bank
                })
                bank_history.append(bank)
                break
    
    total_bets = len(bets)
    wins = sum(1 for b in bets if b['won'])
    losses = total_bets - wins
    total_profit = bank - start_bank
    roi = (total_profit / (total_bets * stake)) * 100 if total_bets > 0 else 0
    
    peak = start_bank
    max_dd = 0
    for b in bank_history:
        if b > peak: peak = b
        dd = (peak - b) / peak * 100
        if dd > max_dd: max_dd = dd
    
    return {
        'bets': bets,
        'total': total_bets,
        'wins': wins,
        'losses': losses,
        'winrate': wins/total_bets*100 if total_bets > 0 else 0,
        'profit': total_profit,
        'roi': roi,
        'bank': bank,
        'max_drawdown': max_dd,
        'bank_history': bank_history
    }

def main():
    print("🔍 Загрузка базы...")
    matches = load_matches()
    print(f"✅ {len(matches)} матчей\n")
    
    # Тестируем разные пороги edge
    for min_edge in [5, 7, 8, 10]:
        print(f"📊 Edge >= {min_edge}%")
        patterns = find_patterns(matches, min_sample=30, min_edge=min_edge)
        print(f"   Паттернов: {len(patterns)}")
        
        if not patterns:
            print("   ❌ Нет паттернов\n")
            continue
        
        result = backtest(matches, patterns, tolerance=0.15, stake=100)
        
        print(f"   Ставок: {result['total']} | ROI: {result['roi']:+.1f}% | Прибыль: {result['profit']:+.0f}₽ | Просадка: {result['max_drawdown']:.1f}%")
        
        if result['roi'] > 5:
            print(f"   🟢 ОТЛИЧНО!")
        elif result['roi'] > 2:
            print(f"   🟡 Хорошо")
        elif result['roi'] > 0:
            print(f"   🔵 Слабый плюс")
        else:
            print(f"   ❌ Убыток")
        print()

if __name__ == "__main__":
    main()
