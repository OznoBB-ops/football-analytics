import streamlit as st
import csv
import os

st.set_page_config(page_title=" Football Analyzer", layout="centered")
st.title("⚽ Анализ матчей по базе")

@st.cache_data
def load_data():
    matches = []
    
    # RUS.csv — без заголовков, позиции фиксированы
    if os.path.exists('RUS.csv'):
        with open('RUS.csv', 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 13:
                    try:
                        matches.append({
                            'home': parts[5].strip().lower(),
                            'away': parts[6].strip().lower(),
                            'res': parts[9].strip(),
                            'h_odd': float(parts[10]) if parts[10] else None,
                            'd_odd': float(parts[11]) if parts[11] else None,
                            'a_odd': float(parts[12]) if parts[12] else None,
                            'league': 'RUS'
                        })
                    except:
                        pass
    
    # P1.csv — с заголовками
    if os.path.exists('P1.csv'):
        with open('P1.csv', 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                # Ищем индексы колонок
                idx = {h.strip(): i for i, h in enumerate(header)}
                hi = idx.get('HomeTeam')
                ai = idx.get('AwayTeam')
                ri = idx.get('FTR')
                b365h = idx.get('B365H')
                b365d = idx.get('B365D')
                b365a = idx.get('B365A')
                
                if hi and ai and ri:
                    for row in reader:
                        if len(row) > max(hi, ai, ri):
                            try:
                                matches.append({
                                    'home': row[hi].strip().lower(),
                                    'away': row[ai].strip().lower(),
                                    'res': row[ri].strip(),
                                    'h_odd': float(row[b365h]) if b365h and len(row) > b365h and row[b365h] else None,
                                    'd_odd': float(row[b365d]) if b365d and len(row) > b365d and row[b365d] else None,
                                    'a_odd': float(row[b365a]) if b365a and len(row) > b365a and row[b365a] else None,
                                    'league': 'P1'
                                })
                            except:
                                pass
    
    return matches

matches = load_data()
st.success(f"✅ Загружено {len(matches)} матчей")

st.markdown("---")
st.subheader("🔍 Поиск матча")

col1, col2 = st.columns(2)
with col1:
    home = st.text_input("🏠 Хозяева", value="zenit").lower().strip()
with col2:
    away = st.text_input(" Гости", value="spartak moscow").lower().strip()

if st.button(" Рассчитать", use_container_width=True):
    # H2H
    h2h = [m for m in matches if m['home'] == home and m['away'] == away]
    h2h_rev = [m for m in matches if m['home'] == away and m['away'] == home]
    all_h2h = h2h + h2h_rev
    
    st.markdown(f"### {home.upper()} vs {away.upper()}")
    
    if len(all_h2h) >= 1:
        h_wins = sum(1 for m in all_h2h if m['res'] == 'H' and m['home'] == home)
        h_wins += sum(1 for m in all_h2h if m['res'] == 'A' and m['away'] == home)
        
        a_wins = sum(1 for m in all_h2h if m['res'] == 'A' and m['home'] == home)
        a_wins += sum(1 for m in all_h2h if m['res'] == 'H' and m['away'] == home)
        
        draws = sum(1 for m in all_h2h if m['res'] == 'D')
        total = len(all_h2h)
        
        st.markdown(f"**📊 Личные встречи ({total} матчей):**")
        st.metric("П1 (хозяева)", f"{h_wins/total*100:.1f}%", f"{h_wins} побед")
        st.metric("Ничья", f"{draws/total*100:.1f}%", f"{draws} игр")
        st.metric("П2 (гости)", f"{a_wins/total*100:.1f}%", f"{a_wins} побед")
    else:
        st.warning("️ Личных встреч не найдено")
    
    # Fair odds из последнего матча с кэфами
    odds_matches = [m for m in all_h2h if m['h_odd'] and m['d_odd'] and m['a_odd']]
    
    if odds_matches:
        last = odds_matches[-1]
        h, d, a = last['h_odd'], last['d_odd'], last['a_odd']
        
        # Убираем маржу БК
        inv_h, inv_d, inv_a = 1/h, 1/d, 1/a
        total_inv = inv_h + inv_d + inv_a
        
        fair_h = (inv_h / total_inv) * 100
        fair_d = (inv_d / total_inv) * 100
        fair_a = (inv_a / total_inv) * 100
        
        margin = (total_inv - 1) * 100
        
        st.markdown(f"**💰 Честные шансы (последний матч с кэфами):**")
        st.markdown(f"- Маржа БК: **{margin:.1f}%**")
        st.metric("П1 fair", f"{fair_h:.1f}%")
        st.metric("Ничья fair", f"{fair_d:.1f}%")
        st.metric("П2 fair", f"{fair_a:.1f}%")
        
        # Поиск валуя
        st.markdown("**🎯 Валуй-анализ:**")
        st.info(f"Если твоя БК дает на П1 кэф выше **{100/fair_h:.2f}** — это валуй")
        st.info(f"Если твоя БК дает на П2 кэф выше **{100/fair_a:.2f}** — это валуй")
    else:
        st.warning("⚠️ Коэффициентов БК в базе нет")
    
    # Последние 5 матчей каждой команды
    st.markdown("---")
    st.subheader(" Форма команд")
    
    home_form = [m for m in matches if m['home'] == home or m['away'] == home][-5:]
    away_form = [m for m in matches if m['home'] == away or m['away'] == away][-5:]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{home} (последние 5):**")
        for m in home_form:
            if m['home'] == home:
                res = "✅" if m['res'] == 'H' else ("⚪" if m['res'] == 'D' else "❌")
                st.text(f"{res} {m['home']} vs {m['away']}: {m['res']}")
            else:
                res = "✅" if m['res'] == 'A' else ("⚪" if m['res'] == 'D' else "❌")
                st.text(f"{res} {m['home']} vs {m['away']}: {m['res']}")
    
    with col2:
        st.markdown(f"**{away} (последние 5):**")
        for m in away_form:
            if m['home'] == away:
                res = "✅" if m['res'] == 'H' else ("⚪" if m['res'] == 'D' else "❌")
                st.text(f"{res} {m['home']} vs {m['away']}: {m['res']}")
            else:
                res = "✅" if m['res'] == 'A' else ("⚪" if m['res'] == 'D' else "❌")
                st.text(f"{res} {m['home']} vs {m['away']}: {m['res']}")
