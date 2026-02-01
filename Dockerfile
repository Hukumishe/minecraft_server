# Используем официальный образ Java для Minecraft сервера
# Java 21 требуется для современных версий Minecraft
FROM eclipse-temurin:21-jre-alpine

# Устанавливаем необходимые пакеты
RUN apk add --no-cache curl bash jq

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
RUN chmod +x /minecraft/start.sh /minecraft/autosave.sh

# Копируем файлы конфигурации
COPY server.properties /minecraft/server.properties
COPY eula.txt /minecraft/eula.txt

# Открываем порт Minecraft
EXPOSE 25565

# Запускаем скрипт
CMD ["/minecraft/start.sh"]

