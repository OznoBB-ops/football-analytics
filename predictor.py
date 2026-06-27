import math
from itertools import product

def poisson_pmf(k, lambda_val):
    """Функция вероятности Пуассона"""
    if lambda_val <= 0:
        return 1.0 if k == 0 else 0.0
    return (lambda_val ** k) * math.exp(-lambda_val) / math.factorial(k)

def calculate_expected_goals(home_form, away_form, h2h=None):
    """Рассчитывает ожидаемые голы (xG) для каждой команды"""
    
    # Базовые xG из формы
    home_xg = home_form['avg_gf'] if home_form else 1.3
    away_xg = away_form['avg_gf'] if away_form else 1.1
    
    # Корректировка по обороне
    home_def = home_form['avg_ga'] if home_form else 1.2
    away_def = away_form['avg_ga'] if away_form else 1.4
    
    # Среднее между атакой хозяев и обороной гостей
    home_expected = (home_xg + away_def) / 2
    
    # Среднее между атакой гостей и обороной хозяев
    away_expected = (away_xg + home_def) / 2
    
    # Корректировка по H2H
    if h2h and h2h['matches'] >= 3:
        h2h_avg = h2h['avg_total'] / 2  # Среднее на команду
        # 30% веса на H2H
        home_expected = home_expected * 0.7 + h2h_avg * 0.3
        away_expected = away_expected * 0.7 + h2h_avg * 0.3
    
    # Домашнее преимущество (+15%)
    home_expected *= 1.15
    
    return {
        'home_xg': round(home_expected, 2),
        'away_xg': round(away_expected, 2),
        'total_xg': round(home_expected + away_expected, 2)
    }

def predict_exact_scores(home_xg, away_xg, max_goals=5):
    """Предсказывает вероятности точных счётов через распределение Пуассона"""
    scores = {}
    
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = poisson_pmf(h, home_xg) * poisson_pmf(a, away_xg)
            scores[f"{h}:{a}"] = {
                'probability': prob * 100,
                'home': h,
                'away': a
            }
    
    # Сортируем по вероятности
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]['probability'], reverse=True)
    return sorted_scores

def predict_outcomes(home_xg, away_xg):
    """Предсказывает исходы (П1/Х/П2) и тоталы"""
    outcomes = {
        'П1': 0, 'Х': 0, 'П2': 0,
        'ТБ 2.5': 0, 'ТМ 2.5': 0,
        'ОЗ Да': 0, 'ОЗ Нет': 0
    }
    
    for h in range(6):
        for a in range(6):
            prob = poisson_pmf(h, home_xg) * poisson_pmf(a, away_xg)
            
            # Исход
            if h > a:
                outcomes['П1'] += prob
            elif h == a:
                outcomes['Х'] += prob
            else:
                outcomes['П2'] += prob
            
            # Тотал
            if h + a > 2.5:
                outcomes['ТБ 2.5'] += prob
            else:
                outcomes['ТМ 2.5'] += prob
            
            # ОЗ
            if h > 0 and a > 0:
                outcomes['ОЗ Да'] += prob
            else:
                outcomes['ОЗ Нет'] += prob
    
    # Конвертируем в проценты
    for key in outcomes:
        outcomes[key] = round(outcomes[key] * 100, 1)
    
    return outcomes

def find_value_bets(predictions, market_odds):
    """Ищет валуйные ставки, сравнивая предсказания с кэфами БК"""
    values = []
    
    # 1X2
    if 'h_odd' in market_odds:
        fair_h = 100 / predictions['П1'] if predictions['П1'] > 0 else 0
        fair_d = 100 / predictions['Х'] if predictions['Х'] > 0 else 0
        fair_a = 100 / predictions['П2'] if predictions['П2'] > 0 else 0
        
        if market_odds['h_odd'] > fair_h * 1.1:
            values.append({
                'bet': f"П1 @ {market_odds['h_odd']:.2f}",
                'fair_odd': fair_h,
                'edge': (market_odds['h_odd'] / fair_h - 1) * 100,
                'prob': predictions['П1']
            })
        if market_odds['d_odd'] > fair_d * 1.1:
            values.append({
                'bet': f"Х @ {market_odds['d_odd']:.2f}",
                'fair_odd': fair_d,
                'edge': (market_odds['d_odd'] / fair_d - 1) * 100,
                'prob': predictions['Х']
            })
        if market_odds['a_odd'] > fair_a * 1.1:
            values.append({
                'bet': f"П2 @ {market_odds['a_odd']:.2f}",
                'fair_odd': fair_a,
                'edge': (market_odds['a_odd'] / fair_a - 1) * 100,
                'prob': predictions['П2']
            })
    
    # Тоталы
    markets = market_odds.get('markets', {})
    if '2.5' in markets.get('totals', {}):
        t = markets['totals']['2.5']
        fair_over = 100 / predictions['ТБ 2.5'] if predictions['ТБ 2.5'] > 0 else 0
        fair_under = 100 / predictions['ТМ 2.5'] if predictions['ТМ 2.5'] > 0 else 0
        
        if t['over'] > fair_over * 1.1:
            values.append({
                'bet': f"ТБ 2.5 @ {t['over']:.2f}",
                'fair_odd': fair_over,
                'edge': (t['over'] / fair_over - 1) * 100,
                'prob': predictions['ТБ 2.5']
            })
        if t['under'] > fair_under * 1.1:
            values.append({
                'bet': f"ТМ 2.5 @ {t['under']:.2f}",
                'fair_odd': fair_under,
                'edge': (t['under'] / fair_under - 1) * 100,
                'prob': predictions['ТМ 2.5']
            })
    
    # ОЗ
    if 'yes' in markets.get('btts', {}):
        btts = markets['btts']
        fair_yes = 100 / predictions['ОЗ Да'] if predictions['ОЗ Да'] > 0 else 0
        fair_no = 100 / predictions['ОЗ Нет'] if predictions['ОЗ Нет'] > 0 else 0
        
        if btts['yes'] > fair_yes * 1.1:
            values.append({
                'bet': f"ОЗ Да @ {btts['yes']:.2f}",
                'fair_odd': fair_yes,
                'edge': (btts['yes'] / fair_yes - 1) * 100,
                'prob': predictions['ОЗ Да']
            })
        if btts['no'] > fair_no * 1.1:
            values.append({
                'bet': f"ОЗ Нет @ {btts['no']:.2f}",
                'fair_odd': fair_no,
                'edge': (btts['no'] / fair_no - 1) * 100,
                'prob': predictions['ОЗ Нет']
            })
    
    values.sort(key=lambda x: x['edge'], reverse=True)
    return values

if __name__ == "__main__":
    # Тест
    home_form = {'avg_gf': 1.8, 'avg_ga': 1.2}
    away_form = {'avg_gf': 1.3, 'avg_ga': 1.6}
    
    xg = calculate_expected_goals(home_form, away_form)
    print(f"xG: {xg['home_xg']} - {xg['away_xg']} (Тотал: {xg['total_xg']})\n")
    
    outcomes = predict_outcomes(xg['home_xg'], xg['away_xg'])
    print("Исходы:")
    for k, v in outcomes.items():
        print(f"  {k}: {v}%")
    
    print("\nТоп-5 точных счётов:")
    scores = predict_exact_scores(xg['home_xg'], xg['away_xg'])
    for score, data in scores[:5]:
        print(f"  {score}: {data['probability']:.1f}%")
