"""
Анализ мотивации команд на основе:
- Позиции в таблице
- Разницы в очках
- Домашней/выездной статистики
"""

# Кеш таблиц лиг
_LEAGUE_TABLES_CACHE = {}

def build_league_table(matches, league):
    """Строит таблицу лиги с кешированием"""
    if league in _LEAGUE_TABLES_CACHE:
        return _LEAGUE_TABLES_CACHE[league]
    
    teams = {}
    
    for m in matches:
        if m['league'] != league or not m['res']:
            continue
        
        home = m['home']
        away = m['away']
        
        if home not in teams:
            teams[home] = {
                'points': 0, 'gf': 0, 'ga': 0, 'w': 0, 'd': 0, 'l': 0, 
                'home_w': 0, 'home_d': 0, 'home_l': 0,
                'away_w': 0, 'away_d': 0, 'away_l': 0
            }
        if away not in teams:
            teams[away] = {
                'points': 0, 'gf': 0, 'ga': 0, 'w': 0, 'd': 0, 'l': 0,
                'home_w': 0, 'home_d': 0, 'home_l': 0,
                'away_w': 0, 'away_d': 0, 'away_l': 0
            }
        
        teams[home]['gf'] += m['hg']
        teams[home]['ga'] += m['ag']
        teams[away]['gf'] += m['ag']
        teams[away]['ga'] += m['hg']
        
        if m['res'] == 'H':
            teams[home]['points'] += 3
            teams[home]['w'] += 1
            teams[home]['home_w'] += 1
            teams[away]['l'] += 1
            teams[away]['away_l'] += 1
        elif m['res'] == 'A':
            teams[away]['points'] += 3
            teams[away]['w'] += 1
            teams[away]['away_w'] += 1
            teams[home]['l'] += 1
            teams[home]['home_l'] += 1
        elif m['res'] == 'D':
            teams[home]['points'] += 1
            teams[away]['points'] += 1
            teams[home]['d'] += 1
            teams[away]['d'] += 1
            teams[home]['home_d'] += 1
            teams[away]['away_d'] += 1
    
    sorted_teams = sorted(teams.items(), key=lambda x: (-x[1]['points'], -(x[1]['gf'] - x[1]['ga'])))
    table = {team: {'pos': i+1, **stats} for i, (team, stats) in enumerate(sorted_teams)}
    
    _LEAGUE_TABLES_CACHE[league] = table
    return table

def find_team_in_table(table, team_name):
    """Ищет команду в таблице с учётом частичного совпадения"""
    team_norm = team_name.lower()
    for team in table:
        if team_norm == team.lower() or team_norm in team.lower() or team.lower() in team_norm:
            return team
    return None

def analyze_motivation(matches, home, away, league=None):
    """Анализирует мотивацию команд"""
    home_norm = home.lower()
    away_norm = away.lower()
    
    # Определяем лигу
    if not league:
        for m in matches:
            if home_norm in m['home_lower'] or home_norm in m['away_lower']:
                league = m['league']
                break
    
    if not league:
        return None
    
    table = build_league_table(matches, league)
    
    home_key = find_team_in_table(table, home)
    away_key = find_team_in_table(table, away)
    
    if not home_key or not away_key:
        return None
    
    home_stats = table[home_key]
    away_stats = table[away_key]
    total_teams = len(table)
    
    # Мотивация хозяев
    home_motivation = 50
    home_factors = []
    
    if home_stats['pos'] <= 3:
        home_motivation += 20
        home_factors.append("🏆 Борьба за титул (топ-3)")
    elif home_stats['pos'] <= 6:
        home_motivation += 10
        home_factors.append("🎯 Еврокубки (топ-6)")
    elif home_stats['pos'] >= total_teams - 2:
        home_motivation += 15
        home_factors.append("⚠️ Зона вылета")
    else:
        home_motivation -= 10
        home_factors.append("😴 Середина таблицы")
    
    points_diff = home_stats['points'] - away_stats['points']
    if points_diff > 10:
        home_motivation -= 5
        home_factors.append(f"📉 Отрыв +{points_diff} очков")
    elif points_diff < -10:
        home_motivation += 10
        home_factors.append(f"📈 Отстают на {-points_diff} очков")
    
    home_games = home_stats['home_w'] + home_stats['home_d'] + home_stats['home_l']
    if home_games > 0:
        home_winrate = home_stats['home_w'] / home_games
        if home_winrate > 0.6:
            home_motivation += 10
            home_factors.append("🏠 Сильны дома")
        elif home_winrate < 0.3:
            home_motivation -= 5
            home_factors.append("🏠 Слабы дома")
    
    # Мотивация гостей
    away_motivation = 50
    away_factors = []
    
    if away_stats['pos'] <= 3:
        away_motivation += 20
        away_factors.append("🏆 Борьба за титул (топ-3)")
    elif away_stats['pos'] <= 6:
        away_motivation += 10
        away_factors.append("🎯 Еврокубки (топ-6)")
    elif away_stats['pos'] >= total_teams - 2:
        away_motivation += 15
        away_factors.append("⚠️ Зона вылета")
    else:
        away_motivation -= 10
        away_factors.append("😴 Середина таблицы")
    
    points_diff_away = away_stats['points'] - home_stats['points']
    if points_diff_away > 10:
        away_motivation -= 5
        away_factors.append(f"📉 Отрыв +{points_diff_away} очков")
    elif points_diff_away < -10:
        away_motivation += 10
        away_factors.append(f"📈 Отстают на {-points_diff_away} очков")
    
    away_games = away_stats['away_w'] + away_stats['away_d'] + away_stats['away_l']
    if away_games > 0:
        away_winrate = away_stats['away_w'] / away_games
        if away_winrate > 0.5:
            away_motivation += 10
            away_factors.append("✈️ Сильны на выезде")
        elif away_winrate < 0.25:
            away_motivation -= 5
            away_factors.append("✈️ Слабы на выезде")
    
    return {
        'home_motivation': min(100, max(0, home_motivation)),
        'away_motivation': min(100, max(0, away_motivation)),
        'home_factors': home_factors,
        'away_factors': away_factors,
        'home_position': home_stats['pos'],
        'away_position': away_stats['pos'],
        'total_teams': total_teams,
        'home_points': home_stats['points'],
        'away_points': away_stats['points']
    }

if __name__ == "__main__":
    from recommendations import load_matches
    
    matches = load_matches()
    
    test_pairs = [
        ("zenit", "spartak"),
        ("barcelona", "real madrid"),
        ("bayern", "dortmund"),
    ]
    
    for home, away in test_pairs:
        print(f"\n{'='*60}")
        print(f"🔍 {home.upper()} vs {away.upper()}")
        print('='*60)
        
        result = analyze_motivation(matches, home, away)
        
        if result:
            print(f"\n🏠 {home.title()} (#{result['home_position']}/{result['total_teams']}, {result['home_points']} очков)")
            print(f"   Мотивация: {result['home_motivation']}/100")
            for factor in result['home_factors']:
                print(f"   • {factor}")
            
            print(f"\n✈️ {away.title()} (#{result['away_position']}/{result['total_teams']}, {result['away_points']} очков)")
            print(f"   Мотивация: {result['away_motivation']}/100")
            for factor in result['away_factors']:
                print(f"   • {factor}")
        else:
            print("❌ Не удалось проанализировать")
