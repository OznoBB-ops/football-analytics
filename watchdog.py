#!/usr/bin/env python3
"""
Watchdog для автоперезапуска бота при падении
"""
import subprocess
import time
import os
from datetime import datetime

LOG_FILE = 'watchdog.log'
CHECK_INTERVAL = 60  # Проверка каждые 60 секунд

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def is_bot_running():
    """Проверяет, запущен ли бот"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'python bot.py'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def start_bot():
    """Запускает бота"""
    try:
        subprocess.Popen(
            ['python', 'bot.py'],
            stdout=open('bot.log', 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        return True
    except Exception as e:
        log(f"❌ Ошибка запуска: {e}")
        return False

def main():
    log("🔍 Watchdog запущен")
    log(f"⏱ Интервал проверки: {CHECK_INTERVAL}с")
    
    consecutive_failures = 0
    
    while True:
        try:
            if is_bot_running():
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                log(f"⚠️ Бот не запущен (попытка {consecutive_failures})")
                
                if consecutive_failures >= 3:
                    log("❌ Слишком много падений. Останавливаю watchdog.")
                    break
                
                log("🔄 Перезапускаю бота...")
                if start_bot():
                    log("✅ Бот перезапущен")
                    time.sleep(10)  # Даём время на старт
                else:
                    log("❌ Не удалось запустить бота")
            
            time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            log("🛑 Watchdog остановлен пользователем")
            break
        except Exception as e:
            log(f"❌ Ошибка watchdog: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
