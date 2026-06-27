import re
import json

def parse_fonbet_html(html_content):
    """Парсит HTML страницу Fonbet"""
    
    # Ищем JSON с данными в скриптах
    json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
    match = re.search(json_pattern, html_content, re.DOTALL)
    
    if not match:
        # Пробуем другой паттерн
        json_pattern = r'"events":\s*(\[.*?\])'
        match = re.search(json_pattern, html_content, re.DOTALL)
    
    if not match:
        return None
    
    try:
        data = json.loads(match.group(1))
        
        # Извлекаем команды и кэфы
        # Структура зависит от версии сайта
        result = {
            'home': '',
            'away': '',
            'h_odd': None,
            'd_odd': None,
            'a_odd': None,
            'totals': {},
            'foras': {}
        }
        
        # Нужно адаптировать под реальную структуру данных
        # Это заглушка - нужно проверить реальный HTML
        
        return result
    except Exception as e:
        print(f"Ошибка парсинга JSON: {e}")
        return None

def parse_fonbet_text(text):
    """Парсит текст, скопированный с Fonbet (если возможно)"""
    # Fonbet может давать копировать в некоторых местах
    # Используем тот же парсер что и для Winline/GGTBET
    from bookmaker_parser import parse_bookmaker_text
    return parse_bookmaker_text(text)

if __name__ == "__main__":
    print("Fonbet парсер")
    print("Варианты использования:")
    print("1. Сохранить страницу как HTML и загрузить файл")
    print("2. Использовать /analyze с текстом (если Fonbet даёт копировать)")
    print("3. Отправить URL для парсинга через API")
