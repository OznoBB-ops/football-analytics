import requests
import os
import csv
from datetime import datetime, timedelta

# Telegram
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def load_matches():
    matches = []
    files = ['RUS.csv','FIN.csv','POL.csv','P1.csv','E0.csv','E1.csv',
             'D1.csv','SP1.csv','I1.csv','N1.csv']
    
    for fname in files:
        if not os.path.exists(fname):
            continue
        league = fname.replace('.csv','')
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            header = f.readline().strip().split(',')
            if not header:
                continue
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
            
            if hi is None or ai is None or ri is None:
                continue
            
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai, ri):
                    continue
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
                except:
                    pass
    return matches

def find_top_values(matches, min_edge=5, min_sample=20, top_n=10):
    ranges = {}
    for m in matches:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1 and m['res']:
            key = (round(m['h_odd'],1), round(m['d_odd'],1), round(m['a_odd'],1))
            if key not in ranges:
                ranges[key] = []
            ranges[key].append(m)
    
    values = []
    for (h,d,a), group in ranges.items():
        if len(group) < min_sample:
            continue
        
        inv = 1/h + 1/d + 1/a
        fh = (1/h/inv)*100
        fd = (1/d/inv)*100
        fa = (1/a/inv)*100
        
        hw = sum(1 for m in group if m['res']=='H')/len(group)*100
        dw = sum(1 for m in group if m['res']=='D')/len(group)*100
        aw = sum(1 for m in group if m['res']=='A')/len(group)*100
        
        if hw - fh > min_edge:
            roi = (hw/100 * h - 1) * 100
            values.append({'range':f'{h}/{d}/{a}','bet':'П1','odds':h,'fair':fh,'real':hw,'edge':hw-fh,'roi':roi,'n':len(group)})
        if dw - fd > min_edge:
            roi = (dw/100 * d - 1) * 100
            values.append({'range':f'{h}/{d}/{a}','bet':'Ничья','odds':d,'fair':fd,'real':dw,'edge':dw-fd,'roi':roi,'n':len(group)})
        if aw - fa > min_edge:
            roi = (aw/100 * a - 1) * 100
            values.append({'range':f'{h}/{d}/{a}','bet':'П2','odds':a,'fair':fa,'real':aw,'edge':aw-fa,'roi':roi,'n':len(group)})
    
    values.sort(key=lambda x: x['roi'], reverse=True)
    return values[:top_n]

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Telegram credentials not set")
        return False
    
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def main():
    print(" Loading matches...")
    matches = load_matches()
    print(f"✅ Loaded {len(matches)} matches")
    
    print("📊 Finding values...")
    values = find_top_values(matches, min_edge=5, min_sample=20, top_n=10)
    
    if not values:
        msg = " <b>Daily Football Report</b>\n\n❌ No value bets found today.\n\nCheck your Streamlit app for manual analysis."
    else:
        msg = f"⚽ <b>Daily Football Report</b>\n📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
        msg += f"🎯 Found <b>{len(values)}</b> value patterns:\n\n"
        
        for i, v in enumerate(values, 1):
            emoji = "🟢" if v['roi'] > 20 else "🟡"
            msg += f"{emoji} <b>#{i} {v['bet']} @ {v['odds']:.1f}</b>\n"
            msg += f"   Odds: {v['range']} | Edge: +{v['edge']:.1f}% | ROI: {v['roi']:+.1f}%\n"
            msg += f"   Fair: {v['fair']:.0f}% → Real: {v['real']:.0f}% | N={v['n']}\n\n"
        
        msg += "💡 <b>How to use:</b>\nFind matches with similar odds in your bookmaker and bet on the highlighted outcome."
    
    print("📤 Sending to Telegram...")
    if send_telegram(msg):
        print("✅ Message sent!")
    else:
        print("❌ Failed to send")

if __name__ == "__main__":
    main()
