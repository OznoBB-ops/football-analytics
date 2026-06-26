def find_value_for_match(h_odd, d_odd, a_odd):
    """Проверяет, есть ли валуй на конкретный матч"""
    
    # Твои 4 рабочих паттерна
    patterns = [
        {'h': 2.1, 'd': 3.3, 'a': 3.9, 'bet': 'П2', 'edge': 8.6, 'roi': 30.0},
        {'h': 2.0, 'd': 3.4, 'a': 4.1, 'bet': 'Ничья', 'edge': 9.8, 'roi': 29.5},
        {'h': 2.4, 'd': 3.2, 'a': 3.3, 'bet': 'П1', 'edge': 13.5, 'roi': 29.2},
        {'h': 2.9, 'd': 3.3, 'a': 2.6, 'bet': 'Ничья', 'edge': 9.8, 'roi': 29.1},
    ]
    
    values = []
    tolerance = 0.15  # допуск по кэфам
    
    for p in patterns:
        if (abs(h_odd - p['h']) <= tolerance and 
            abs(d_odd - p['d']) <= tolerance and 
            abs(a_odd - p['a']) <= tolerance):
            values.append(p)
    
    return values
