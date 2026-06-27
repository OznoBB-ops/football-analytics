import telebot
import os
import json
from dotenv import load_dotenv
from teams_ru import translate_team
from bookmaker_parser import parse_bookmaker_text, save_to_base, analyze_match, format_for_telegram, generate_express, generate_systems
from recommendations import load_matches, find_patterns
from pnl_tracker import add_bet, update_result, get_stats, get_history, get_pending_bets

load_dotenv()

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN не найден")
    exit(1)

bot = telebot.TeleBot(TOKEN)
TRACKED_FILE = 'tracked.json'
WAITING_FOR_TEXT = {}
WAITING_FOR_BET = {}

MATCHES = load_matches()
print(f"✅ {len(MATCHES)} матчей")
PATTERNS = find_patterns(MATCHES, min_sample=30, min_edge=10)
print(f"✅ Паттернов: 1X2={len(PATTERNS['1X2'])}, Тоталы={len(PATTERNS['totals'])}, ОЗ={len(PATTERNS['btts'])}")

def load_tracked():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tracked(data):
    with open(TRACKED_FILE, 'w') as f:
        json.dump(data, f)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = """
⚽ *Football Analyzer*

📋 *Анализ линии БК:*
/analyze — пришли текст с кэфами

💰 *Учёт ставок (P&L):*
/bet — добавить ставку
/result — результат ставки
/pending — активные ставки
/stats — статистика
/history — история ставок

🔍 *Поиск матча:*
Напиши две команды: `Зенит Спартак`

📌 *Подписки:*
/track Зенит — следить
/untrack Зенит — отписаться
/tracked — список

📊 *Аналитика:*
/values — валуйные паттерны
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['bet'])
def start_bet(message):
    user_id = message.chat.id
    WAITING_FOR_BET[user_id] = {'step': 1}
    text = """💰 *Добавление ставки*

Введите данные в формате:
`Матч Тип_ставки Кэф Сумма`

Примеры:
`Зенит Спартак П1 2.1 300`
`Барселона Реал ТБ 2.5 1.85 300`

/cancel — отмена"""
    bot.send_message(user_id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: WAITING_FOR_BET.get(m.chat.id, {}).get('step') == 1, content_types=['text'])
def handle_bet_input(message):
    user_id = message.chat.id
    text = message.text.strip()
    parts = text.split()
    
    if len(parts) < 4:
        bot.send_message(user_id, "❌ Неверный формат. Пример: `Зенит Спартак П1 2.1 300`", parse_mode='Markdown')
        return
    
    try:
        stake = float(parts[-1])
        odds = float(parts[-2])
        bet_type = parts[-3]
        match = ' '.join(parts[:-3])
        
        bet_id = add_bet(match, bet_type, odds, stake)
        
        bot.send_message(user_id, 
            f"✅ Ставка #{bet_id} добавлена!\n\n"
            f"📋 {match}\n"
            f"💰 {bet_type} @ {odds}\n"
            f"💵 Сумма: {stake:.0f}₽\n\n"
            f"Используйте /result {bet_id} win/lose")
        
        del WAITING_FOR_BET[user_id]
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['result'])
def update_bet_result(message):
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "Использование: /result ID win/lose")
        return
    try:
        bet_id = int(args[1])
        result = args[2].lower()
        if result not in ('win', 'lose'):
            bot.send_message(message.chat.id, "❌ Результат: win или lose")
            return
        if update_result(bet_id, result):
            stats = get_stats()
            bot.send_message(message.chat.id, 
                f"✅ Ставка #{bet_id} обновлена!\n\n"
                f"📊 Ставок: {stats['total_bets']}\n"
                f"Winrate: {stats['winrate']:.1f}%\n"
                f"ROI: {stats['roi']:+.1f}%\n"
                f"Прибыль: {stats['total_profit']:+.0f}₽")
        else:
            bot.send_message(message.chat.id, f"❌ Ставка #{bet_id} не найдена")
    except ValueError:
        bot.send_message(message.chat.id, "❌ ID должен быть числом")

@bot.message_handler(commands=['pending'])
def show_pending(message):
    pending = get_pending_bets()
    if not pending:
        bot.send_message(message.chat.id, "⏳ Нет активных ставок")
        return
    text = "⏳ *Активные ставки:*\n\n"
    for bet in pending:
        text += f"#{bet['id']} {bet['match']}\n"
        text += f"  {bet['bet_type']} @ {bet['odds']} | {bet['stake']:.0f}₽\n"
        text += f"  📅 {bet['date']}\n\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def show_stats(message):
    stats = get_stats()
    if stats['total_bets'] == 0:
        bot.send_message(message.chat.id, "📊 Нет ставок. Используйте /bet")
        return
    text = f"""📊 *Статистика*

