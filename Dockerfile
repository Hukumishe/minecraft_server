# Используем официальный образ Java для Minecraft сервера
# Java 21 требуется для современных версий Minecraft
FROM eclipse-temurin:21-jre-alpine

# Устанавливаем необходимые пакеты
RUN apk add --no-cache curl bash jq python3 py3-pip

# Создаем рабочую директорию
WORKDIR /minecraft

# Переменные окружения для настройки сервера
ENV MEMORY=6G
ENV MINECRAFT_VERSION=latest
ENV CUSTOM_SERVER_URL=
ENV EULA=true
ENV AUTO_SAVE_ENABLED=true
ENV AUTO_SAVE_INTERVAL=15
ENV MAX_BACKUPS=10

# Копируем скрипты
COPY start.sh /minecraft/start.sh
COPY autosave.sh /minecraft/autosave.sh
COPY server_api.py /minecraft/server_api.py
RUN chmod +x /minecraft/start.sh /minecraft/autosave.sh /minecraft/server_api.py

# Копируем файлы конфигурации
COPY server.properties /minecraft/server.properties
COPY eula.txt /minecraft/eula.txt

# Открываем порты
EXPOSE 25565 8080

# Запускаем скрипт
CMD ["/minecraft/start.sh"]

