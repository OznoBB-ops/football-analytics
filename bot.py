import telebot
import os
import json
from telebot import types
from dotenv import load_dotenv
from teams_ru import translate_team
from bookmaker_parser import parse_bookmaker_text, save_to_base, analyze_match, format_for_telegram, generate_express, generate_systems
from recommendations import load_matches, find_patterns
from pnl_tracker import add_bet, update_result, get_stats, get_history, get_pending_bets
from daily_digest import generate_daily_digest, format_digest

load_dotenv()

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN не найден")
    exit(1)

bot = telebot.TeleBot(TOKEN)
TRACKED_FILE = 'tracked.json'
USERS_FILE = 'users.json'
WAITING_FOR_TEXT = {}
WAITING_FOR_BET = {}

MATCHES = load_matches()
print(f"✅ {len(MATCHES)} матчей")
PATTERNS = find_patterns(MATCHES, min_sample=30, min_edge=10)
print(f"✅ Паттернов: 1X2={len(PATTERNS['1X2'])}, Тоталы={len(PATTERNS['totals'])}, ОЗ={len(PATTERNS['btts'])}")

# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(user_id):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            'username': None,
            'bankroll': 1000,
            'bet_size': 300,
            'notifications': True,
            'created': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        save_users(users)
    return users[uid]

def update_user(user_id, **kwargs):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        get_user(user_id)
    users[uid].update(kwargs)
    save_users(users)

def load_tracked():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tracked(data):
    with open(TRACKED_FILE, 'w') as f:
        json.dump(data, f)

# ========== ГЛАВНОЕ МЕНЮ ==========

def main_menu_keyboard():
    """Главное меню с кнопками"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Анализ линии", callback_data="menu_analyze"),
        types.InlineKeyboardButton("🎯 Дайджест", callback_data="menu_digest")
    )
    markup.add(
        types.InlineKeyboardButton("💰 Мои ставки", callback_data="menu_bets"),
        types.InlineKeyboardButton("📈 Статистика", callback_data="menu_stats")
    )
    markup.add(
        types.InlineKeyboardButton("🔍 Поиск матча", callback_data="menu_search"),
        types.InlineKeyboardButton("📌 Подписки", callback_data="menu_track")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 Валуйные паттерны", callback_data="menu_values"),
        types.InlineKeyboardButton("👤 Личный кабинет", callback_data="menu_profile")
    )
    return markup

def profile_keyboard():
    """Меню личного кабинета"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💵 Изменить банкролл", callback_data="profile_bankroll"),
        types.InlineKeyboardButton("🎲 Изменить размер ставки", callback_data="profile_bet_size"),
        types.InlineKeyboardButton("🔔 Уведомления: ВКЛ/ВЫКЛ", callback_data="profile_notify"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="menu_main")
    )
    return markup

def bets_keyboard():
    """Меню ставок"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить ставку", callback_data="bet_add"),
        types.InlineKeyboardButton("⏳ Активные", callback_data="bet_pending")
    )
    markup.add(
        types.InlineKeyboardButton("📋 История", callback_data="bet_history"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="menu_main")
    )
    return markup

def back_to_main_keyboard():
    """Кнопка назад"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="menu_main"))
    return markup

# ========== КОМАНДЫ ==========

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = get_user(message.chat.id)
    update_user(message.chat.id, username=message.from_user.username)
    
    text = f"""👋 *Привет, {message.from_user.first_name}!*

⚽ *Football Analyzer* — твоя система для анализа ставок

💰 Банкролл: {user['bankroll']}₽
🎲 Размер ставки: {user['bet_size']}₽

👇 Выбери раздел:"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['help', 'menu'])
def show_help(message):
    bot.send_message(
        message.chat.id,
        "👇 *Главное меню*",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

# ========== CALLBACK HANDLERS ==========

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.message.chat.id
    
    try:
        # Главное меню
        if call.data == "menu_main":
            user = get_user(user_id)
            text = f"👇 *Главное меню*\n\n💰 Банкролл: {user['bankroll']}₽ | 🎲 Ставка: {user['bet_size']}₽"
            bot.edit_message_text(text, user_id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=main_menu_keyboard())
        
        # Анализ линии
        elif call.data == "menu_analyze":
            WAITING_FOR_TEXT[user_id] = True
            text = """📊 *Анализ линии*