Всего ставок: {stats['total_bets']}
✓ Выиграно: {stats['won']}
✗ Проиграно: {stats['lost']}
⏳ Активных: {stats['pending']}

Winrate: {stats['winrate']:.1f}%
ROI: {stats['roi']:+.1f}%
Оборот: {stats['total_stake']:.0f}₽
Прибыль: {stats['total_profit']:+.0f}₽"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['history'])
def show_history(message):
    history = get_history(limit=15)
    if not history:
        bot.send_message(message.chat.id, "📋 История пуста")
        return
    text = "📋 *Последние 15 ставок:*\n\n"
    for bet in reversed(history):
        status = "✓" if bet['status'] == 'won' else "✗" if bet['status'] == 'lost' else "⏳"
        profit_str = f"{bet['profit']:+.0f}₽" if bet['status'] != 'pending' else "—"
        text += f"{status} #{bet['id']} {bet['match']}\n"
        text += f"  {bet['bet_type']} @ {bet['odds']} | {bet['stake']:.0f}₽ | {profit_str}\n"
        text += f"  📅 {bet['date']}\n\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['analyze'])
def start_analyze(message):
    WAITING_FOR_TEXT[message.chat.id] = True
    bot.send_message(message.chat.id,
        "📋 *Режим анализа БК*\n\n"
        "Пришли текст со страницы БК.\n"
        "❌ Отмена: /cancel",
        parse_mode='Markdown')

@bot.message_handler(commands=['cancel'])
def cancel_analyze(message):
    user_id = message.chat.id
    WAITING_FOR_TEXT.pop(user_id, None)
    WAITING_FOR_BET.pop(user_id, None)
    bot.send_message(user_id, "❌ Отменено")

@bot.message_handler(func=lambda m: WAITING_FOR_TEXT.get(m.chat.id, False), content_types=['text'])
def handle_bookmaker_text(message):
    matches = parse_bookmaker_text(message.text)
    if not matches:
        bot.send_message(message.chat.id, "❌ Не удалось распознать матчи")
        WAITING_FOR_TEXT.pop(message.chat.id, None)
        return
    saved = save_to_base(matches)
    analyses = [analyze_match(m, MATCHES, PATTERNS) for m in matches]
    express_list = generate_express(analyses, min_matches=2, max_matches=4) if len(analyses) >= 2 else None
    systems_list = generate_systems(analyses) if len(analyses) >= 3 else None
    result = format_for_telegram(analyses, express_list, systems_list)
    result = f"📋 <b>{len(matches)} матчей</b> (сохранено: {saved})\n\n" + result
    if len(result) > 4000:
        parts = result.split('\n\n')
        current = ""
        for part in parts:
            if len(current) + len(part) + 2 > 4000:
                bot.send_message(message.chat.id, current, parse_mode='HTML')
                current = part
            else:
                current += '\n\n' + part if current else part
        if current:
            bot.send_message(message.chat.id, current, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, result, parse_mode='HTML')
    WAITING_FOR_TEXT.pop(message.chat.id, None)

