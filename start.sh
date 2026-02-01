#!/bin/bash

# Скачиваем сервер, если его еще нет
if [ ! -f server.jar ]; then
    # Проверяем, указана ли кастомная сборка
    if [ ! -z "$CUSTOM_SERVER_URL" ]; then
        echo "Скачивание кастомной сборки Minecraft сервера..."
        echo "URL: $CUSTOM_SERVER_URL"
        
        # Скачиваем кастомную сборку
        curl -L -o server.jar "$CUSTOM_SERVER_URL"
        
        if [ ! -f server.jar ]; then
            echo "Ошибка: не удалось скачать кастомную сборку с $CUSTOM_SERVER_URL"
            exit 1
        fi
        
        echo "Кастомная сборка успешно скачана!"
    else
        echo "Скачивание стандартного Minecraft сервера версии ${MINECRAFT_VERSION}..."
        
        # Получаем URL для скачивания сервера
        VERSION_MANIFEST_URL="https://launchermeta.mojang.com/mc/game/version_manifest.json"
        
        if [ "$MINECRAFT_VERSION" = "latest" ]; then
            # Получаем последнюю версию
            VERSION_URL=$(curl -s $VERSION_MANIFEST_URL | jq -r '.latest.release as $latest | .versions[] | select(.id == $latest) | .url')
        else
            # Получаем указанную версию
            VERSION_URL=$(curl -s $VERSION_MANIFEST_URL | jq -r ".versions[] | select(.id == \"$MINECRAFT_VERSION\") | .url")
        fi
        
        if [ -z "$VERSION_URL" ] || [ "$VERSION_URL" = "null" ]; then
            echo "Ошибка: не удалось найти версию $MINECRAFT_VERSION"
            echo "Используем последнюю стабильную версию..."
            VERSION_URL=$(curl -s $VERSION_MANIFEST_URL | jq -r '.latest.release as $latest | .versions[] | select(.id == $latest) | .url')
        fi
        
        # Получаем URL сервера
        SERVER_URL=$(curl -s "$VERSION_URL" | jq -r '.downloads.server.url')
        
        if [ -z "$SERVER_URL" ] || [ "$SERVER_URL" = "null" ]; then
            echo "Ошибка: не удалось получить URL сервера"
            exit 1
        fi
        
        echo "Скачивание с $SERVER_URL"
        curl -L -o server.jar "$SERVER_URL"
        
        if [ ! -f server.jar ]; then
            echo "Ошибка: не удалось скачать server.jar"
            exit 1
        fi
        
        echo "Сервер успешно скачан!"
    fi
fi

# Обновляем порт в server.properties, если Railway предоставил переменную PORT
if [ ! -z "$PORT" ]; then
    echo "Обновление порта сервера на $PORT (из переменной окружения Railway)"
    sed -i "s/server-port=.*/server-port=$PORT/" server.properties
fi

# Функция для обработки сигналов остановки
cleanup() {
    echo ""
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Получен сигнал остановки, сохраняем мир..."
    
    # Создаем бэкап перед остановкой
    if [ -d "/minecraft/world" ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Создание бэкапа перед остановкой..."
        BACKUP_DIR="/minecraft/backups"
        mkdir -p "$BACKUP_DIR"
        backup_name="world_$(date +%Y%m%d_%H%M%S).tar.gz"
        tar -czf "$BACKUP_DIR/$backup_name" -C /minecraft world 2>/dev/null
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Бэкап создан: $backup_name"
    fi
    
    # Останавливаем Java процесс
    kill -TERM $SERVER_PID 2>/dev/null
    wait $SERVER_PID
    exit 0
}

# Устанавливаем обработчик сигналов
trap cleanup SIGTERM SIGINT

# Запускаем автосохранение в фоне (если включено)
if [ "$AUTO_SAVE_ENABLED" = "true" ]; then
    echo "Запуск автосохранения (интервал: ${AUTO_SAVE_INTERVAL} минут)..."
    /minecraft/autosave.sh &
    AUTO_SAVE_PID=$!
fi

# Запускаем сервер
echo "Запуск Minecraft сервера с ${MEMORY} памяти..."
java -Xmx${MEMORY} -Xms${MEMORY} -jar server.jar nogui &
SERVER_PID=$!

# Ждем завершения сервера
wait $SERVER_PID
EXIT_CODE=$?

# Останавливаем автосохранение
if [ ! -z "$AUTO_SAVE_PID" ]; then
    kill $AUTO_SAVE_PID 2>/dev/null
fi

# Финальное сохранение
if [ -d "/minecraft/world" ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Создание финального бэкапа..."
    /minecraft/autosave.sh
fi

exit $EXIT_CODE

