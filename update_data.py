import csv
import requests
import os
from datetime import datetime

# Коды лиг на football-data.co.uk
SEASON = '2526'

SOURCES = {
    'RUS.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/R1.csv',
    'P1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/P1.csv',
    'POL.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/PO1.csv',
    'FIN.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/F1.csv',
}

def count_rows(filename):
    if not os.path.exists(filename):
        return 0
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        return sum(1 for _ in f)

def update_file(local_file, url):
    print(f"⬇️  {url}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"   ❌ Ошибка сети: {e}")
        return
    
    temp = f"temp_{local_file}"
    with open(temp, 'wb') as f:
        f.write(r.content)
    
    new_rows = count_rows(temp)
    print(f"   📥 Получено строк: {new_rows}")
    
    if not os.path.exists(local_file):
        os.rename(temp, local_file)
        print(f"   ✅ Создан {local_file}")
        return
    
    # Читаем существующие строки в множество
    old_rows = set()
    with open(local_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            old_rows.add(line.strip())
    
    old_count = len(old_rows)
    
    # Добавляем новые уникальные строки
    with open(temp, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            old_rows.add(line.strip())
    
    # Записываем обратно
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in old_rows:
            f.write(row + '\n')
    
    os.remove(temp)
    new_count = len(old_rows)
    print(f"   ✅ {local_file}: {old_count} → {new_count} строк (+{new_count - old_count})")

def main():
    print(f"🔄 Обновление: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    for filename, url in SOURCES.items():
        update_file(filename, url)
    print("\n✅ Готово!")

if __name__ == "__main__":
    main()