@bot.message_handler(commands=['track'])
def track_team(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /track Зенит")
        return
    team = args[1].strip().lower()
    user_id = str(message.chat.id)
    tracked = load_tracked()
    if user_id not in tracked:
        tracked[user_id] = []
    if team in tracked[user_id]:
        bot.send_message(message.chat.id, f"⚠️ Уже следишь за {team}")
        return
    tracked[user_id].append(team)
    save_tracked(tracked)
    bot.send_message(message.chat.id, f"✅ Слежу за {team.upper()}")

@bot.message_handler(commands=['untrack'])
def untrack_team(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /untrack Зенит")
        return
    team = args[1].strip().lower()
    user_id = str(message.chat.id)
    tracked = load_tracked()
    if user_id in tracked and team in tracked[user_id]:
        tracked[user_id].remove(team)
        save_tracked(tracked)
        bot.send_message(message.chat.id, f"❌ Отписался от {team.upper()}")
    else:
        bot.send_message(message.chat.id, "Ты не следишь за этой командой")

@bot.message_handler(commands=['tracked'])
def show_tracked(message):
    user_id = str(message.chat.id)
    tracked = load_tracked()
    if user_id not in tracked or not tracked[user_id]:
        bot.send_message(message.chat.id, " Список пуст")
        return
    teams = "\n".join([f"• {t.upper()}" for t in tracked[user_id]])
    bot.send_message(message.chat.id, f"📌 *Твои команды:*\n{teams}", parse_mode='Markdown')

@bot.message_handler(commands=['values'])
def send_values(message):
    text = "🎯 *Топ валуйные паттерны:*\n\n"
    text += "*1X2:*\n"
    for i, p in enumerate(PATTERNS['1X2'][:5], 1):
        text += f"{i}. {p['bet']} @ {p['odds']:.1f} | ROI {p['roi']:+.0f}% | N={p['n']}\n"
    text += "\n*Тоталы:*\n"
    for i, p in enumerate(PATTERNS['totals'][:3], 1):
        text += f"{i}. {p['bet']} | {p['real']:.0f}% | N={p['n']}\n"
    text += "\n*ОЗ:*\n"
    for i, p in enumerate(PATTERNS['btts'][:3], 1):
        text += f"{i}. {p['bet']} | {p['real']:.0f}% | N={p['n']}\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: not WAITING_FOR_TEXT.get(m.chat.id, False) and not WAITING_FOR_BET.get(m.chat.id))
def search_match(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Напиши две команды: `Зенит Спартак`", parse_mode='Markdown')
        return
    h2h = []
    for m in MATCHES:
        home_in = any(q.lower() in m['home'] for q in parts)
        away_in = any(q.lower() in m['away'] for q in parts)
        if home_in and away_in: h2h.append(m)
    if not h2h:
        bot.send_message(message.chat.id, "❌ Личных встреч не найдено")
        return
    total = len(h2h)
    hw = sum(1 for m in h2h if (m['home']==h2h[0]['home'] and m['res']=='H') or (m['away']==h2h[0]['home'] and m['res']=='A'))
    aw = sum(1 for m in h2h if (m['home']==h2h[0]['away'] and m['res']=='H') or (m['away']==h2h[0]['away'] and m['res']=='A'))
    dr = sum(1 for m in h2h if m['res']=='D')
    totals = [m['total'] for m in h2h]
    over25 = sum(1 for t in totals if t > 2.5) / total * 100
    btts = sum(1 for m in h2h if m['hg']>0 and m['ag']>0) / total * 100
    text = f"🔍 *{translate_team(h2h[0]['home'])} vs {translate_team(h2h[0]['away'])}*\n"
    text += f"Встреч: {total}\n"
    text += f"📊 П1: {hw/total*100:.0f}% ({hw}) | Х: {dr/total*100:.0f}% ({dr}) | П2: {aw/total*100:.0f}% ({aw})\n"
    text += f"📈 ТБ 2.5: {over25:.0f}% | ОЗ: {btts:.0f}% | Средний тотал: {sum(totals)/total:.1f}"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

print("🤖 Бот запущен...")
bot.infinity_polling()
