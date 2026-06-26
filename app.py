import streamlit as st
import os

st.set_page_config(page_title="Football Analyzer", layout="centered")
st.title("⚽ Анализ матчей")

@st.cache_data
def load_matches():
    matches = []
    
    # RUS, FIN, POL, CHN — без заголовков
    # Формат: Country,League,Season,Date,Time,Home,Away,FTHG,FTAG,FTR,B365H,B365D,B365A
    for fname, league in [('RUS.csv','RUS'), ('FIN.csv','FIN'), ('POL.csv','POL'), ('CHN.csv','CHN')]:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    p = line.strip().split(',')
                    if len(p) >= 13:
                        try:
                            matches.append({
                                'home': p[5].strip().lower(),
                                'away': p[6].strip().lower(),
                                'res': p[9].strip(),
                                'h_odd': float(p[10]) if p[10] else None,
                                'd_odd': float(p[11]) if p[11] else None,
                                'a_odd': float(p[12]) if p[12] else None,
                                'league': league
                            })
                        except: pass
    
    # P1 — с заголовками
    if os.path.exists('P1.csv'):
        with open('P1.csv', 'r', encoding='utf-8', errors='ignore') as f:
            header = f.readline().strip().split(',')
            idx = {h.strip(): i for i, h in enumerate(header)}
            hi, ai, ri = idx.get('HomeTeam'), idx.get('AwayTeam'), idx.get('FTR')
            bh, bd, ba = idx.get('B365H'), idx.get('B365D'), idx.get('B365A')
            if hi is not None and ai is not None and ri is not None:
                for line in f:
                    p = line.strip().split(',')
                    if len(p) > max(hi, ai, ri):
                        try:
                            matches.append({
                                'home': p[hi].strip().lower(),
                                'away': p[ai].strip().lower(),
                                'res': p[ri].strip(),
                                'h_odd': float(p[bh]) if bh and len(p) > bh and p[bh] else None,
                                'd_odd': float(p[bd]) if bd and len(p) > bd and p[bd] else None,
                                'a_odd': float(p[ba]) if ba and len(p) > ba and p[ba] else None,
                                'league': 'P1'
                            })
                        except: pass
    return matches

matches = load_matches()
st.success(f"✅ Загружено {len(matches)} матчей")

st.markdown("---")
st.subheader("🔍 Поиск матча")

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
        
        st.markdown(f"**📊 Личные встречи ({total}):**")
        c1,c2,c3 = st.columns(3)
        c1.metric("П1", f"{hw/total*100:.1f}%", f"{hw} побед")
        c2.metric("Ничья", f"{dr/total*100:.1f}%", f"{dr}")
        c3.metric("П2", f"{aw/total*100:.1f}%", f"{aw} побед")
    else:
        st.warning("⚠️ Личных встреч нет")
    
    odds = [m for m in h2h if m['h_odd'] and m['d_odd'] and m['a_odd'] and m['h_odd']>1]
    if odds:
        last = odds[-1]
        h,d,a = last['h_odd'], last['d_odd'], last['a_odd']
        inv = 1/h + 1/d + 1/a
        margin = (inv-1)*100
        fh = (1/h/inv)*100
        fd = (1/d/inv)*100
        fa = (1/a/inv)*100
        
        st.markdown(f"**💰 Честные шансы (кэфы {h}/{d}/{a}, маржа {margin:.1f}%):**")
        c1,c2,c3 = st.columns(3)
        c1.metric("П1 fair", f"{fh:.1f}%")
        c2.metric("Ничья fair", f"{fd:.1f}%")
        c3.metric("П2 fair", f"{fa:.1f}%")
        
        st.info(f"🎯 Валуй П1: бери если кэф БК > **{100/fh:.2f}**")
        st.info(f"🎯 Валуй П2: бери если кэф БК > **{100/fa:.2f}**")
    else:
        st.warning("⚠️ Коэффициентов БК в базе нет")
    
    st.markdown("---")
    st.subheader("📈 Форма (последние 5)")
    hf = [m for m in matches if m['home']==home or m['away']==home][-5:]
    af = [m for m in matches if m['home']==away or m['away']==away][-5:]
    
    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f"**{home}:**")
        for m in hf:
            res = "✅" if (m['home']==home and m['res']=='H') or (m['away']==home and m['res']=='A') else ("⚪" if m['res']=='D' else "❌")
            st.text(f"{res} {m['home']} vs {m['away']}")
    with c2:
        st.markdown(f"**{away}:**")
        for m in af:
            res = "✅" if (m['home']==away and m['res']=='H') or (m['away']==away and m['res']=='A') else ("⚪" if m['res']=='D' else "❌")
            st.text(f"{res} {m['home']} vs {m['away']}")
