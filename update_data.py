import requests
import os
from datetime import datetime

SEASON = '2526'

SOURCES = {
    'RUS.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/R1.csv',
    'P1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/P1.csv',
    'POL.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/PO1.csv',
    'FIN.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/F1.csv',
    'E0.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/E0.csv',
    'E1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/E1.csv',
    'D1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/D1.csv',
    'SP1.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/SP1.csv',
    'I1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/I1.csv',
    'N1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/N1.csv',
    'B1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/B1.csv',
    'TU1.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/TU1.csv',
    'SC1.csv': f'https://www.football-data.co.uk/mmz4281/{SEASON}/SC1.csv',
    'G1.csv':  f'https://www.football-data.co.uk/mmz4281/{SEASON}/G1.csv',
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
        print(f"   ❌ {e}")
        return
    
    temp = f"temp_{local_file}"
    with open(temp, 'wb') as f:
        f.write(r.content)
    
    new_rows = count_rows(temp)
    
    if new_rows <= 1:
        print(f"   ⚠️ Пустой файл (сезон ещё не начался?)")
        os.remove(temp)
        return
    
    print(f"   📥 Получено строк: {new_rows}")
    
    if not os.path.exists(local_file):
        os.rename(temp, local_file)
        print(f"   ✅ Создан {local_file}")
        return
    
    old_rows = set()
    with open(local_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            old_rows.add(line.strip())
    
    old_count = len(old_rows)
    
    with open(temp, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            old_rows.add(line.strip())
    
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in old_rows:
            f.write(row + '\n')
    
    os.remove(temp)
    new_count = len(old_rows)
    print(f"   ✅ {local_file}: {old_count} → {new_count} (+{new_count - old_count})")

def main():
    print(f"🔄 Обновление: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    for filename, url in SOURCES.items():
        update_file(filename, url)
    print("\n✅ Готово!")

if __name__ == "__main__":
    main()
