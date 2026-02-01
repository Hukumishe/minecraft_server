# Используем официальный образ Java для Minecraft сервера
FROM eclipse-temurin:17-jre-alpine

# Устанавливаем необходимые пакеты
RUN apk add --no-cache curl bash jq

# Создаем рабочую директорию
WORKDIR /minecraft

# Переменные окружения для настройки сервера
ENV MEMORY=6G
ENV MINECRAFT_VERSION=latest
ENV CUSTOM_SERVER_URL=
ENV EULA=true

# Копируем скрипты
COPY start.sh /minecraft/start.sh
RUN chmod +x /minecraft/start.sh

# Копируем файлы конфигурации
COPY server.properties /minecraft/server.properties
COPY eula.txt /minecraft/eula.txt

# Открываем порт Minecraft
EXPOSE 25565

# Запускаем скрипт
CMD ["/minecraft/start.sh"]

