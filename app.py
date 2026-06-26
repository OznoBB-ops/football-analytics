import streamlit as st
import os

st.set_page_config(page_title="Football Analyzer", layout="wide")
st.title("⚽ Анализ матчей")

@st.cache_data
def load_all():
    matches = []
    errors = []
    
    # P1.csv — с заголовками
    if os.path.exists('P1.csv'):
        try:
            with open('P1.csv', 'r', encoding='utf-8', errors='ignore') as f:
                header = f.readline().strip().split(',')
                idx = {h.strip(): i for i, h in enumerate(header)}
                hi = idx.get('HomeTeam')
                ai = idx.get('AwayTeam')
                ri = idx.get('FTR')
                b365h = idx.get('B365H')
                b365d = idx.get('B365D')
                b365a = idx.get('B365A')
                
                if hi is not None and ai is not None and ri is not None:
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) > max(hi, ai, ri):
                            try:
                                matches.append({
                                    'home': parts[hi].strip().lower(),
                                    'away': parts[ai].strip().lower(),
                                    'res': parts[ri].strip(),
                                    'h_odd': float(parts[b365h]) if b365h and len(parts) > b365h and parts[b365h] else None,
                                    'd_odd': float(parts[b365d]) if b365d and len(parts) > b365d and parts[b365d] else None,
                                    'a_odd': float(parts[b365a]) if b365a and len(parts) > b365a and parts[b365a] else None,
                                    'league': 'P1'
                                })
                            except:
                                pass
        except Exception as e:
            errors.append(f"P1: {e}")
    
    # FIN, POL, RUS — без заголовков, позиции: 5=Home, 6=Away, 9=FTR, 10=B365H, 11=B365D, 12=B365A
    for fname, league in [('FIN.csv', 'FIN'), ('POL.csv', 'POL'), ('RUS.csv', 'RUS')]:
        if os.path.exists(fname):
            try:
                with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
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
                                    'league': league
                                })
                            except:
                                pass
            except Exception as e:
                errors.append(f"{fname}: {e}")
    
    return matches, errors

matches, errors = load_all()

if errors:
    for e in errors:
        st.warning(f"⚠️ {e}")

st.success(f"✅ Загружено {len(matches)} матчей")

st.markdown("---")
st.subheader("🔍 Поиск матча")

col1, col2 = st.columns(2)
with col1:
    home = st.text_input("🏠 Хозяева", value="porto").lower().strip()
with col2:
    away = st.text_input("🛫 Гости", value="benfica").lower().strip()

if st.button("📊 Рассчитать", use_container_width=True):
    h2h = [m for m in matches if m['home'] == home and m['away'] == away]
    h2h_rev = [m for m in matches if m['home'] == away and m['away'] == home]
    all_h2h = h2h + h2h_rev
    
    st.markdown(f"### {home.upper()} vs {away.upper()}")
    
    if len(all_h2h) >= 1:
        # Считаем победы home команды (в любом порядке)
        h_wins = 0
        for m in all_h2h:
            if m['home'] == home and m['res'] == 'H':
                h_wins += 1
            elif m['away'] == home and m['res'] == 'A':
                h_wins += 1
        
        a_wins = 0
        for m in all_h2h:
            if m['home'] == away and m['res'] == 'H':
                a_wins += 1
            elif m['away'] == away and m['res'] == 'A':
                a_wins += 1
        
        draws = sum(1 for m in all_h2h if m['res'] == 'D')
        total = len(all_h2h)
        
        st.markdown(f"**📊 Личные встречи ({total} матчей):**")
        col1, col2, col3 = st.columns(3)
        col1.metric("П1 (хозяева)", f"{h_wins/total*100:.1f}%", f"{h_wins} побед")
        col2.metric("Ничья", f"{draws/total*100:.1f}%", f"{draws} игр")
        col3.metric("П2 (гости)", f"{a_wins/total*100:.1f}%", f"{a_wins} побед")
    else:
        st.warning("⚠️ Личных встреч не найдено")
    
    # Fair odds
    odds_matches = [m for m in all_h2h if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd'] > 1]
    
    if odds_matches:
        last = odds_matches[-1]
        h, d, a = last['h_odd'], last['d_odd'], last['a_odd']
        
        inv_h, inv_d, inv_a = 1/h, 1/d, 1/a
        total_inv = inv_h + inv_d + inv_a
        margin = (total_inv - 1) * 100
        
        fair_h = (inv_h / total_inv) * 100
        fair_d = (inv_d / total_inv) * 100
        fair_a = (inv_a / total_inv) * 100
        
        st.markdown(f"**💰 Честные шансы (последний матч с кэфами {h}/{d}/{a}):**")
        st.markdown(f"- Маржа БК: **{margin:.1f}%**")
        col1, col2, col3 = st.columns(3)
        col1.metric("П1 fair", f"{fair_h:.1f}%")
        col2.metric("Ничья fair", f"{fair_d:.1f}%")
        col3.metric("П2 fair", f"{fair_a:.1f}%")
        
        st.markdown("**🎯 Порог валуя:**")
        st.info(f"Бери П1, если твоя БК дает кэф выше **{100/fair_h:.2f}**")
        st.info(f"Бери П2, если твоя БК дает кэф выше **{100/fair_a:.2f}**")
    else:
        st.warning("⚠️ Коэффициентов БК в базе нет")
    
    # Форма
    st.markdown("---")
    st.subheader("📈 Форма команд (последние 5)")
    
    home_form = [m for m in matches if m['home'] == home or m['away'] == home][-5:]
    away_form = [m for m in matches if m['home'] == away or m['away'] == away][-5:]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{home}:**")
        for m in home_form:
            if m['home'] == home:
                res = "✅" if m['res'] == 'H' else ("⚪" if m['res'] == 'D' else "❌")
            else:
                res = "✅" if m['res'] == 'A' else ("⚪" if m['res'] == 'D' else "")
            st.text(f"{res} {m['home']} vs {m['away']}: {m['res']}")
    
    with col2:
        st.markdown(f"**{away}:**")
        for m in away_form:
            if m['home'] == away:
                res = "✅" if m['res'] == 'H' else ("⚪" if m['res'] == 'D' else "❌")
            else:
                res = "✅" if m['res'] == 'A' else ("⚪" if m['res'] == 'D' else "❌")
            st.text(f"{res} {m['home']} vs {m['away']}: {m['res']}")