Пришли текст с кэфами из букмекерской конты.

Парсер поддерживает:
• Исходы 1X2
• Тоталы
• Форы
• Обе забьют

❌ Отмена: /cancel"""
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=back_to_main_keyboard())
        
        # Дайджест
        elif call.data == "menu_digest":
            bot.answer_callback_query(call.id, "⏳ Формирую дайджест...")
            recs = generate_daily_digest()
            digest = format_digest(recs)
            bot.edit_message_text(digest, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=back_to_main_keyboard())
        
        # Мои ставки
        elif call.data == "menu_bets":
            text = "💰 *Мои ставки*\n\nВыбери действие:"
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=bets_keyboard())
        
        # Добавить ставку
        elif call.data == "bet_add":
            WAITING_FOR_BET[user_id] = {'step': 1}
            text = """➕ *Новая ставка*

Формат: `Матч Тип_ставки Кэф Сумма`

Примеры:
`Зенит Спартак П1 2.1 300`
`Барселона Реал ТБ 2.5 1.85 300`"""
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=back_to_main_keyboard())
        
        # Активные ставки
        elif call.data == "bet_pending":
            pending = get_pending_bets()
            if not pending:
                text = "⏳ *Активные ставки*\n\nНет активных ставок"
            else:
                text = "⏳ *Активные ставки:*\n\n"
                for bet in pending:
                    text += f"#{bet['id']} {bet['match']}\n"
                    text += f"  {bet['bet_type']} @ {bet['odds']} | {bet['stake']:.0f}₽\n"
                    text += f"  📅 {bet['date']}\n\n"
                text += "Для обновления результата: `/result ID win/lose`"
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=bets_keyboard())
        
        # История
        elif call.data == "bet_history":
            history = get_history(limit=10)
            if not history:
                text = "📋 *История*\n\nПуста"
            else:
                text = "📋 *Последние ставки:*\n\n"
                for bet in reversed(history):
                    status = "✓" if bet['status'] == 'won' else "✗" if bet['status'] == 'lost' else "⏳"
                    profit_str = f"{bet['profit']:+.0f}₽" if bet['status'] != 'pending' else "—"
                    text += f"{status} #{bet['id']} {bet['bet_type']} @ {bet['odds']} | {profit_str}\n"
                    text += f"   {bet['match']}\n\n"
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=bets_keyboard())
        
        # Статистика
        elif call.data == "menu_stats":
            stats = get_stats()
            if stats['total_bets'] == 0:
                text = "📈 *Статистика*\n\nНет ставок. Добавь первую через «Мои ставки»."
            else:
                text = f"""📈 *Статистика*

📊 Всего ставок: {stats['total_bets']}
✓ Выиграно: {stats['won']}
✗ Проиграно: {stats['lost']}
⏳ Активных: {stats['pending']}

🎯 Winrate: {stats['winrate']:.1f}%
💹 ROI: {stats['roi']:+.1f}%
💵 Оборот: {stats['total_stake']:.0f}₽
💰 Прибыль: {stats['total_profit']:+.0f}₽"""
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=back_to_main_keyboard())
        
        # Поиск матча
        elif call.data == "menu_search":
            text = """🔍 *Поиск матча*

Напиши в чат две команды через пробел:
`Зенит Спартак`
`Барселона Реал Мадрид`

