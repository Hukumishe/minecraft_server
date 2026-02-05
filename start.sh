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

# Создаем ops.json, если его нет и указаны переменные окружения
if [ ! -f ops.json ] && [ ! -z "$OPS_UUID" ] && [ ! -z "$OPS_NAME" ]; then
    echo "Создание ops.json для оператора $OPS_NAME..."
    cat > ops.json << EOF
[
  {
    "uuid": "$OPS_UUID",
    "name": "$OPS_NAME",
    "level": 4,
    "bypassesPlayerLimit": false
  }
]
EOF
    echo "ops.json создан!"
fi

# Запускаем сервер
echo "Запуск Minecraft сервера с ${MEMORY} памяти..."
java -Xmx${MEMORY} -Xms${MEMORY} -jar server.jar nogui

