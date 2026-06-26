import streamlit as st
import os

st.set_page_config(page_title="Football Analyzer", layout="wide")
st.title("⚽ Football Analyzer")

# === ЗАГРУЗКА ДАННЫХ ===
@st.cache_data
def load_matches():
    matches = []
    
    # Все лиги с заголовками (формат football-data.co.uk)
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
            
            # Определяем формат
            if 'HomeTeam' in idx:
                hi, ai, ri = idx.get('HomeTeam'), idx.get('AwayTeam'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
            elif 'Home' in idx:
                hi, ai, ri = idx.get('Home'), idx.get('Away'), idx.get('FTR')
                bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
            else:
                # Без заголовков — позиции фиксированы
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

matches = load_matches()
st.sidebar.success(f"✅ {len(matches)} матчей в базе")

# === ВКЛАДКИ ===
tab1, tab2, tab3 = st.tabs(["🔍 Поиск матча", "🎯 Валуи", "📊 Статистика"])

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
        else:
            st.warning("⚠️ Личных встреч не найдено")
        
        odds = [m for m in h2h if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1]
        if odds:
            last = odds[-1]
            h,d,a = last['h_odd'], last['d_odd'], last['a_odd']
            inv = 1/h + 1/d + 1/a
            margin = (inv-1)*100
            fh,fd,fa = (1/h/inv)*100, (1/d/inv)*100, (1/a/inv)*100
            
            st.markdown(f"**💰 Честные шансы** (кэфы {h}/{d}/{a}, маржа {margin:.1f}%):")
            c1,c2,c3 = st.columns(3)
            c1.metric("П1 fair", f"{fh:.1f}%")
            c2.metric("Ничья fair", f"{fd:.1f}%")
            c3.metric("П2 fair", f"{fa:.1f}%")
            
            st.info(f"🎯 Валуй П1: кэф БК > **{100/fh:.2f}**")
            st.info(f"🎯 Валуй П2: кэф БК > **{100/fa:.2f}**")

# === ВКЛАДКА 2: ВАЛУИ ===
with tab2:
    st.header("🎯 Исторические валуи")
    st.caption("Паттерны, где БК систематически ошибается. Используй для поиска похожих матчей в линии.")
    
    min_edge = st.slider("Минимальное преимущество (%)", 3, 15, 5)
    min_sample = st.slider("Минимальная выборка", 10, 50, 20)
    
    league_filter = st.multiselect("Фильтр по лигам", 
        ['RUS','FIN','POL','P1','E0','E1','D1','SP1','I1','N1'],
        default=['RUS','FIN','POL','P1','E0','E1','D1','SP1','I1','N1'])
    
    filtered = [m for m in matches if m['league'] in league_filter]
    
    ranges = {}
    for m in filtered:
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
    
    if not values:
        st.warning("Валуев не найдено. Попробуй уменьшить минимальное преимущество.")
    else:
        st.markdown(f"### Найдено {len(values)} паттернов")
        
        for v in values[:30]:
            color = "🟢" if v['roi'] > 20 else ("🟡" if v['roi'] > 10 else "🔵")
            st.markdown(f"""
            {color} **Кэфы {v['range']}** → Ставка: **{v['bet']} @ {v['odds']:.1f}**
            - Fair: {v['fair']:.0f}% → Реальность: {v['real']:.0f}% | Edge: +{v['edge']:.1f}% | ROI: {v['roi']:+.1f}% | N={v['n']}
            """)

# === ВКЛАДКА 3: СТАТИСТИКА ===
with tab3:
    team = st.text_input("Название команды", value="zenit").lower().strip()
    
    if st.button("📊 Показать статистику"):
        team_matches = [m for m in matches if team in m['home'] or team in m['away']]
        
        if not team_matches:
            st.warning(f"Команда '{team}' не найдена")
        else:
            total = len(team_matches)
            wins = sum(1 for m in team_matches if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'))
            draws = sum(1 for m in team_matches if m['res']=='D')
            losses = total - wins - draws
            
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Матчей", total)
            c2.metric("Побед", f"{wins} ({wins/total*100:.0f}%)")
            c3.metric("Ничьих", f"{draws} ({draws/total*100:.0f}%)")
            c4.metric("Поражений", f"{losses} ({losses/total*100:.0f}%)")
            
            # По лигам
            st.markdown("### По лигам")
            leagues = {}
            for m in team_matches:
                if m['league'] not in leagues:
                    leagues[m['league']] = {'w':0,'d':0,'l':0,'t':0}
                leagues[m['league']]['t'] += 1
                if (m['home']==team and m['res']=='H') or (m['away']==team and m['res']=='A'):
                    leagues[m['league']]['w'] += 1
                elif m['res']=='D':
                    leagues[m['league']]['d'] += 1
                else:
                    leagues[m['league']]['l'] += 1
            
            for league, stats in sorted(leagues.items()):
                t = stats['t']
                st.markdown(f"**{league}** ({t} матчей): ✅{stats['w']} ⚪{stats['d']} ❌{stats['l']} | Win rate: {stats['w']/t*100:.0f}%")
            
            # Форма
            st.markdown("### Последние 10 матчей")
            last10 = team_matches[-10:]
            for m in last10:
                if m['home']==team:
                    res = "✅" if m['res']=='H' else ("⚪" if m['res']=='D' else "❌")
                    st.text(f"{res} {m['home']} vs {m['away']} ({m['league']})")
                else:
                    res = "✅" if m['res']=='A' else ("⚪" if m['res']=='D' else "❌")
                    st.text(f"{res} {m['home']} vs {m['away']} ({m['league']})")
