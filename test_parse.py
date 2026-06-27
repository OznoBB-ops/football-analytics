from bookmaker_parser import parse_bookmaker_text

text = """Live

Основные
Футбол
Квинсленд, Премьер ЛигаАвстралия
1
Пенинсула Пауэр
Брисбен Роар (мол)
0
0
0
0
1.47
3.65
6.50
1Т 44'
+42

Новый Южный Уэльс, Лига 1Австралия
1
Нортерн Тайгерс
Далвич Хилл
1
0
1
0
1.12
7.25
15.5
1Т 6'
+69

Новый Южный Уэльс, Премьер ЛигаАвстралия
2
НСВ Университи
Сазерленд Шаркс
1
1
0
0
1
1
3.75
1.62
4.75"""

matches = parse_bookmaker_text(text)
print(f"✅ Найдено {len(matches)} матчей:\n")
for m in matches:
    inv = 1/m['h_odd'] + 1/m['d_odd'] + 1/m['a_odd']
    margin = (inv - 1) * 100
    print(f"🏆 {m['league']}")
    print(f"⚽ {m['home']} vs {m['away']}")
    print(f"💰 {m['h_odd']}/{m['d_odd']}/{m['a_odd']} | Маржа: {margin:.1f}%\n")