Получишь H2H статистику, тоталы, ОЗ."""
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=back_to_main_keyboard())
        
        # Подписки
        elif call.data == "menu_track":
            tracked = load_tracked()
            user_tracked = tracked.get(str(user_id), [])
            if not user_tracked:
                text = "📌 *Подписки*\n\nСписок пуст.\n\nДобавь команду: `/track Зенит`"
            else:
                teams = "\n".join([f"• {t.upper()}" for t in user_tracked])
                text = f"📌 *Подписки:*\n\n{teams}\n\nУдалить: `/untrack Команда`"
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=back_to_main_keyboard())
        
        # Валуйные паттерны
        elif call.data == "menu_values":
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
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=back_to_main_keyboard())
        
        # Личный кабинет
        elif call.data == "menu_profile":
            user = get_user(user_id)
            text = f"""👤 *Личный кабинет*

👤 @{user.get('username') or 'не указан'}
💰 Банкролл: {user['bankroll']}₽
🎲 Размер ставки: {user['bet_size']}₽
🔔 Уведомления: {'✅ Вкл' if user['notifications'] else '❌ Выкл'}
📅 Регистрация: {user['created']}"""
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=profile_keyboard())
        
        # Настройки профиля
        elif call.data == "profile_bankroll":
            WAITING_FOR_BET[user_id] = {'step': 'bankroll'}
            bot.edit_message_text("💵 Введи новый банкролл (число):", user_id, call.message.message_id,
                                 reply_markup=back_to_main_keyboard())
        
        elif call.data == "profile_bet_size":
            WAITING_FOR_BET[user_id] = {'step': 'bet_size'}
            bot.edit_message_text("🎲 Введи новый размер ставки (число):", user_id, call.message.message_id,
                                 reply_markup=back_to_main_keyboard())
        
        elif call.data == "profile_notify":
            user = get_user(user_id)
            new_val = not user['notifications']
            update_user(user_id, notifications=new_val)
            status = "✅ Вкл" if new_val else "❌ Выкл"
            bot.answer_callback_query(call.id, f"Уведомления: {status}")
            # Обновляем меню
            user = get_user(user_id)
            text = f"""👤 *Личный кабинет*

👤 @{user.get('username') or 'не указан'}
💰 Банкролл: {user['bankroll']}₽
🎲 Размер ставки: {user['bet_size']}₽
🔔 Уведомления: {'✅ Вкл' if user['notifications'] else '❌ Выкл'}
📅 Регистрация: {user['created']}"""
            bot.edit_message_text(text, user_id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=profile_keyboard())
        
        else:
            bot.answer_callback_query(call.id, "⚠️ Неизвестная команда")
    
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)[:50]}")

# ========== ОБРАБОТКА ТЕКСТА ==========

@bot.message_handler(commands=['cancel'])
def cancel_analyze(message):
    user_id = message.chat.id
    WAITING_FOR_TEXT.pop(user_id, None)
    WAITING_FOR_BET.pop(user_id, None)
    bot.send_message(user_id, "❌ Отменено", reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['analyze'])
def start_analyze(message):
    WAITING_FOR_TEXT[message.chat.id] = True
    bot.send_message(message.chat.id,
        "📊 *Режим анализа*\n\nПришли текст с кэфами.\n❌ /cancel",
        parse_mode='Markdown', reply_markup=back_to_main_keyboard())

@bot.message_handler(commands=['bet'])
def start_bet_cmd(message):
    WAITING_FOR_BET[message.chat.id] = {'step': 1}
    bot.send_message(message.chat.id,
        "➕ *Новая ставка*\n\nФормат: `Матч Тип Кэф Сумма`\nПример: `Зенит Спартак П1 2.1 300`",
        parse_mode='Markdown', reply_markup=back_to_main_keyboard())

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
                f"Прибыль: {stats['total_profit']:+.0f}₽",
                reply_markup=main_menu_keyboard())
        else:
            bot.send_message(message.chat.id, f"❌ Ставка #{bet_id} не найдена")
    except ValueError:
        bot.send_message(message.chat.id, "❌ ID должен быть числом")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    stats = get_stats()
    if stats['total_bets'] == 0:
        bot.send_message(message.chat.id, "📊 Нет ставок", reply_markup=main_menu_keyboard())
        return
    text = f"""📈 *Статистика*

