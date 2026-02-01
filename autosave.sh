#!/bin/bash

# Скрипт для автоматического сохранения мира Minecraft
# Запускается в фоновом режиме и мониторит сервер

WORLD_DIR="/minecraft/world"
BACKUP_DIR="/minecraft/backups"
AUTO_SAVE_ENABLED=${AUTO_SAVE_ENABLED:-"true"}
AUTO_SAVE_INTERVAL=${AUTO_SAVE_INTERVAL:-"15"} # минуты
MAX_BACKUPS=${MAX_BACKUPS:-"10"}

# Создаем директорию для бэкапов, если её нет
mkdir -p "$BACKUP_DIR"

# Функция создания бэкапа
create_backup() {
    local backup_name="world_$(date +%Y%m%d_%H%M%S).tar.gz"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Создание бэкапа: $backup_name"
    
    # Создаем архив мира
    if [ -d "$WORLD_DIR" ]; then
        tar -czf "$backup_path" -C /minecraft world
        
        if [ $? -eq 0 ]; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Бэкап успешно создан: $backup_name"
            
            # Удаляем старые бэкапы, если их больше MAX_BACKUPS
            local backup_count=$(ls -1 "$BACKUP_DIR"/*.tar.gz 2>/dev/null | wc -l)
            if [ $backup_count -gt $MAX_BACKUPS ]; then
                ls -t "$BACKUP_DIR"/*.tar.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
                echo "[$(date +'%Y-%m-%d %H:%M:%S')] Удалены старые бэкапы"
            fi
        else
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Ошибка при создании бэкапа"
        fi
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Директория мира не найдена: $WORLD_DIR"
    fi
}

# Функция проверки количества игроков через логи
check_players() {
    # Проверяем последние логи на наличие информации об игроках
    # Это упрощенная версия - в реальности нужно парсить логи более точно
    local log_file="/minecraft/logs/latest.log"
    
    if [ -f "$log_file" ]; then
        # Ищем последнее упоминание о количестве игроков
        local players_online=$(tail -n 100 "$log_file" | grep -oP "There are \K\d+" | tail -n 1)
        
        if [ ! -z "$players_online" ] && [ "$players_online" = "0" ]; then
            return 0 # Нет игроков
        fi
    fi
    
    return 1 # Есть игроки или не удалось определить
}

# Основной цикл мониторинга
if [ "$AUTO_SAVE_ENABLED" = "true" ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Автосохранение включено (интервал: ${AUTO_SAVE_INTERVAL} минут)"
    
    while true; do
        sleep $((AUTO_SAVE_INTERVAL * 60))
        
        # Проверяем, есть ли игроки
        if check_players; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Нет игроков онлайн, создаем бэкап..."
            create_backup
        else
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Игроки онлайн, пропускаем автосохранение"
        fi
    done
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Автосохранение отключено"
fi

