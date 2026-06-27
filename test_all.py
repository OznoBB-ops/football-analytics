#!/usr/bin/env python3
"""
Комплексное тестирование системы Football Analytics
"""
import os
import sys
import time
from datetime import datetime

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def test_files_exist():
    """Тест 1: Проверка наличия всех файлов"""
    print_header("ТЕСТ 1: Проверка файлов")
    
    required_files = [
        'app.py',
        'bot.py',
        'bookmaker_parser.py',
        'predictor.py',
        'recommendations.py',
        'teams_ru.py',
        'requirements.txt',
        'daily_values.py',
        'backtest.py',
        'backtest_by_league.py',
        'load_all.py'
    ]
    
    csv_files = ['FIN.csv', 'POL.csv', 'TU1.csv', 'SC1.csv', 'B1.csv', 'G1.csv', 'P1.csv']
    
    all_ok = True
    
    for file in required_files:
        if os.path.exists(file):
            print_success(f"{file} существует")
        else:
            print_error(f"{file} отсутствует")
            all_ok = False
    
    for file in csv_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print_success(f"{file} существует ({size:,} байт)")
        else:
            print_error(f"{file} отсутствует")
            all_ok = False
    
    return all_ok

def test_imports():
    """Тест 2: Проверка импортов"""
    print_header("ТЕСТ 2: Проверка импортов")
    
    modules = [
        ('streamlit', 'Streamlit'),
        ('pandas', 'Pandas'),
        ('matplotlib', 'Matplotlib'),
        ('requests', 'Requests'),
        ('telebot', 'PyTelegramBotAPI'),
        ('dotenv', 'python-dotenv')
    ]
    
    all_ok = True
    
    for module, name in modules:
        try:
            __import__(module)
            print_success(f"{name} импортирован")
        except ImportError as e:
            print_error(f"{name} не импортирован: {e}")
            all_ok = False
    
    return all_ok

def test_local_modules():
    """Тест 3: Проверка локальных модулей"""
    print_header("ТЕСТ 3: Проверка локальных модулей")
    
    all_ok = True
    
    # teams_ru
    try:
        from teams_ru import translate_team, TEAMS_RU
        test_teams = ['zenit', 'barcelona', 'bayern']
        for team in test_teams:
            translated = translate_team(team)
            if translated != team:
                print_success(f"Перевод {team} → {translated}")
            else:
                print_warning(f"Перевод {team} не найден (используется оригинал)")
        print_success(f"teams_ru работает ({len(TEAMS_RU)} команд в словаре)")
    except Exception as e:
        print_error(f"teams_ru ошибка: {e}")
        all_ok = False
    
    # predictor
    try:
        from predictor import calculate_expected_goals, predict_exact_scores, predict_outcomes
        home_form = {'avg_gf': 1.8, 'avg_ga': 1.2}
        away_form = {'avg_gf': 1.3, 'avg_ga': 1.6}
        xg = calculate_expected_goals(home_form, away_form)
        print_success(f"xG рассчитан: {xg['home_xg']} - {xg['away_xg']}")
        
        scores = predict_exact_scores(xg['home_xg'], xg['away_xg'])
        print_success(f"Точные счёта предсказаны: {len(scores)} вариантов")
        
        outcomes = predict_outcomes(xg['home_xg'], xg['away_xg'])
        print_success(f"Исходы предсказаны: П1 {outcomes['П1']:.1f}% | Х {outcomes['Х']:.1f}% | П2 {outcomes['П2']:.1f}%")
    except Exception as e:
        print_error(f"predictor ошибка: {e}")
        all_ok = False
    
    # recommendations
    try:
        from recommendations import load_matches, find_patterns
        matches = load_matches()
        print_success(f"Загружено {len(matches)} матчей")
        
        patterns = find_patterns(matches, min_sample=30, min_edge=10)
        total_patterns = len(patterns['1X2']) + len(patterns['totals']) + len(patterns['btts'])
        print_success(f"Найдено {total_patterns} паттернов (1X2: {len(patterns['1X2'])}, Тоталы: {len(patterns['totals'])}, ОЗ: {len(patterns['btts'])})")
    except Exception as e:
        print_error(f"recommendations ошибка: {e}")
        all_ok = False
    
    # bookmaker_parser
    try:
        from bookmaker_parser import parse_bookmaker_text
        test_text = """Нортерн Тайгерс
Далвич Хилл
10
10
1.48
М3.5Б
2.39
1Т 33'
+69"""
        matches = parse_bookmaker_text(test_text)
        if len(matches) > 0:
            print_success(f"Парсер БК работает (найдено {len(matches)} матчей)")
        else:
            print_warning("Парсер БК не нашёл матчей в тестовом тексте")
    except Exception as e:
        print_error(f"bookmaker_parser ошибка: {e}")
        all_ok = False
    
    return all_ok

