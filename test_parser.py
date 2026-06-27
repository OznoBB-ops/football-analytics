from bookmaker_parser import parse_bookmaker_text

text = """Нортерн Тайгерс
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
+69"""

matches = parse_bookmaker_text(text)
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
    for v, d in totals.items():
        parts = []
        if 'over' in d: parts.append(f"ТБ {d['over']:.2f}")
        if 'under' in d: parts.append(f"ТМ {d['under']:.2f}")
        print(f"📊 Тотал {v}: {' | '.join(parts)}")
    print("-" * 60)
