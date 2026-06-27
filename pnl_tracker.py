import json
import os
from datetime import datetime

PnL_FILE = 'pnl.json'

def load_pnl():
    """Загружает P&L из JSON"""
    if os.path.exists(PnL_FILE):
        with open(PnL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'bets': [], 'next_id': 1}

def save_pnl(data):
    """Сохраняет P&L в JSON"""
    with open(PnL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_bet(match, bet_type, odds, stake, league='N/A'):
    """Добавляет новую ставку"""
    data = load_pnl()
    
    bet = {
        'id': data['next_id'],
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'match': match,
        'bet_type': bet_type,
        'odds': odds,
        'stake': stake,
        'status': 'pending',  # pending, won, lost
        'profit': 0,
        'league': league
    }
    
    data['bets'].append(bet)
    data['next_id'] += 1
    save_pnl(data)
    
    return bet['id']

def update_result(bet_id, result):
    """Обновляет результат ставки (win/lose)"""
    data = load_pnl()
    
    for bet in data['bets']:
        if bet['id'] == bet_id:
            bet['status'] = 'won' if result == 'win' else 'lost'
            if result == 'win':
                bet['profit'] = bet['stake'] * (bet['odds'] - 1)
            else:
                bet['profit'] = -bet['stake']
            save_pnl(data)
            return True
    
    return False

def get_stats():
    """Возвращает статистику"""
    data = load_pnl()
    bets = data['bets']
    
    if not bets:
        return {
            'total_bets': 0,
            'won': 0,
            'lost': 0,
            'pending': 0,
            'winrate': 0,
            'total_stake': 0,
            'total_profit': 0,
            'roi': 0
        }
    
    won = sum(1 for b in bets if b['status'] == 'won')
    lost = sum(1 for b in bets if b['status'] == 'lost')
    pending = sum(1 for b in bets if b['status'] == 'pending')
    
    total_stake = sum(b['stake'] for b in bets if b['status'] != 'pending')
    total_profit = sum(b['profit'] for b in bets if b['status'] != 'pending')
    
    winrate = (won / (won + lost) * 100) if (won + lost) > 0 else 0
    roi = (total_profit / total_stake * 100) if total_stake > 0 else 0
    
    return {
        'total_bets': len(bets),
        'won': won,
        'lost': lost,
        'pending': pending,
        'winrate': winrate,
        'total_stake': total_stake,
        'total_profit': total_profit,
        'roi': roi
    }

def get_history(limit=10):
    """Возвращает последние ставки"""
    data = load_pnl()
    return data['bets'][-limit:]

def get_pending_bets():
    """Возвращает все pending ставки"""
    data = load_pnl()
    return [b for b in data['bets'] if b['status'] == 'pending']

if __name__ == "__main__":
    # Тест
    print("Тест P&L трекера\n")
    
    # Добавляем тестовые ставки
    id1 = add_bet("Зенит vs Спартак", "П1", 2.1, 300, "RUS")
    print(f"✓ Добавлена ставка #{id1}")
    
    id2 = add_bet("Барселона vs Реал", "ТБ 2.5", 1.85, 300, "SP1")
    print(f"✓ Добавлена ставка #{id2}")
    
    # Обновляем результаты
    update_result(id1, 'win')
    print(f"✓ Ставка #{id1} выиграла")
    
    update_result(id2, 'lose')
    print(f"✓ Ставка #{id2} проиграла")
    
    # Статистика
    stats = get_stats()
    print(f"\n📊 Статистика:")
    print(f"  Всего ставок: {stats['total_bets']}")
    print(f"  Выиграно: {stats['won']}")
    print(f"  Проиграно: {stats['lost']}")
    print(f"  Winrate: {stats['winrate']:.1f}%")
    print(f"  ROI: {stats['roi']:+.1f}%")
    print(f"  Прибыль: {stats['total_profit']:+.0f}₽")
    
    # История
    print(f"\n📋 Последние ставки:")
    for bet in get_history():
        status = "✓" if bet['status'] == 'won' else "✗" if bet['status'] == 'lost' else "⏳"
        print(f"  {status} #{bet['id']} {bet['match']} | {bet['bet_type']} @ {bet['odds']} | {bet['profit']:+.0f}₽")
