import requests
import os
import time

# Все сезоны (от новых к старым)
SEASONS = ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']

# Все лиги football-data.co.uk
LEAGUES = {
    # Англия
    'E0.csv': 'E0',      # Premier League
    'E1.csv': 'E1',      # Championship
    'E2.csv': 'E2',      # League 1
    'E3.csv': 'E3',      # League 2
    'EC.csv': 'EC',      # National
    # Шотландия
    'SC0.csv': 'SC0',    # Premiership
    'SC1.csv': 'SC1',    # Championship
    'SC2.csv': 'SC2',    # League 1
    'SC3.csv': 'SC3',    # League 2
    # Германия
    'D1.csv': 'D1',      # Bundesliga
    'D2.csv': 'D2',      # 2. Bundesliga
    # Италия
    'I1.csv': 'I1',      # Serie A
    'I2.csv': 'I2',      # Serie B
    # Испания
    'SP1.csv': 'SP1',    # La Liga
    'SP2.csv': 'SP2',    # La Liga 2
    # Франция
    'F1.csv': 'F1',      # Ligue 1
    'F2.csv': 'F2',      # Ligue 2
    # Нидерланды
    'N1.csv': 'N1',      # Eredivisie
    # Бельгия
    'B1.csv': 'B1',      # Pro League
    # Португалия
    'P1.csv': 'P1',      # Primeira Liga
    # Турция
    'TU1.csv': 'TU1',    # Super Lig
    # Греция
    'G1.csv': 'G1',      # Super League
    # Россия
    'RUS.csv': 'R1',     # Premier League
    # Польша
    'POL.csv': 'PO1',    # Ekstraklasa
    # Финляндия
    'FIN.csv': 'FIN',    # Veikkausliiga
}

def download_file(url, timeout=30):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"   ❌ {e}")
        return None

def merge_csv(local_file, content):
    """Добавляет новые строки из content в local_file"""
    # Сохраняем во временный файл
    temp = f"temp_{local_file}"
    with open(temp, 'wb') as f:
        f.write(content)
    
    # Считаем строки
    with open(temp, 'r', encoding='utf-8', errors='ignore') as f:
        new_lines = [line.strip() for line in f if line.strip()]
    
    if len(new_lines) <= 1:
        os.remove(temp)
        return 0
    
    # Если файла нет — создаём
    if not os.path.exists(local_file):
        os.rename(temp, local_file)
        return len(new_lines) - 1  # без заголовка
    
    # Читаем существующие
    old_rows = set()
    with open(local_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            old_rows.add(line.strip())
    
    old_count = len(old_rows)
    
    # Добавляем новые
    for line in new_lines:
        old_rows.add(line)
    
    # Записываем
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in old_rows:
            f.write(row + '\n')
    
    os.remove(temp)
    return len(old_rows) - old_count

def main():
    total_added = 0
    total_files = 0
    
    print(f"🔄 Загрузка всех лиг за {len(SEASONS)} сезонов\n")
    
    for local_file, league_code in LEAGUES.items():
        print(f"\n{'='*70}")
        print(f"📁 {local_file} ({league_code})")
        print(f"{'='*70}")
        
        file_added = 0
        
        for season in SEASONS:
            url = f'https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv'
            print(f"  📅 {season}: ", end='', flush=True)
            
            content = download_file(url)
            if content is None:
                print("⚠️ Нет данных")
                continue
            
            added = merge_csv(local_file, content)
            file_added += added
            total_added += added
            
            if added > 0:
                print(f"+{added} строк")
            else:
                print("уже есть")
            
            # Пауза, чтобы не блокировали
            time.sleep(0.3)
        
        if os.path.exists(local_file):
            with open(local_file, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines = sum(1 for _ in f)
            print(f"  ✅ Итого в {local_file}: {total_lines} строк")
            total_files += 1
    
    print(f"\n{'='*70}")
    print(f"✅ ГОТОВО!")
    print(f"   Файлов: {total_files}")
    print(f"   Добавлено строк: {total_added}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
