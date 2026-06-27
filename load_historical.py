import requests
import os

# Сезоны для загрузки
SEASONS = ['2324', '2425', '2526']

# Лиги
LEAGUES = {
    'RUS': 'R1', 'FIN': 'F1', 'POL': 'PO1', 'P1': 'P1',
    'E0': 'E0', 'E1': 'E1', 'D1': 'D1', 'SP1': 'SP1',
    'I1': 'I1', 'N1': 'N1', 'B1': 'B1', 'TU1': 'TU1',
    'SC1': 'SC1', 'G1': 'G1'
}

def download_season(season, league_code, local_name):
    url = f'https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv'
    print(f"⬇️  {url}")
    
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 404:
            print(f"   ⚠️ Не найдено (404)")
            return 0
        r.raise_for_status()
    except Exception as e:
        print(f"   ❌ {e}")
        return 0
    
    temp = f"temp_{local_name}_{season}"
    with open(temp, 'wb') as f:
        f.write(r.content)
    
    # Считаем строки
    with open(temp, 'r', encoding='utf-8', errors='ignore') as f:
        rows = sum(1 for _ in f)
    
    if rows <= 1:
        print(f"   ⚠️ Пустой файл")
        os.remove(temp)
        return 0
    
    # Добавляем в основной файл
    if not os.path.exists(local_name):
        os.rename(temp, local_name)
        print(f"   ✅ Создан {local_name}: {rows} строк")
        return rows
    
    # Читаем существующие
    old_rows = set()
    with open(local_name, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            old_rows.add(line.strip())
    
    old_count = len(old_rows)
    
    # Добавляем новые
    with open(temp, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            old_rows.add(line.strip())
    
    # Записываем
    with open(local_name, 'w', encoding='utf-8') as f:
        for row in old_rows:
            f.write(row + '\n')
    
    os.remove(temp)
    new_count = len(old_rows)
    print(f"   ✅ {local_name}: {old_count} → {new_count} (+{new_count - old_count})")
    return new_count - old_count

def main():
    total_added = 0
    
    for season in SEASONS:
        print(f"\n{'='*70}")
        print(f"📅 Сезон {season}")
        print(f"{'='*70}\n")
        
        for local_name, league_code in LEAGUES.items():
            added = download_season(season, league_code, local_name)
            total_added += added
    
    print(f"\n{'='*70}")
    print(f"✅ Готово! Добавлено {total_added} новых строк")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
