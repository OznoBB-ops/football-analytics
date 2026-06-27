"""
Расширенный бэктест по всем 14 лигам
Компактный вывод + диагностика
"""
from recommendations import load_matches, find_patterns, check_patterns
from collections import defaultdict

def backtest_by_league():
    matches = load_matches()
    by_league = defaultdict(list)
    for m in matches:
        if m['res'] and m['h_odd'] and m['d_odd'] and m['a_odd']:
            by_league[m['league']].append(m)
    
    results = []
    
    for league, league_matches in sorted(by_league.items()):
        # Паттерны на ВСЕЙ лиге (кроме последних 500)
        train = league_matches[:-500]
        test = league_matches[-500:]
        
        if len(train) < 100:
            continue
        
        patterns = find_patterns(train, min_sample=15, min_edge=5)
        total_patterns = len(patterns['1X2']) + len(patterns['totals']) + len(patterns['btts'])
        
        # Бэктест
        bets_count = 0
        wins = 0
        stake_total = 0
        payout_total = 0
        
        for m in test:
            found = check_patterns(m, patterns, tolerance=0.2)  # увеличил tolerance
            if not found:
                continue
            
            p = found[0]
            stake = 100
            bets_count += 1
            stake_total += stake
            
            won = False
            payout = 0
            
            if p['type'] == '1X2':
                if (p['bet'] == 'П1' and m['res'] == 'H') or \
                   (p['bet'] == 'Ничья' and m['res'] == 'D') or \
                   (p['bet'] == 'П2' and m['res'] == 'A'):
                    won = True
                    payout = stake * p['odds']
            elif p['type'] == 'totals':
                if ('ТБ 2.5' in p['bet'] and m['total'] > 2.5) or \
                   ('ТМ 2.5' in p['bet'] and m['total'] < 2.5):
                    won = True
                    payout = stake * 1.9
            elif p['type'] == 'btts':
                both = m['hg'] > 0 and m['ag'] > 0
                if ('ОЗ Да' in p['bet'] and both) or ('ОЗ Нет' in p['bet'] and not both):
                    won = True
                    payout = stake * 1.9
            
            if won:
                wins += 1
                payout_total += payout
        
        profit = payout_total - stake_total
        roi = (profit / stake_total * 100) if stake_total > 0 else 0
        winrate = (wins / bets_count * 100) if bets_count > 0 else 0
        
        results.append({
            'league': league,
            'total': len(league_matches),
            'patterns': total_patterns,
            'bets': bets_count,
            'wins': wins,
            'winrate': winrate,
            'roi': roi,
            'profit': profit
        })
    
    return results

def print_results(results):
    print("\n" + "="*70)
    print("📊 БЭКТЕСТ ПО ЛИГАМ (тест: последние 500 матчей)")
    print("="*70)
    
    # Компактная таблица
    print(f"\n{'Лига':<5} {'Матчей':>6} {'Патт':>5} {'Ставок':>6} {'Win%':>5} {'ROI':>7} {'P&L':>8}")
    print("-"*70)
    
    for r in sorted(results, key=lambda x: x['roi'], reverse=True):
        emoji = "🟢" if r['roi'] > 5 else "🟡" if r['roi'] > 0 else "🔴" if r['bets'] > 0 else "⚪"
        print(f"{emoji} {r['league']:<4} {r['total']:>6} {r['patterns']:>5} {r['bets']:>6} {r['winrate']:>4.0f}% {r['roi']:>+6.1f}% {r['profit']:>+7.0f}₽")
    
    # Диагностика
    print("\n" + "="*70)
    print("🔍 ДИАГНОСТИКА")
    print("="*70)
    
    profitable = [r for r in results if r['roi'] > 0]
    losing = [r for r in results if r['roi'] < 0 and r['bets'] > 0]
    no_bets = [r for r in results if r['bets'] == 0]
    
    print(f"\n🟢 Прибыльных лиг: {len(profitable)}")
    print(f"🔴 Убыточных лиг: {len(losing)}")
    print(f"⚪ Без ставок: {len(no_bets)}")
    
    if no_bets:
        print(f"\n⚠️ Лиги без ставок (паттерны не сработали):")
        for r in no_bets:
            print(f"   • {r['league']}: {r['patterns']} паттернов найдено, но 0 совпадений на тесте")
    
    # Рекомендации
    print("\n" + "="*70)
    print("💡 РЕКОМЕНДАЦИИ")
    print("="*70)
    
    if profitable:
        print(f"\n✅ Ставить на лиги: {', '.join(r['league'] for r in profitable)}")
    if losing:
        print(f"❌ Избегать лиг: {', '.join(r['league'] for r in losing)}")
    if no_bets:
        print(f"⚠️ Нужна доработка для: {', '.join(r['league'] for r in no_bets)}")

if __name__ == "__main__":
    results = backtest_by_league()
    print_results(results)
