import csv
import os
from datetime import datetime

def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), '%d/%m/%Y')
    except:
        return None

def load_matches():
    matches = []
    
    # RUS, FIN, POL — без заголовков
    for fname, league in [('RUS.csv','RUS'), ('FIN.csv','FIN'), ('POL.csv','POL')]:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    p = line.strip().split(',')
                    if len(p) >= 13:
                        try:
                            date = parse_date(p[3])
                            if date:
                                matches.append({
                                    'date': date,
                                    'home': p[5].strip(),
                                    'away': p[6].strip(),
                                    'res': p[9].strip() if p[9] else None,
                                    'h_odd': float(p[10]) if p[10] else None,
                                    'd_odd': float(p[11]) if p[11] else None,
                                    'a_odd': float(p[12]) if p[12] else None,
                                    'league': league
                                })
                        except: pass
    
    # P1 — с заголовками
    if os.path.exists('P1.csv'):
        with open('P1.csv', 'r', encoding='utf-8', errors='ignore') as f:
            header = f.readline().strip().split(',')
            idx = {h.strip(): i for i, h in enumerate(header)}
            di = idx.get('Date')
            hi = idx.get('HomeTeam')
            ai = idx.get('AwayTeam')
            ri = idx.get('FTR')
            bh = idx.get('B365H')
            bd = idx.get('B365D')
            ba = idx.get('B365A')
            
            if all(x is not None for x in [di, hi, ai, bh, bd, ba]):
                for line in f:
                    p = line.strip().split(',')
                    if len(p) > max(di, hi, ai, bh, bd, ba):
                        try:
                            date = parse_date(p[di])
                            if date:
                                matches.append({
                                    'date': date,
                                    'home': p[hi].strip(),
                                    'away': p[ai].strip(),
                                    'res': p[ri].strip() if ri and len(p) > ri and p[ri] else None,
                                    'h_odd': float(p[bh]) if p[bh] else None,
                                    'd_odd': float(p[bd]) if p[bd] else None,
                                    'a_odd': float(p[ba]) if p[ba] else None,
                                    'league': 'P1'
                                })
                        except: pass
    
    return matches

def find_historical_values(matches, min_edge=3, min_sample=20):
    """Ищет исторические валуи — где БК систематически ошибалась"""
    
    # Группируем матчи по диапазонам кэфов (с шагом 0.1)
    ranges = {}
    for m in matches:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd'] > 1 and m['res']:
            # Округляем кэфы до 0.1 для группировки
            h_range = round(m['h_odd'], 1)
            d_range = round(m['d_odd'], 1)
            a_range = round(m['a_odd'], 1)
            
            key = (h_range, d_range, a_range)
            if key not in ranges:
                ranges[key] = []
            ranges[key].append(m)
    
    values = []
    
    for (h_range, d_range, a_range), group in ranges.items():
        if len(group) < min_sample:
            continue
        
        # Считаем fair odds (без маржи)
        inv_h, inv_d, inv_a = 1/h_range, 1/d_range, 1/a_range
        total_inv = inv_h + inv_d + inv_a
        margin = (total_inv - 1) * 100
        
        fair_h = (inv_h / total_inv) * 100
        fair_d = (inv_d / total_inv) * 100
        fair_a = (inv_a / total_inv) * 100
        
        # Считаем реальную частоту исходов
        h_wins = sum(1 for m in group if m['res'] == 'H')
        d_wins = sum(1 for m in group if m['res'] == 'D')
        a_wins = sum(1 for m in group if m['res'] == 'A')
        total = len(group)
        
        real_h = (h_wins / total) * 100
        real_d = (d_wins / total) * 100
        real_a = (a_wins / total) * 100
        
        # Ищем расхождения
        edge_h = real_h - fair_h
        edge_d = real_d - fair_d
        edge_a = real_a - fair_a
        
        if edge_h > min_edge:
            values.append({
                'range': f"П1 ~{h_range} / Х ~{d_range} / П2 ~{a_range}",
                'bet': 'П1',
                'bookmaker_odds': h_range,
                'fair_odds': fair_h,
                'real_freq': real_h,
                'edge': edge_h,
                'sample': total,
                'roi': (real_h/100 * h_range - 1) * 100
            })
        
        if edge_d > min_edge:
            values.append({
                'range': f"П1 ~{h_range} / Х ~{d_range} / П2 ~{a_range}",
                'bet': 'Ничья',
                'bookmaker_odds': d_range,
                'fair_odds': fair_d,
                'real_freq': real_d,
                'edge': edge_d,
                'sample': total,
                'roi': (real_d/100 * d_range - 1) * 100
            })
        
        if edge_a > min_edge:
            values.append({
                'range': f"П1 ~{h_range} / Х ~{d_range} / П2 ~{a_range}",
                'bet': 'П2',
                'bookmaker_odds': a_range,
                'fair_odds': fair_a,
                'real_freq': real_a,
                'edge': edge_a,
                'sample': total,
                'roi': (real_a/100 * a_range - 1) * 100
            })
    
    # Сортируем по ROI
    values.sort(key=lambda x: x['roi'], reverse=True)
    return values

def main():
    print("🔍 Загрузка базы...")
    matches = load_matches()
    print(f"✅ Загружено {len(matches)} матчей\n")
    
    print("📊 Ретроспективный анализ (где БК ошибалась)...\n")
    values = find_historical_values(matches, min_edge=3, min_sample=20)
    
    if not values:
        print("❌ Системных ошибок БК не найдено")
        return
    
    print(f"🎯 Найдено {len(values)} паттернов с преимуществом:\n")
    print("=" * 90)
    
    for v in values[:25]:
        print(f" Диапазон: {v['range']}")
        print(f"   Ставка: {v['bet']} @ {v['bookmaker_odds']:.1f}")
        print(f"   Fair odds БК: {v['fair_odds']:.1f}% | Реальная частота: {v['real_freq']:.1f}%")
        print(f"   Преимущество: +{v['edge']:.1f}% | ROI: {v['roi']:+.1f}%")
        print(f"   Выборка: {v['sample']} матчей")
        print("-" * 90)
    
    # Сохраняем
    with open('historical_values.txt', 'w', encoding='utf-8') as f:
        f.write(f"Исторические валуи (анализ {len(matches)} матчей)\n")
        f.write("=" * 90 + "\n\n")
        for v in values:
            f.write(f"{v['range']} | {v['bet']} @ {v['bookmaker_odds']:.1f}\n")
            f.write(f"   Fair: {v['fair_odds']:.1f}% | Real: {v['real_freq']:.1f}% | Edge: +{v['edge']:.1f}% | ROI: {v['roi']:+.1f}% | N={v['sample']}\n\n")
    
    print(f"\n💾 Результаты сохранены в historical_values.txt")

if __name__ == "__main__":
    main()
