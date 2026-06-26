#!/bin/bash
echo "🛑 Останавливаю старые процессы..."
pkill -f bot.py
sleep 2
echo "🚀 Запускаю бота..."
nohup python bot.py > bot.log 2>&1 &
echo "✅ Бот запущен в фоне (PID: $!)"
echo "📋 Логи: tail -f bot.log"
