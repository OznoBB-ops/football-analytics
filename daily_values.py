import requests
import os
from datetime import datetime

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
                hg_idx, ag_idx = idx.get('FTHG'), idx.get('FTAG')
            elif 'Home' in idx:
                hi, ai, ri = idx.get('Home'), idx.get('Away'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
                hg_idx, ag_idx = idx.get('FTHG'), idx.get('FTAG')
            else:
                hi, ai, ri, hg_idx, ag_idx = 5, 6, 9, 7, 8
                bh, bd, ba = 10, 11, 12
            if hi is None or ai is None or ri is None: continue
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai, ri): continue
                try:
                    hg = int(p[hg_idx]) if hg_idx is not None and len(p) > hg_idx and p[hg_idx] else 0
                    ag = int(p[ag_idx]) if ag_idx is not None and len(p) > ag_idx and p[ag_idx] else 0
                    matches.append({
                        'home': p[hi].strip().lower(), 'away': p[ai].strip().lower(),
                        'res': p[ri].strip() if p[ri].strip() else None,
                        'h_odd': float(p[bh]) if bh is not None and len(p) > bh and p[bh] else None,
                        'd_odd': float(p[bd]) if bd is not None and len(p) > bd and p[bd] else None,
                        'a_odd': float(p[ba]) if ba is not None and len(p) > ba and p[ba] else None,
                        'hg': hg, 'ag': ag, 'total': hg+ag, 'league': league
                    })
                except: pass
    return matches

def find_values(matches, min_edge=5, min_sample=30, top_n=10):
    ranges = {}
    for m in matches:
        if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1 and m['res']:
            key = (round(m['h_odd'],1), round(m['d_odd'],1), round(m['a_odd'],1))
            if key not in ranges: ranges[key] = []
            ranges[key].append(m)
    values = []
    for (h,d,a), group in ranges.items():
        if len(group) < min_sample: continue
        inv = 1/h + 1/d + 1/a
        fh,fd,fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
        hw = sum(1 for m in group if m['res']=='H')/len(group)*100
        dw = sum(1 for m in group if m['res']=='D')/len(group)*100
        aw = sum(1 for m in group if m['res']=='A')/len(group)*100
        if hw - fh > min_edge:
            values.append({'range':f'{h}/{d}/{a}','bet':'П1','odds':h,'fair':fh,'real':hw,'edge':hw-fh,'roi':(hw/100*h-1)*100,'n':len(group)})
        if dw - fd > min_edge:
            values.append({'range':f'{h}/{d}/{a}','bet':'Ничья','odds':d,'fair':fd,'real':dw,'edge':dw-fd,'roi':(dw/100*d-1)*100,'n':len(group)})
        if aw - fa > min_edge:
            values.append({'range':f'{h}/{d}/{a}','bet':'П2','odds':a,'fair':fa,'real':aw,'edge':aw-fa,'roi':(aw/100*a-1)*100,'n':len(group)})
    values.sort(key=lambda x: x['roi'], reverse=True)
    return values[:top_n]

def league_totals(matches):
    stats = {}
    for m in matches:
        l = m['league']
        if l not in stats: stats[l] = {'t':0,'o25':0,'btts':0}
        stats[l]['t'] += 1
        if m['total'] > 2.5: stats[l]['o25'] += 1
        if m['hg']>0 and m['ag']>0: stats[l]['btts'] += 1
    return stats

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID: return False
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    try:
        r = requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}, timeout=10)
        return r.status_code == 200
    except: return False

def main():
    matches = load_matches()
    values = find_values(matches, min_edge=5, min_sample=30, top_n=8)
    totals = league_totals(matches)
    
    msg = f"⚽ <b>Daily Report</b> {datetime.now().strftime('%d.%m')}\n"
    msg += f"База: {len(matches)} матчей\n\n"
    
    msg += "<b> Топ валуи:</b>\n"
    if values:
        for i, v in enumerate(values, 1):
            emoji = "🟢" if v['roi']>20 else "🟡"
            msg += f"{emoji} #{i} {v['bet']} @ {v['odds']:.1f} | Edge +{v['edge']:.1f}% | ROI {v['roi']:+.0f}%\n"
    else:
        msg += "❌ Не найдено\n"
    
    msg += "\n<b> Тоталы по лигам:</b>\n"
    for l, s in sorted(totals.items()):
        if s['t'] > 10:
            msg += f"• {l}: ТБ2.5 {s['o25']/s['t']*100:.0f}% | ОЗ {s['btts']/s['t']*100:.0f}% ({s['t']} игр)\n"
    
    send_telegram(msg)
    print("✅ Отправлено")

if __name__ == "__main__":
    main()
