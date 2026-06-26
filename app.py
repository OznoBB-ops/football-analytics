import streamlit as st
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="Football Analyzer", layout="wide")
st.title("⚽ Football Analyzer")

@st.cache_data
def load_matches():
    matches = []
    files = ['RUS.csv','FIN.csv','POL.csv','P1.csv','E0.csv','E1.csv',
             'D1.csv','SP1.csv','I1.csv','N1.csv','B1.csv','TU1.csv','SC1.csv','G1.csv']
    
    for fname in files:
        if not os.path.exists(fname):
            continue
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
                hi, ai, ri = 5, 6, 9
                bh, bd, ba = 10, 11, 12
                hg_idx, ag_idx = 7, 8
            
            if hi is None or ai is None or ri is None: continue
            
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai, ri): continue
                try:
                    hg = int(p[hg_idx]) if hg_idx is not None and len(p) > hg_idx and p[hg_idx] else 0
                    ag = int(p[ag_idx]) if ag_idx is not None and len(p) > ag_idx and p[ag_idx] else 0
                    matches.append({
                        'home': p[hi].strip().lower(),
                        'away': p[ai].strip().lower(),
                        'res': p[ri].strip() if p[ri].strip() else None,
                        'h_odd': float(p[bh]) if bh is not None and len(p) > bh and p[bh] else None,
                        'd_odd': float(p[bd]) if bd is not None and len(p) > bd and p[bd] else None,
                        'a_odd': float(p[ba]) if ba is not None and len(p) > ba and p[ba] else None,
                        'hg': hg, 'ag': ag, 'total': hg+ag, 'league': league
                    })
                except: pass
    return matches

matches = load_matches()
st.sidebar.success(f"✅ {len(matches)} матчей из {len(set(m['league'] for m in matches))} лиг")

tab1, tab2, tab3, tab4, tab5 = st.tabs([" Матч", "🎯 Валуи", "📊 Команда", " Графики", "⚽ Тоталы"])

# === ВКЛАДКА 1: МАТЧ ===
with tab1:
    col1, col2 = st.columns(2)
    with col1: home = st.text_input("Хозяева", value="zenit").lower().strip()
    with col2: away = st.text_input("Гости", value="spartak moscow").lower().strip()
    
    if st.button("Рассчитать", use_container_width=True):
        h2h = [m for m in matches if (m['home']==home and m['away']==away) or (m['home']==away and m['away']==home)]
        st.markdown(f"### {home.upper()} vs {away.upper()}")
        
        if h2h:
            hw = sum(1 for m in h2h if (m['home']==home and m['res']=='H') or (m['away']==home and m['res']=='A'))
            aw = sum(1 for m in h2h if (m['home']==away and m['res']=='H') or (m['away']==away and m['res']=='A'))
            dr = sum(1 for m in h2h if m['res']=='D')
            total = len(h2h)
            
            c1,c2,c3 = st.columns(3)
            c1.metric("П1", f"{hw/total*100:.1f}%", f"{hw}")
            c2.metric("Ничья", f"{dr/total*100:.1f}%", f"{dr}")
            c3.metric("П2", f"{aw/total*100:.1f}%", f"{aw}")
            
            # Тоталы
            over15 = sum(1 for m in h2h if m['total'] > 1.5)
            over25 = sum(1 for m in h2h if m['total'] > 2.5)
            over35 = sum(1 for m in h2h if m['total'] > 3.5)
            btts = sum(1 for m in h2h if m['hg']>0 and m['ag']>0)
            
            st.markdown("#### Тоталы и ОЗ")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("ТБ 1.5", f"{over15/total*100:.0f}%")
            c2.metric("ТБ 2.5", f"{over25/total*100:.0f}%")
            c3.metric("ТБ 3.5", f"{over35/total*100:.0f}%")
            c4.metric("ОЗ", f"{btts/total*100:.0f}%")
        
        odds = [m for m in h2h if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1]
        if odds:
            last = odds[-1]
            h,d,a = last['h_odd'], last['d_odd'], last['a_odd']
            inv = 1/h + 1/d + 1/a
            fh,fd,fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
            st.markdown(f"**Fair odds** (маржа {(inv-1)*100:.1f}%): П1 {fh:.0f}% | Х {fd:.0f}% | П2 {fa:.0f}%")
            st.info(f"Валуй П1 если кэф > {100/fh:.2f} | Валуй П2 если кэф > {100/fa:.2f}")

# === ВКЛАДКА 2: ВАЛУИ ===
with tab2:
    st.header("Исторические валуи")
    min_edge = st.slider("Мин. преимущество (%)", 3, 15, 5)
    min_sample = st.slider("Мин. выборка", 10, 100, 30)
    
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
    for v in values[:30]:
        color = "🟢" if v['roi'] > 20 else ("🟡" if v['roi'] > 10 else "🔵")
        st.markdown(f"{color} **{v['range']}** → **{v['bet']} @ {v['odds']:.1f}** | Edge +{v['edge']:.1f}% | ROI {v['roi']:+.1f}% | N={v['n']}")