def test_csv_data():
    """Тест 4: Проверка CSV данных"""
    print_header("ТЕСТ 4: Проверка CSV данных")
    
    csv_files = ['FIN.csv', 'POL.csv', 'TU1.csv', 'SC1.csv', 'B1.csv', 'G1.csv', 'P1.csv']
    
    all_ok = True
    total_matches = 0
    
    for file in csv_files:
        if not os.path.exists(file):
            print_error(f"{file} отсутствует")
            all_ok = False
            continue
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                count = len(lines) - 1  # минус заголовок
                total_matches += count
                print_success(f"{file}: {count} матчей")
        except Exception as e:
            print_error(f"{file} ошибка чтения: {e}")
            all_ok = False
    
    print(f"\n{BLUE}Всего матчей в базе: {total_matches:,}{RESET}")
    
    return all_ok

def test_backtest():
    """Тест 5: Проверка бэктеста"""
    print_header("ТЕСТ 5: Проверка бэктеста")
    
    try:
        from recommendations import load_matches, find_patterns
        from itertools import combinations
        
        matches = load_matches()
        patterns = find_patterns(matches, min_sample=30, min_edge=10)
        
        # Простой бэктест на последних 100 матчах
        played = [m for m in matches if m['res'] and m['h_odd']][-100:]
        
        value_wins = 0
        value_total = 0
        
        for m in played:
            from recommendations import check_patterns
            found = check_patterns(m, patterns)
            for p in found:
                if p['type'] == '1X2':
                    value_total += 1
                    bet_res = {'П1': 'H', 'Ничья': 'D', 'П2': 'A'}[p['bet']]
                    if m['res'] == bet_res:
                        value_wins += 1
        
        if value_total > 0:
            winrate = value_wins / value_total * 100
            print_success(f"Бэктест: {value_wins}/{value_total} ({winrate:.1f}%)")
            if winrate > 50:
                print_success("Стратегия прибыльная!")
            else:
                print_warning("Стратегия убыточная")
        else:
            print_warning("Нет валуйных ставок для проверки")
        
        return True
    except Exception as e:
        print_error(f"Бэктест ошибка: {e}")
        return False

def test_env():
    """Тест 6: Проверка .env"""
    print_header("ТЕСТ 6: Проверка .env")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
        
        all_ok = True
        for var in required_vars:
            value = os.getenv(var)
            if value:
                masked = value[:10] + '...' + value[-5:] if len(value) > 15 else '***'
                print_success(f"{var} установлен ({masked})")
            else:
                print_error(f"{var} не установлен")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print_error(f".env ошибка: {e}")
        return False

def test_performance():
    """Тест 7: Проверка производительности"""
    print_header("ТЕСТ 7: Проверка производительности")
    
    try:
        from recommendations import load_matches, find_patterns
        
        start = time.time()
        matches = load_matches()
        load_time = time.time() - start
        print_success(f"Загрузка базы: {load_time:.2f}с ({len(matches)} матчей)")
        
        start = time.time()
        patterns = find_patterns(matches, min_sample=30, min_edge=10)
        find_time = time.time() - start
        print_success(f"Поиск паттернов: {find_time:.2f}с")
        
        total_time = load_time + find_time
        if total_time < 5:
            print_success(f"Производительность отличная ({total_time:.2f}с)")
        elif total_time < 10:
            print_warning(f"Производительность средняя ({total_time:.2f}с)")
        else:
            print_error(f"Производительность низкая ({total_time:.2f}с)")
        
        return total_time < 10
    except Exception as e:
        print_error(f"Производительность ошибка: {e}")
        return False

def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ FOOTBALL ANALYTICS{RESET}")
    print(f"{BLUE}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = []
    
    results.append(("Файлы", test_files_exist()))
    results.append(("Импорты", test_imports()))
    results.append(("Локальные модули", test_local_modules()))
    results.append(("CSV данные", test_csv_data()))
    results.append(("Бэктест", test_backtest()))
    results.append((".env", test_env()))
    results.append(("Производительность", test_performance()))
    
    print_header("ИТОГИ ТЕСТИРОВАНИЯ")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        if result:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: FAIL")
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Пройдено тестов: {passed}/{total}{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!{RESET}")
    elif passed >= total * 0.8:
        print(f"{YELLOW}⚠ Большинство тестов пройдено{RESET}")
    else:
        print(f"{RED}✗ Есть критические ошибки{RESET}")
    
    print(f"{BLUE}{'='*70}{RESET}\n")

if __name__ == "__main__":
    main()
