"""
Стратегия для топ-лиг на основе xG + форма + мотивация
"""
from recommendations import analyze_team_form, analyze_h2h
from predictor import calculate_expected_goals, predict_outcomes
from motivation import analyze_motivation

def is_valid_odd(odd):
    """Проверяет, что кэф реалистичный"""
    return odd and 1.3 <= odd <= 4.0

def analyze_match_xg(match, all_matches):
    """Анализирует матч через xG + форму + мотивацию"""
    home = match['home']
    away = match['away']
    
    # Форма команд
    home_form = analyze_team_form(all_matches, home, last_n=10)
    away_form = analyze_team_form(all_matches, away, last_n=10)
    
    if not home_form or not away_form:
        return None
    
    # H2H
    h2h = analyze_h2h(all_matches, home, away)
    
    # xG
    xg = calculate_expected_goals(home_form, away_form, h2h)
    predictions = predict_outcomes(xg['home_xg'], xg['away_xg'])
    
    # Мотивация
    motivation = analyze_motivation(all_matches, home, away)
    
    recommendations = []
    
    # 1. Анализ 1X2 через xG (только валидные кэфы)
    if is_valid_odd(match['h_odd']):
        fair_prob = predictions['П1']
        fair_odd = 100 / fair_prob if fair_prob > 0 else 0
        
        if match['h_odd'] > fair_odd:
            edge = (fair_prob/100 * match['h_odd'] - 1) * 100
            if 5 < edge < 50:  # edge должен быть реалистичным
                recommendations.append({
                    'bet': f"П1 @ {match['h_odd']:.2f}",
                    'type': '1X2',
                    'score': min(50, edge * 2),
                    'reason': f"xG П1: {fair_prob:.0f}%, fair: {fair_odd:.2f}, edge: {edge:+.1f}%"
                })
    
    if is_valid_odd(match['a_odd']):
        fair_prob = predictions['П2']
        fair_odd = 100 / fair_prob if fair_prob > 0 else 0
        
        if match['a_odd'] > fair_odd:
            edge = (fair_prob/100 * match['a_odd'] - 1) * 100
            if 5 < edge < 50:
                recommendations.append({
                    'bet': f"П2 @ {match['a_odd']:.2f}",
                    'type': '1X2',
                    'score': min(50, edge * 2),
                    'reason': f"xG П2: {fair_prob:.0f}%, fair: {fair_odd:.2f}, edge: {edge:+.1f}%"
                })
    
    # 2. Тоталы через xG (только если xG реалистичный)
    expected_total = xg['home_xg'] + xg['away_xg']
    
    if 2.0 <= expected_total <= 4.0:  # реалистичный диапазон
        if expected_total > 2.8:
            assumed_odd = 1.9
            edge = (65/100 * assumed_odd - 1) * 100
            if edge > 5:
                recommendations.append({
                    'bet': f"ТБ 2.5 @ ~{assumed_odd:.2f}",
                    'type': 'totals',
                    'score': min(40, edge * 1.5),
                    'reason': f"xG тотал: {expected_total:.1f}, edge: {edge:+.1f}%"
                })
        
        if expected_total < 2.3:
            assumed_odd = 1.9
            edge = (65/100 * assumed_odd - 1) * 100
            if edge > 5:
                recommendations.append({
                    'bet': f"ТМ 2.5 @ ~{assumed_odd:.2f}",
                    'type': 'totals',
                    'score': min(40, edge * 1.5),
                    'reason': f"xG тотал: {expected_total:.1f}, edge: {edge:+.1f}%"
                })
    
    # 3. Корректировка через мотивацию
    if motivation:
        if motivation['home_motivation'] >= 70:
            for r in recommendations:
                if 'П1' in r['bet']:
                    r['score'] += 15
                    r['reason'] += f" | мотивация {motivation['home_motivation']}/100"
        
        if motivation['away_motivation'] >= 70:
            for r in recommendations:
                if 'П2' in r['bet']:
                    r['score'] += 15
                    r['reason'] += f" | мотивация {motivation['away_motivation']}/100"
    
    # 4. Форма команд
    if home_form['winrate'] > 70:
        for r in recommendations:
            if 'П1' in r['bet']:
                r['score'] += 10
                r['reason'] += f" | форма {home_form['winrate']:.0f}%"
    
    if away_form['winrate'] > 70:
        for r in recommendations:
            if 'П2' in r['bet']:
                r['score'] += 10
                r['reason'] += f" | форма {away_form['winrate']:.0f}%"
    
    # Сортируем по score
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'match': f"{home} vs {away}",
        'league': match['league'],
        'date': match['date'],
        'xg': xg,
        'predictions': predictions,
        'motivation': motivation,
        'home_form': home_form,
        'away_form': away_form,
        'h2h': h2h,
        'recommendations': recommendations[:3]
    }

if __name__ == "__main__":
    from recommendations import load_matches
    
    matches = load_matches()
    
    # Тест на последних матчах E0
    e0_matches = [m for m in matches if m['league'] == 'E0' and m['h_odd']][-10:]
    
    print(f"Тестирую xG-стратегию на {len(e0_matches)} матчах АПЛ\n")
    
    valid_count = 0
    for m in e0_matches[:5]:
        result = analyze_match_xg(m, matches)
        if result and result['recommendations']:
            valid_count += 1
            print(f"📊 {result['match']} ({result['date']})")
            print(f"   Кэфы: П1 {m['h_odd']:.2f} | Х {m['d_odd']:.2f} | П2 {m['a_odd']:.2f}")
            print(f"   xG: {result['xg']['home_xg']:.2f} - {result['xg']['away_xg']:.2f}")
            print(f"   Прогноз: П1 {result['predictions']['П1']:.0f}% | Х {result['predictions']['Х']:.0f}% | П2 {result['predictions']['П2']:.0f}%")
            for r in result['recommendations']:
                print(f"   💡 {r['bet']} (score: {r['score']:.0f})")
                print(f"      {r['reason']}")
            print()
        else:
            print(f"⚪ {m['home']} vs {m['away']} — нет рекомендаций (кэфы: {m['h_odd']:.2f}/{m['d_odd']:.2f}/{m['a_odd']:.2f})\n")
    
    print(f"\n✅ Валидных матчей: {valid_count}/{min(5, len(e0_matches))}")
