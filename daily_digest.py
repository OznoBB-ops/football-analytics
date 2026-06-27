from datetime import datetime
from recommendations import load_matches, find_patterns, check_patterns
from predictor import predict_outcomes
from teams_ru import translate_team
import csv
import os

def load_live_matches():
    """Загружает будущие матчи из live_matches.csv"""
    if not os.path.exists('live_matches.csv'):
        return []
    
    matches = []
    with open('live_matches.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                matches.append({
                    'home': row['home'],
                    'away': row['away'],
                    'home_lower': row['home'].lower(),
                    'away_lower': row['away'].lower(),
                    'h_odd': float(row['h_odd']) if row['h_odd'] else None,
                    'd_odd': float(row['d_odd']) if row['d_odd'] else None,
                    'a_odd': float(row['a_odd']) if row['a_odd'] else None,
                    'league': row['league'],
                    'date': row['date']
                })
            except:
                continue
    
    return matches

def analyze_odds(m):
    """Анализирует кэфы матча без истории команд"""
    if not (m['h_odd'] and m['d_odd'] and m['a_odd']):
        return None
    
    h, d, a = m['h_odd'], m['d_odd'], m['a_odd']
    
    # Маржа БК
    inv = 1/h + 1/d + 1/a
    margin = (inv - 1) * 100
    
    # Fair probabilities (без маржи)
    fair_h = (1/h/inv) * 100
    fair_d = (1/d/inv) * 100
    fair_a = (1/a/inv) * 100
    
    # Определяем фаворита
    if fair_h > 55:
        favorite = 'П1'
        fav_prob = fair_h
        fav_odd = h
    elif fair_a > 55:
        favorite = 'П2'
        fav_prob = fair_a
        fav_odd = a
    else:
        favorite = None
        fav_prob = 0
        fav_odd = 0
    
    return {
        'margin': margin,
        'fair_h': fair_h,
        'fair_d': fair_d,
        'fair_a': fair_a,
        'favorite': favorite,
        'fav_prob': fav_prob,
        'fav_odd': fav_odd
    }

def generate_daily_digest():
    """Генерирует топ-3 рекомендации на день"""
    matches = load_matches()
    patterns = find_patterns(matches, min_sample=30, min_edge=10)
    live_matches = load_live_matches()
    
    if not live_matches:
        return []
    
    recommendations = []
    
    for m in live_matches:
        score = 0
        reasons = []
        
        # 1. Анализ кэфов (всегда работает)
        odds_analysis = analyze_odds(m)
        if odds_analysis:
            # Большая маржа = больше шансов на валуй
            if odds_analysis['margin'] > 12:
                score += 10
                reasons.append(f"💸 Маржа БК: {odds_analysis['margin']:.1f}%")
            
            # Явный фаворит
            if odds_analysis['favorite']:
                score += 15
                reasons.append(f"👑 Фаворит: {odds_analysis['favorite']} ({odds_analysis['fav_prob']:.0f}%)")
        
        # 2. Паттерны из базы (если кэфы совпадают с историческими)
        found = check_patterns(m, patterns)
        for p in found[:2]:
            if p['type'] == '1X2':
                score += min(40, p['roi'] * 2)
                reasons.append(f"💰 {p['bet']} @ {p['odds']:.2f} (ROI {p['roi']:+.0f}%)")
            elif p['type'] == 'totals':
                score += min(35, p['roi'] * 1.5)
                reasons.append(f"📊 {p['bet']} ({p['real']:.0f}%)")
            elif p['type'] == 'btts':
                score += min(35, p['roi'] * 1.5)
                reasons.append(f"⚽ {p['bet']} ({p['real']:.0f}%)")
        
        # 3. Прогноз на основе кэфов
        predictions = None
        if odds_analysis:
            # Используем fair odds как приближение к прогнозу
            predictions = {
                'П1': odds_analysis['fair_h'],
                'Х': odds_analysis['fair_d'],
                'П2': odds_analysis['fair_a'],
                'ТБ 2.5': 50,  # по умолчанию
                'ОЗ Да': 50
            }
        
        recommendations.append({
            'match': f"{translate_team(m['home'])} vs {translate_team(m['away'])}",
            'league': m['league'],
            'date': m['date'],
            'score': score,
            'reasons': reasons[:3] if reasons else ["📋 Стандартный матч"],
            'predictions': predictions,
            'odds': {'h': m['h_odd'], 'd': m['d_odd'], 'a': m['a_odd']},
            'margin': odds_analysis['margin'] if odds_analysis else 0
        })
    
    # Сортируем: сначала по score, потом по марже
    recommendations.sort(key=lambda x: (x['score'], x['margin']), reverse=True)
    
    return recommendations[:3]

def format_digest(recommendations):
    """Форматирует дайджест для Telegram"""
    if not recommendations:
        return "📋 Сегодня нет матчей для анализа\n\nИспользуйте /analyze для анализа текущей линии БК"
    
    lines = ["🎯 *ДНЕВНОЙ ДАЙДЖЕСТ*\n"]
    lines.append(f"📅 {datetime.now().strftime('%d.%m.%Y')}\n")
    
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"*{i}. {rec['match']}*")
        lines.append(f"🏆 {rec['league']} | 📅 {rec['date']}")
        
        # Кэфы
        if rec['odds']['h'] and rec['odds']['d'] and rec['odds']['a']:
            lines.append(f"💰 П1: {rec['odds']['h']:.2f} | Х: {rec['odds']['d']:.2f} | П2: {rec['odds']['a']:.2f}")
        
        # Fair odds
        if rec['predictions']:
            pred = rec['predictions']
            lines.append(f"🎯 Fair: П1 {pred['П1']:.0f}% | Х {pred['Х']:.0f}% | П2 {pred['П2']:.0f}%")
        
        lines.append(f"📊 Score: {rec['score']}")
        
        # Анализ
        if rec['reasons']:
            lines.append("💡 *Анализ:*")
            for r in rec['reasons']:
                lines.append(f"  • {r}")
        
        lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    print("Генерация дайджеста...")
    recs = generate_daily_digest()
    digest = format_digest(recs)
    print(digest)
