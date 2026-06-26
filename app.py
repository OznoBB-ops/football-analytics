import streamlit as st
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="Football Analyzer", layout="wide")
st.title("⚽ Football Analyzer")

@st.cache_data
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
                hg_idx, ag_idx = idx.get('FTHG'), idx.get('FTAG')
            elif 'Home' in idx:
                hi, ai, ri = idx.get('Home'), idx.get('Away'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
                hg_idx, ag_idx = idx.get('FTHG'), idx.get('FTAG')
            else:
                hi, ai, ri = 5, 6, 9
                bh, bd, ba = 10, 11, 12
                hg_idx, ag_idx = 7, 8
            
            if hi is None or ai is None or ri is None:
                continue
            
            for line in f:
                p = line.strip().split(',')
                if len(p) <= max(hi, ai, ri):
                    continue
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
                        'hg': hg,
                        'ag': ag,
                        'league': league
                    })
                except:
                    pass
    return matches

matches = load_matches()
st.sidebar.success(f"✅ {len(matches)} матчей в базе")

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Поиск матча", "🎯 Валуи", "📊 Статистика", "📈 Графики"])

# === ВКЛАДКА 1: ПОИСК МАТЧА ===
with tab1:
    col1, col2 = st.columns(2)
    with col1: home = st.text_input("🏠 Хозяева", value="zenit").lower().strip()
    with col2: away = st.text_input("🛫 Гости", value="spartak moscow").lower().strip()
    
    if st.button("📊 Рассчитать", use_container_width=True):
        h2h = [m for m in matches 
               if (m['home']==home and m['away']==away) or 
                  (m['home']==away and m['away']==home)]
        
        st.markdown(f"### {home.upper()} vs {away.upper()}")
        
        if h2h:
            hw = sum(1 for m in h2h if (m['home']==home and m['res']=='H') or (m['away']==home and m['res']=='A'))
            aw = sum(1 for m in h2h if (m['home']==away and m['res']=='H') or (m['away']==away and m['res']=='A'))
            dr = sum(1 for m in h2h if m['res']=='D')
            total = len(h2h)
            
            c1,c2,c3 = st.columns(3)
            c1.metric("П1", f"{hw/total*100:.1f}%", f"{hw} побед")
            c2.metric("Ничья", f"{dr/total*100:.1f}%", f"{dr}")
            c3.metric("П2", f"{aw/total*100:.1f}%", f"{aw} побед")

            # Тоталы и ОЗ
            over25 = sum(1 for m in h2h if m['hg'] + m['ag'] > 2.5)
            btts = sum(1 for m in h2h if m['hg'] > 0 and m['ag'] > 0)
            c4, c5 = st.columns(2)
            c4.metric("ТБ 2.5", f"{over25/total*100:.1f}%")
            c5.metric("Обе забьют", f"{btts/total*100:.1f}%")
        else:
            st.warning("⚠️ Личных встреч не найдено")

# === ВКЛАДКА 2: ВАЛУИ ===
with tab2:
    st.header("🎯 Исторические валуи")
    min_edge = st.slider("Минимальное преимущество (%)", 3, 15, 5)
    min_sample = st.slider("Минимальная выборка", 10, 50, 20)
    
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
        fh, fd, fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
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
        st.markdown(f"{color} **Кэфы {v['range']}** → **{v['bet']} @ {v['odds']:.1f}** | Edge: +{v['edge']:.1f}% | ROI: {v['roi']:+.1f}% | N={v['n']}")

# === ВКЛАДКА 3: СТАТИСТИКА ===
with tab3:
    team = st.text_input("Название команды", value="zenit").lower().strip()
    if st.button("📊 Показать статистику"):
        team_matches = [m for m in matches if team in m['home'] or team in m['away']]
        if team_matches:
            total = len(team_matches)
            wins = sum(1 for m in team_matches if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'))
            st.metric("Винрейт", f"{wins/total*100:.1f}%", f"{wins} из {total}")
            
            # Форма
            last10 = team_matches[-10:]
            form_str = ""
            for m in last10:
                if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'): form_str += "✅"
                elif m['res']=='D': form_str += "⚪"
                else: form_str += "❌"
            st.markdown(f"**Форма (10 матчей):** {form_str}")

# === ВКЛАДКА 4: ГРАФИКИ ===
with tab4:
    st.header("📈 Аналитика по лигам")
    
    # Статистика лиг (Тоталы и ОЗ)
    st.subheader("Тотал больше 2.5 и Обе забьют по лигам")
    league_stats = {}
    for m in matches:
        l = m['league']
        if l not in league_stats:
            league_stats[l] = {'total':0, 'over25':0, 'btts':0}
        league_stats[l]['total'] += 1
        if m['hg'] + m['ag'] > 2.5:
            league_stats[l]['over25'] += 1
        if m['hg'] > 0 and m['ag'] > 0:
            league_stats[l]['btts'] += 1
    
    data = []
    for l, s in sorted(league_stats.items()):
        if s['total'] > 10:
            data.append({
                'Лига': l,
                'Матчей': s['total'],
                'ТБ 2.5 %': round(s['over25']/s['total']*100, 1),
                'ОЗ %': round(s['btts']/s['total']*100, 1)
            })
    st.table(data)
    
    # График формы команды
    st.subheader("График голов команды")
    team_chart = st.text_input("Команда для графика", value="zenit").lower().strip()
    if st.button("Построить график"):
        chart_matches = [m for m in matches if team_chart in m['home'] or team_chart in m['away']][-20:]
        if chart_matches:
            goals_for = []
            goals_against = []
            labels = []
            for m in chart_matches:
                if m['home'] == team_chart:
                    goals_for.append(m['hg'])
                    goals_against.append(m['ag'])
                    labels.append(f"vs {m['away'][:3]}")
                else:
                    goals_for.append(m['ag'])
                    goals_against.append(m['hg'])
                    labels.append(f"vs {m['home'][:3]}")
            
            fig, ax = plt.subplots(figsize=(10, 4))
            x = range(len(labels))
            ax.bar([i - 0.2 for i in x], goals_for, 0.4, label='Забито', color='green')
            ax.bar([i + 0.2 for i in x], goals_against, 0.4, label='Пропущено', color='red')
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
            ax.legend()
            ax.set_title(f"Голы {team_chart.upper()} (последние 20)")
            st.pyplot(fig)
