import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import json

# Импорты на верхнем уровне
from recommendations import load_matches, find_patterns, analyze_team_form
from pnl_tracker import load_pnl as load_pnl_data, get_stats
from teams_ru import translate_team

# Пароль для защиты
PASSWORD = "football2024"

# Проверка авторизации
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Football Analytics")
    password = st.text_input("Введите пароль:", type="password")
    if st.button("Войти"):
        if password == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный пароль")
    st.stop()

# Заголовок
st.title("⚽ Football Analytics")
st.markdown("---")

# Боковое меню
st.sidebar.title("📊 Навигация")
page = st.sidebar.radio("Выберите раздел:", [
    "🏠 Главная",
    "🔍 Поиск матча",
    "💰 Валуйные ставки",
    "💵 Мои ставки (P&L)",
    "📈 Статистика",
    "📋 Команды"
])

# Загрузка данных с кешированием
@st.cache_data
def get_matches():
    return load_matches()

@st.cache_data
def get_patterns():
    matches = get_matches()
    return find_patterns(matches, min_sample=30, min_edge=10)

@st.cache_data
def get_pnl():
    return load_pnl_data()

# Главная страница
if page == "🏠 Главная":
    st.header("🏠 Главная")
    
    matches = get_matches()
    patterns = get_patterns()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего матчей", f"{len(matches):,}")
    with col2:
        st.metric("Паттернов", f"{len(patterns['1X2']) + len(patterns['totals']) + len(patterns['btts'])}")
    with col3:
        st.metric("Лиг", "14")
    
    st.markdown("---")
    st.subheader("📈 Матчей по лигам")
    
    leagues = {}
    for m in matches:
        if m['league'] not in leagues:
            leagues[m['league']] = 0
        leagues[m['league']] += 1
    
    df_leagues = pd.DataFrame([
        {'Лига': k, 'Матчей': v} for k, v in sorted(leagues.items(), key=lambda x: x[1], reverse=True)
    ])
    
    fig = px.bar(df_leagues, x='Лига', y='Матчей', title='Количество матчей по лигам')
    st.plotly_chart(fig, use_container_width=True)

