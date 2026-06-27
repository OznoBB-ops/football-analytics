import telebot
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
    exit(1)

bot = telebot.TeleBot(TOKEN)
TRACKED_FILE = 'tracked.json'

def load_matches():
    matches = []
    files = ['RUS.csv','FIN.csv','POL.csv','P1.csv','E0.csv','E1.csv',
             'D1.csv','SP1.csv','I1.csv','N1.csv','B1.csv','TU1.csv','SC1.csv','G1.csv']
    
    for fname in files:
        if not os.path.exists(fname): continue
        league = fname.replace('.csv','')
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            header = f.readline().strip().split(',')
            if not header: continue
            idx = {h.strip(): i for i, h in enumerate(header)}
            
            if 'HomeTeam' in idx:
                hi, ai, ri = idx.get('HomeTeam'), idx.get('AwayTeam'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
            elif 'Home' in idx:
                hi, ai, ri = idx.get('Home'), idx.get('Away'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
            else:
                hi, ai, ri = 5, 6, 9
                bh, bd, ba = 10, 11, 12
            
            if hi is None or ai is None or ri is None: continue
            
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai, ri): continue
                try:
                    matches.append({
                        'home': p[hi].strip().lower(),
                        'away': p[ai].strip().lower(),
                        'res': p[ri].strip() if p[ri].strip() else None,
                        'h_odd': float(p[bh]) if bh is not None and len(p) > bh and p[bh] else None,
                        'd_odd': float(p[bd]) if bd is not None and len(p) > bd and p[bd] else None,
                        'a_odd': float(p[ba]) if ba is not None and len(p) > ba and p[ba] else None,
                        'league': league
                    })
                except: pass
    return matches

MATCHES = load_matches()
print(f"✅ Загружено {len(MATCHES)} матчей")

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

🔍 *Поиск матча:*
Напиши две команды: `Zenit Spartak`

📌 *Подписки:*
/track Zenit — следить за командой
/untrack Zenit — отписаться
/tracked — список твоих команд
/check — отчет по последним матчам

 *Аналитика:*
/values — исторические валуи
/stats Zenit — статистика команды
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['track'])
def track_team(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /track zenit")
        return
    
    team = args[1].strip().lower()
    user_id = str(message.chat.id)
    tracked = load_tracked()
    
    if user_id not in tracked:
        tracked[user_id] = []
    
    if team in tracked[user_id]:
        bot.send_message(message.chat.id, f"⚠️ Ты уже следишь за {team}")
        return
    
    exists = any(team in m['home'] or team in m['away'] for m in MATCHES)
    if not exists:
        bot.send_message(message.chat.id, f"❌ Команда '{team}' не найдена в базе")
        return
    
    tracked[user_id].append(team)
    save_tracked(tracked)
    bot.send_message(message.chat.id, f"✅ Теперь я слежу за {team.upper()}")

@bot.message_handler(commands=['untrack'])
def untrack_team(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /untrack zenit")
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
        bot.send_message(message.chat.id, " Список пуст. Добавь команды через /track")
        return
    
    teams = "\n".join([f"• {t.upper()}" for t in tracked[user_id]])
    bot.send_message(message.chat.id, f"📌 *Твои команды:*\n{teams}", parse_mode='Markdown')

@bot.message_handler(commands=['check'])
def check_tracked(message):
    user_id = str(message.chat.id)
    tracked = load_tracked()
    
    if user_id not in tracked or not tracked[user_id]:
        bot.send_message(message.chat.id, "Сначала добавь команды через /track")
        return
    
    report = "📊 <b>Последние матчи твоих команд:</b>\n\n"
    
    for team in tracked[user_id]:
        team_matches = [m for m in MATCHES if team in m['home'] or team in m['away']]
        if team_matches:
            last = team_matches[-1]
            report += f"⚽ <b>{team.upper()}</b> ({last['league']})\n"
            report += f"   {last['home']} vs {last['away']}\n"
            if last['h_odd']:
                report += f"   Кэфы: {last['h_odd']}/{last['d_odd']}/{last['a_odd']}\n"
            report += "\n"
    
    bot.send_message(message.chat.id, report, parse_mode='HTML')

@bot.message_handler(commands=['values'])
def send_values(message):
    ranges = {}
    for m in MATCHES:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd'] > 1 and m['res']:
            key = (round(m['h_odd'], 1), round(m['d_odd'], 1), round(m['a_odd'], 1))
            if key not in ranges: ranges[key] = []
            ranges[key].append(m)
    
    values = []
    for (h, d, a), group in ranges.items():
        if len(group) < 20: continue
        inv = 1/h + 1/d + 1/a
        fh = (1/h/inv)*100; fd = (1/d/inv)*100; fa = (1/a/inv)*100
        hw = sum(1 for m in group if m['res']=='H')/len(group)*100
        dw = sum(1 for m in group if m['res']=='D')/len(group)*100
        aw = sum(1 for m in group if m['res']=='A')/len(group)*100
        
        if hw - fh > 5: values.append(f"🎯 П1 @ {h:.1f} (fair {fh:.0f}% → real {hw:.0f}%) N={len(group)}")
        if dw - fd > 5: values.append(f"🎯 Ничья @ {d:.1f} (fair {fd:.0f}% → real {dw:.0f}%) N={len(group)}")
        if aw - fa > 5: values.append(f" П2 @ {a:.1f} (fair {fa:.0f}% → real {aw:.0f}%) N={len(group)}")
    
    if not values:
        bot.send_message(message.chat.id, "❌ Валуйных паттернов не найдено")
        return
    
    text = " *Топ валуи из истории:*\n\n" + "\n".join(values[:15])
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def send_stats(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Используй: /stats zenit")
        return
    
    team = args[1].strip().lower()
    team_matches = [m for m in MATCHES if team in m['home'] or team in m['away']]
    
    if not team_matches:
        bot.send_message(message.chat.id, f"❌ Команда '{team}' не найдена")
        return
    
    total = len(team_matches)
    wins = sum(1 for m in team_matches if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'))
    draws = sum(1 for m in team_matches if m['res']=='D')
    losses = total - wins - draws
    
    last5 = team_matches[-5:]
    form = ""
    for m in last5:
        if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'): form += "✅"
        elif m['res']=='D': form += "⚪"
        else: form += "❌"
    
    text = f"📊 *{team.upper()}*\nВсего матчей: {total}\nПобед: {wins} ({wins/total*100:.0f}%)\nНичьих: {draws} ({draws/total*100:.0f}%)\nПоражений: {losses} ({losses/total*100:.0f}%)\n\nФорма (5): {form}"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def search_match(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Напиши две команды: `Zenit Spartak`", parse_mode='Markdown')
        return
    
    h2h = []
    for m in MATCHES:
        home_in = any(q in m['home'] for q in parts)
        away_in = any(q in m['away'] for q in parts)
        if home_in and away_in: h2h.append(m)
    
    if not h2h:
        bot.send_message(message.chat.id, f"❌ Личных встреч не найдено.")
        return
    
    total = len(h2h)
    hw = sum(1 for m in h2h if (m['home']==h2h[0]['home'] and m['res']=='H') or (m['away']==h2h[0]['home'] and m['res']=='A'))
    aw = sum(1 for m in h2h if (m['home']==h2h[0]['away'] and m['res']=='H') or (m['away']==h2h[0]['away'] and m['res']=='A'))
    dr = sum(1 for m in h2h if m['res']=='D')
    
    text = f"🔍 *{h2h[0]['home'].title()} vs {h2h[0]['away'].title()}*\nЛичных встреч: {total}\n\n📊 П1: {hw/total*100:.0f}% ({hw})\n⚪ Ничья: {dr/total*100:.0f}% ({dr})\n📊 П2: {aw/total*100:.0f}% ({aw})"
    
    odds = [m for m in h2h if m['h_odd'] and m['h_odd'] > 1]
    if odds:
        last = odds[-1]
        inv = 1/last['h_odd'] + 1/last['d_odd'] + 1/last['a_odd']
        fh = (1/last['h_odd']/inv)*100
        fa = (1/last['a_odd']/inv)*100
        text += f"\n\n💰 Fair: П1 {fh:.0f}% | П2 {fa:.0f}%\n🎯 Валуй П1 если кэф > {100/fh:.2f}\n🎯 Валуй П2 если кэф > {100/fa:.2f}"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

print("🤖 Бот запущен...")
bot.infinity_polling()
