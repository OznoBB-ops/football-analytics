from recommendations import load_matches, find_patterns, check_patterns

print("Загрузка базы...")
matches = load_matches()
print(f"✓ {len(matches)} матчей\n")

print("Поиск паттернов...")
patterns = find_patterns(matches, min_sample=30, min_edge=10)
total = len(patterns['1X2']) + len(patterns['totals']) + len(patterns['btts'])
print(f"✓ {total} паттернов\n")

print("Бэктест на последних 1000 матчах...")
played = [m for m in matches if m['res'] and m['h_odd']][-1000:]

value_wins = 0
value_total = 0

for m in played:
    found = check_patterns(m, patterns)
    for p in found:
        if p['type'] == '1X2':
            value_total += 1
            bet_res = {'П1': 'H', 'Ничья': 'D', 'П2': 'A'}[p['bet']]
            if m['res'] == bet_res:
                value_wins += 1

if value_total > 0:
    winrate = value_wins / value_total * 100
    print(f"✓ Валуйных ставок: {value_total}")
    print(f"✓ Выигрышей: {value_wins} ({winrate:.1f}%)")
    
    if winrate > 50:
        print("✓ Стратегия прибыльная!")
    elif winrate > 40:
        print("⚠ Стратегия на грани")
    else:
        print("✗ Стратегия убыточная")
else:
    print("⚠ Нет валуйных ставок для проверки")