Всего: {stats['total_bets']} | ✓ {stats['won']} | ✗ {stats['lost']} | ⏳ {stats['pending']}
Winrate: {stats['winrate']:.1f}% | ROI: {stats['roi']:+.1f}%
Прибыль: {stats['total_profit']:+.0f}₽"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['digest'])
def send_daily_digest(message):
    recs = generate_daily_digest()
    digest = format_digest(recs)
    bot.send_message(message.chat.id, digest, parse_mode='Markdown', reply_markup=main_menu_keyboard())

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
    bot.send_message(message.chat.id, f"✅ Слежу за {team.upper()}", reply_markup=main_menu_keyboard())

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
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda m: WAITING_FOR_BET.get(m.chat.id, {}).get('step') == 'bankroll', content_types=['text'])
def handle_bankroll_input(message):
    user_id = message.chat.id
    try:
        amount = float(message.text.strip())
        if amount < 100:
            bot.send_message(user_id, "❌ Минимум 100₽")
            return
        update_user(user_id, bankroll=amount)
        bot.send_message(user_id, f"✅ Банкролл обновлён: {amount:.0f}₽", reply_markup=main_menu_keyboard())
        del WAITING_FOR_BET[user_id]
    except:
        bot.send_message(user_id, "❌ Введи число")

@bot.message_handler(func=lambda m: WAITING_FOR_BET.get(m.chat.id, {}).get('step') == 'bet_size', content_types=['text'])
def handle_bet_size_input(message):
    user_id = message.chat.id
    try:
        amount = float(message.text.strip())
        if amount < 50:
            bot.send_message(user_id, "❌ Минимум 50₽")
            return
        update_user(user_id, bet_size=amount)
        bot.send_message(user_id, f"✅ Размер ставки: {amount:.0f}₽", reply_markup=main_menu_keyboard())
        del WAITING_FOR_BET[user_id]
    except:
        bot.send_message(user_id, "❌ Введи число")

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
            f"Результат: /result {bet_id} win/lose",
            reply_markup=main_menu_keyboard())
        
        del WAITING_FOR_BET[user_id]
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda m: WAITING_FOR_TEXT.get(m.chat.id, False), content_types=['text'])
def handle_bookmaker_text(message):
    matches = parse_bookmaker_text(message.text)
    if not matches:
        bot.send_message(message.chat.id, "❌ Не удалось распознать матчи", reply_markup=main_menu_keyboard())
        WAITING_FOR_TEXT.pop(message.chat.id, None)
        return
    saved = save_to_base(matches)
    analyses = [analyze_match(m, MATCHES, PATTERNS) for m in matches]
    express_list = generate_express(analyses, min_matches=2, max_matches=4) if len(analyses) >= 2 else None
    systems_list = generate_systems(analyses) if len(analyses) >= 3 else None
    result = format_for_telegram(analyses, express_list, systems_list)
    result = f"📊 <b>{len(matches)} матчей</b> (сохранено: {saved})\n\n" + result
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

@bot.message_handler(func=lambda m: not WAITING_FOR_TEXT.get(m.chat.id, False) and not WAITING_FOR_BET.get(m.chat.id))
def search_match(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Напиши две команды: `Зенит Спартак`", 
                        parse_mode='Markdown', reply_markup=main_menu_keyboard())
        return
    h2h = []
    for m in MATCHES:
        home_in = any(q.lower() in m['home'] for q in parts)
        away_in = any(q.lower() in m['away'] for q in parts)
        if home_in and away_in: h2h.append(m)
    if not h2h:
        bot.send_message(message.chat.id, "❌ Личных встреч не найдено", reply_markup=main_menu_keyboard())
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
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_menu_keyboard())

print("🤖 Бот запущен...")
bot.infinity_polling()
