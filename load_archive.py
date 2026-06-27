import requests
import os

# Архивные URL (примеры для разных сезонов)
ARCHIVE_URLS = {
    '2023_24': [
        'https://www.football-data.co.uk/mmz4281/2324/F1.csv',  # Финляндия
        'https://www.football-data.co.uk/mmz4281/2324/R1.csv',  # Россия
        'https://www.football-data.co.uk/mmz4281/2324/PO1.csv', # Польша
        'https://www.football-data.co.uk/mmz4281/2324/TU1.csv', # Турция
    ],
    '2022_23': [
        'https://www.football-data.co.uk/mmz4281/2223/F1.csv',
        'https://www.football-data.co.uk/mmz4281/2223/R1.csv',
        'https://www.football-data.co.uk/mmz4281/2223/PO1.csv',
        'https://www.football-data.co.uk/mmz4281/2223/TU1.csv',
    ],
    '2021_22': [
        'https://www.football-data.co.uk/mmz4281/2122/F1.csv',
        'https://www.football-data.co.uk/mmz4281/2122/R1.csv',
        'https://www.football-data.co.uk/mmz4281/2122/PO1.csv',
        'https://www.football-data.co.uk/mmz4281/2122/TU1.csv',
    ]
}

def download_and_merge(url, local_file):
    print(f"⬇️  {url}")
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 404:
            print(f"   ⚠️ Не найдено")
            return 0
        r.raise_for_status()
    except Exception as e:
        print(f"   ❌ {e}")
        return 0
    
    temp = f"temp_{local_file}_archive"
    with open(temp, 'wb') as f:
        f.write(r.content)
    
    # Считаем строки
    with open(temp, 'r', encoding='utf-8', errors='ignore') as f:
        rows = sum(1 for _ in f)
    
    if rows <= 1:
        print(f"   ⚠️ Пустой файл")
        os.remove(temp)
        return 0
    
    # Если файла нет — создаём
    if not os.path.exists(local_file):
        os.rename(temp, local_file)
        print(f"   ✅ Создан {local_file}: {rows} строк")
        return rows
    
    # Добавляем к существующему
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
    added = new_count - old_count
    print(f"   ✅ {local_file}: +{added} строк (всего {new_count})")
    return added

def main():
    total = 0
    
    for season, urls in ARCHIVE_URLS.items():
        print(f"\n{'='*70}")
        print(f"📅 Сезон {season}")
        print(f"{'='*70}\n")
        
        for url in urls:
            # Определяем локальное имя
            league_code = url.split('/')[-1]
            local_name = league_code.replace('PO1', 'POL').replace('R1', 'RUS').replace('F1', 'FIN').replace('TU1', 'TU1')
            
            added = download_and_merge(url, local_name)
            total += added
    
    print(f"\n{'='*70}")
    print(f"✅ Добавлено {total} строк из архива")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
