import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

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
                di = idx.get('Date')
            elif 'Home' in idx:
                hi, ai, ri = idx.get('Home'), idx.get('Away'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
                di = idx.get('Date')
            else:
                hi, ai, ri, di = 5, 6, 9, 3
                bh, bd, ba = 10, 11, 12
            if hi is None or ai is None: continue
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai): continue
                try:
                    date_str = p[di].strip() if di is not None and len(p) > di else ''
                    res = p[ri].strip() if ri is not None and len(p) > ri and p[ri].strip() else None
                    h_odd = float(p[bh]) if bh is not None and len(p) > bh and p[bh] else None
                    d_odd = float(p[bd]) if bd is not None and len(p) > bd and p[bd] else None
                    a_odd = float(p[ba]) if ba is not None and len(p) > ba and p[ba] else None
                    matches.append({
                        'date': date_str,
                        'home': p[hi].strip().lower(), 'away': p[ai].strip().lower(),
                        'res': res,
                        'h_odd': h_odd, 'd_odd': d_odd, 'a_odd': a_odd,
                        'league': league
                    })
                except: pass
    return matches

def find_patterns(matches, min_sample=30, min_edge=10):
    ranges = {}
    for m in matches:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1 and m['res']:
            key = (round(m['h_odd'],1), round(m['d_odd'],1), round(m['a_odd'],1))
            if key not in ranges: ranges[key] = []
            ranges[key].append(m)
    patterns = []
    for (h,d,a), group in ranges.items():
        if len(group) < min_sample: continue
        inv = 1/h + 1/d + 1/a
        fh,fd,fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
        hw = sum(1 for m in group if m['res']=='H')/len(group)*100
        dw = sum(1 for m in group if m['res']=='D')/len(group)*100
        aw = sum(1 for m in group if m['res']=='A')/len(group)*100
        if hw - fh > 5:
            patterns.append({'range':(h,d,a),'bet':'П1','odds':h,'fair':fh,'real':hw,'edge':hw-fh,'roi':(hw/100*h-1)*100,'n':len(group)})
        if dw - fd > 5:
            patterns.append({'range':(h,d,a),'bet':'Ничья','odds':d,'fair':fd,'real':dw,'edge':dw-fd,'roi':(dw/100*d-1)*100,'n':len(group)})
        if aw - fa > 5:
            patterns.append({'range':(h,d,a),'bet':'П2','odds':a,'fair':fa,'real':aw,'edge':aw-fa,'roi':(aw/100*a-1)*100,'n':len(group)})
    patterns.sort(key=lambda x: x['roi'], reverse=True)
    return patterns

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID: 
        print("❌ Telegram credentials not set")
        return False
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    try:
        r = requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def main():
    matches = load_matches()
    patterns = find_patterns(matches, min_sample=30, min_edge=10)
    
    msg = f"⚽ <b>Daily Report</b> {datetime.now().strftime('%d.%m.%Y')}\n"
    msg += f"📊 База: {len(matches)} матчей | Паттерны: {len(patterns)}\n\n"
    
    msg += "<b>Топ исторических паттернов:</b>\n"
    for i, p in enumerate(patterns[:5], 1):
        emoji = "🟢" if p['roi']>20 else "🟡"
        msg += f"{emoji} #{i} {p['bet']} @ {p['odds']:.1f} | ROI {p['roi']:+.0f}% | N={p['n']}\n"
    
    if send_telegram(msg):
        print("✅ Отправлено")
    else:
        print(" Не отправлено")

if __name__ == "__main__":
    main()