# === ВКЛАДКА 3: КОМАНДА ===
with tab3:
    team = st.text_input("Команда", value="zenit").lower().strip()
    if st.button("Статистика"):
        tm = [m for m in matches if team in m['home'] or team in m['away']]
        if not tm:
            st.warning("Не найдена")
        else:
            total = len(tm)
            wins = sum(1 for m in tm if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'))
            draws = sum(1 for m in tm if m['res']=='D')
            losses = total - wins - draws
            
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Матчей", total)
            c2.metric("Побед", f"{wins/total*100:.0f}%")
            c3.metric("Ничьих", f"{draws/total*100:.0f}%")
            c4.metric("Поражений", f"{losses/total*100:.0f}%")
            
            # По лигам
            st.markdown("### По лигам")
            leagues = {}
            for m in tm:
                l = m['league']
                if l not in leagues: leagues[l] = {'w':0,'d':0,'l':0,'t':0,'gf':0,'ga':0}
                leagues[l]['t'] += 1
                if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'): leagues[l]['w'] += 1
                elif m['res']=='D': leagues[l]['d'] += 1
                else: leagues[l]['l'] += 1
                if m['home']==team: leagues[l]['gf'] += m['hg']; leagues[l]['ga'] += m['ag']
                else: leagues[l]['gf'] += m['ag']; leagues[l]['ga'] += m['hg']
            
            for l, s in sorted(leagues.items()):
                t = s['t']
                st.markdown(f"**{l}** ({t}): ✅{s['w']} {s['d']} ❌{s['l']} | Голы {s['gf']}-{s['ga']} | WR {s['w']/t*100:.0f}%")
            
            # Форма
            st.markdown("### Последние 10")
            last10 = tm[-10:]
            form = ""
            for m in last10:
                if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'): form += "✅"
                elif m['res']=='D': form += ""
                else: form += "❌"
            st.markdown(f"**{form}**")

# === ВКЛАДКА 4: ГРАФИКИ ===
with tab4:
    st.header("Графики")
    team_chart = st.text_input("Команда для графика", value="zenit").lower().strip()
    if st.button("Построить"):
        cm = [m for m in matches if team_chart in m['home'] or team_chart in m['away']][-20:]
        if cm:
            gf, ga, labels = [], [], []
            for m in cm:
                if m['home'] == team_chart:
                    gf.append(m['hg']); ga.append(m['ag']); labels.append(f"vs {m['away'][:3]}")
                else:
                    gf.append(m['ag']); ga.append(m['hg']); labels.append(f"vs {m['home'][:3]}")
            
            fig, ax = plt.subplots(figsize=(10, 4))
            x = range(len(labels))
            ax.bar([i-0.2 for i in x], gf, 0.4, label='Забито', color='green')
            ax.bar([i+0.2 for i in x], ga, 0.4, label='Пропущено', color='red')
            ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
            ax.legend(); ax.set_title(f"Голы {team_chart.upper()} (20 матчей)")
            st.pyplot(fig)

# === ВКЛАДКА 5: ТОТАЛЫ ПО ЛИГАМ ===
with tab5:
    st.header("Статистика тоталов по лигам")
    
    league_stats = {}
    for m in matches:
        l = m['league']
        if l not in league_stats:
            league_stats[l] = {'total':0, 'over15':0, 'over25':0, 'over35':0, 'btts':0, 'goals':0}
        league_stats[l]['total'] += 1
        league_stats[l]['goals'] += m['total']
        if m['total'] > 1.5: league_stats[l]['over15'] += 1
        if m['total'] > 2.5: league_stats[l]['over25'] += 1
        if m['total'] > 3.5: league_stats[l]['over35'] += 1
        if m['hg']>0 and m['ag']>0: league_stats[l]['btts'] += 1
    
    data = []
    for l, s in sorted(league_stats.items()):
        t = s['total']
        if t > 10:
            data.append({
                'Лига': l,
                'Матчей': t,
                'Ср. голов': round(s['goals']/t, 2),
                'ТБ 1.5 %': round(s['over15']/t*100, 1),
                'ТБ 2.5 %': round(s['over25']/t*100, 1),
                'ТБ 3.5 %': round(s['over35']/t*100, 1),
                'ОЗ %': round(s['btts']/t*100, 1)
            })
    st.table(data)
    
    # График
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    leagues = [d['Лига'] for d in data]
    over25 = [d['ТБ 2.5 %'] for d in data]
    btts = [d['ОЗ %'] for d in data]
    
    axes[0].barh(leagues, over25, color='blue')
    axes[0].set_title('ТБ 2.5 по лигам (%)')
    axes[0].set_xlabel('%')
    
    axes[1].barh(leagues, btts, color='green')
    axes[1].set_title('Обе забьют по лигам (%)')
    axes[1].set_xlabel('%')
    
    plt.tight_layout()
    st.pyplot(fig)