# Поиск матча
elif page == "🔍 Поиск матча":
    st.header("🔍 Поиск матча")
    
    matches = get_matches()
    
    col1, col2 = st.columns(2)
    with col1:
        home = st.text_input("Команда 1", placeholder="Зенит")
    with col2:
        away = st.text_input("Команда 2", placeholder="Спартак")
    
    if home and away:
        h2h = []
        for m in matches:
            home_in = home.lower() in m['home_lower'] or home.lower() in m['away_lower']
            away_in = away.lower() in m['home_lower'] or away.lower() in m['away_lower']
            if home_in and away_in:
                h2h.append(m)
        
        if h2h:
            total = len(h2h)
            hw = sum(1 for m in h2h if (m['home']==h2h[0]['home'] and m['res']=='H') or (m['away']==h2h[0]['home'] and m['res']=='A'))
            aw = sum(1 for m in h2h if (m['home']==h2h[0]['away'] and m['res']=='H') or (m['away']==h2h[0]['away'] and m['res']=='A'))
            dr = sum(1 for m in h2h if m['res']=='D')
            
            st.subheader(f"📊 {translate_team(h2h[0]['home'])} vs {translate_team(h2h[0]['away'])}")
            st.write(f"Личных встреч: **{total}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("П1", f"{hw/total*100:.0f}%", f"{hw} побед")
            with col2:
                st.metric("Ничья", f"{dr/total*100:.0f}%", f"{dr} матчей")
            with col3:
                st.metric("П2", f"{aw/total*100:.0f}%", f"{aw} побед")
            
            totals = [m['total'] for m in h2h]
            over25 = sum(1 for t in totals if t > 2.5) / total * 100
            btts = sum(1 for m in h2h if m['hg']>0 and m['ag']>0) / total * 100
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("ТБ 2.5", f"{over25:.0f}%")
            with col2:
                st.metric("ОЗ Да", f"{btts:.0f}%")
            with col3:
                st.metric("Средний тотал", f"{sum(totals)/total:.1f}")
        else:
            st.warning("Матчи не найдены")

# Валуйные ставки
elif page == "💰 Валуйные ставки":
    st.header("💰 Валуйные ставки")
    
    patterns = get_patterns()
    
    st.subheader("🎯 1X2 (П1/Ничья/П2)")
    df_1x2 = pd.DataFrame([
        {
            'Ставка': p['bet'],
            'Кэф': f"{p['odds']:.2f}",
            'Fair %': f"{p['fair']:.0f}%",
            'Real %': f"{p['real']:.0f}%",
            'Edge': f"{p['edge']:+.0f}%",
            'ROI': f"{p['roi']:+.0f}%",
            'N': p['n']
        }
        for p in patterns['1X2'][:20]
    ])
    st.dataframe(df_1x2, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📊 Тоталы")
    df_totals = pd.DataFrame([
        {
            'Ставка': p['bet'],
            'Real %': f"{p['real']:.0f}%",
            'ROI': f"{p['roi']:+.0f}%",
            'N': p['n']
        }
        for p in patterns['totals'][:10]
    ])
    st.dataframe(df_totals, use_container_width=True)
    
    st.markdown("---")
    st.subheader("⚽ Обе забьют")
    df_btts = pd.DataFrame([
        {
            'Ставка': p['bet'],
            'Real %': f"{p['real']:.0f}%",
            'ROI': f"{p['roi']:+.0f}%",
            'N': p['n']
        }
        for p in patterns['btts'][:10]
    ])
    st.dataframe(df_btts, use_container_width=True)

# Мои ставки (P&L)
elif page == "💵 Мои ставки (P&L)":
    st.header("💵 Мои ставки (P&L)")
    
    pnl_data = get_pnl()
    bets = pnl_data['bets']
    
    if not bets:
        st.info("Нет ставок. Используйте Telegram-бот для добавления ставок.")
    else:
        stats = get_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего ставок", stats['total_bets'])
        with col2:
            st.metric("Winrate", f"{stats['winrate']:.1f}%")
        with col3:
            st.metric("ROI", f"{stats['roi']:+.1f}%")
        with col4:
            st.metric("Прибыль", f"{stats['total_profit']:+.0f}₽")
        
        st.markdown("---")
        
        # График роста банка
        st.subheader("📈 Рост банка")
        
        df_bets = pd.DataFrame(bets)
        df_bets['date'] = pd.to_datetime(df_bets['date'])
        df_bets = df_bets[df_bets['status'] != 'pending'].sort_values('date')
        
        if not df_bets.empty:
            df_bets['cumulative_profit'] = df_bets['profit'].cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_bets['date'],
                y=df_bets['cumulative_profit'],
                mode='lines+markers',
                name='Прибыль',
                line=dict(color='green', width=3)
            ))
            fig.update_layout(
                xaxis_title='Дата',
                yaxis_title='Прибыль (₽)',
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Таблица ставок
        st.subheader("📋 История ставок")
        
        df_display = pd.DataFrame([
            {
                'ID': b['id'],
                'Дата': b['date'],
                'Матч': b['match'],
                'Тип': b['bet_type'],
                'Кэф': f"{b['odds']:.2f}",
                'Сумма': f"{b['stake']:.0f}₽",
                'Статус': '✓' if b['status'] == 'won' else '✗' if b['status'] == 'lost' else '⏳',
                'Прибыль': f"{b['profit']:+.0f}₽" if b['status'] != 'pending' else '—'
            }
            for b in reversed(bets)
        ])
        
        st.dataframe(df_display, use_container_width=True, height=400)

# Статистика
elif page == "📈 Статистика":
    st.header("📈 Статистика")
    
    matches = get_matches()
    
    st.subheader("📊 Распределение тоталов")
    
    totals = [m['total'] for m in matches if m['res']]
    
    fig = px.histogram(
        x=totals,
        nbins=10,
        title='Распределение тоталов матчей',
        labels={'x': 'Тотал голов', 'y': 'Количество матчей'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📈 Результаты матчей")
    
    results = [m['res'] for m in matches if m['res']]
    h_count = results.count('H')
    d_count = results.count('D')
    a_count = results.count('A')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("П1", f"{h_count/len(results)*100:.1f}%", f"{h_count} матчей")
    with col2:
        st.metric("Ничья", f"{d_count/len(results)*100:.1f}%", f"{d_count} матчей")
    with col3:
        st.metric("П2", f"{a_count/len(results)*100:.1f}%", f"{a_count} матчей")

# Команды
elif page == "📋 Команды":
    st.header("📋 Команды")
    
    matches = get_matches()
    
    team = st.text_input("Введите название команды", placeholder="Зенит")
    
    if team:
        form = analyze_team_form(matches, team, last_n=10)
        
        if form:
            st.subheader(f"📊 {translate_team(team)}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Матчей", form['matches'])
            with col2:
                st.metric("Winrate", f"{form['winrate']:.1f}%")
            with col3:
                st.metric("xG за", f"{form['avg_gf']:.2f}")
            with col4:
                st.metric("xG против", f"{form['avg_ga']:.2f}")
            
            st.write(f"Побед: {form['wins']} | Ничьих: {form['draws']} | Поражений: {form['losses']}")
        else:
            st.warning("Команда не найдена")

# Футер
st.markdown("---")
st.markdown("🤖 Telegram-бот | 📧 oznobb@yandex.ru")
