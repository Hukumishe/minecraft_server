# Интеграция веб-интерфейса с Minecraft сервером

## Переменные окружения Railway для управления

Веб-интерфейс должен управлять следующими переменными окружения на Railway:

### Загрузка сборки
- `CUSTOM_SERVER_URL` - URL кастомной сборки .jar файла

### Настройки мира
- `WORLD_SEED` - seed для генерации мира (опционально)
- `GAMEMODE` - режим игры: `survival`, `creative`, `adventure`, `spectator`
- `DIFFICULTY` - сложность: `peaceful`, `easy`, `normal`, `hard`
- `PVP_ENABLED` - включить PvP: `true` или `false`
- `GENERATE_STRUCTURES` - генерировать структуры: `true` или `false`
- `ALLOW_NETHER` - разрешить Nether: `true` или `false`
- `ALLOW_END` - разрешить End: `true` или `false`
- `MAX_PLAYERS` - максимальное количество игроков (по умолчанию 5)
- `VIEW_DISTANCE` - расстояние прорисовки (4-32)
- `SIMULATION_DISTANCE` - расстояние симуляции (4-32)

### Сохранение мира
- `AUTO_SAVE_ENABLED` - включить автосохранение: `true` или `false`
- `AUTO_SAVE_INTERVAL` - интервал автосохранения в минутах (5, 10, 15, 30)
- `MAX_BACKUPS` - максимальное количество сохранений (по умолчанию 10)

## API Endpoints для веб-интерфейса

### Railway API

**Базовый URL:** `https://api.railway.app/v1`

**Аутентификация:** Bearer token (Railway API Key)

#### 1. Получение информации о сервисе
```
GET /services/{serviceId}
```

#### 2. Получение переменных окружения
```
GET /services/{serviceId}/variables
```

#### 3. Обновление переменной окружения
```
PATCH /variables/{variableId}
Body: {
  "value": "новое значение"
}
```

#### 4. Получение деплоев
```
GET /services/{serviceId}/deployments
```

#### 5. Получение логов деплоя
```
GET /deployments/{deploymentId}/logs
```

#### 6. Перезапуск деплоя
```
POST /deployments/{deploymentId}/restart
```

#### 7. Получение доменов (TCP Proxy)
```
GET /services/{serviceId}/domains
```

## Логика работы с настройками мира

При изменении настроек мира через веб-интерфейс:

1. Сохранить все настройки в переменные окружения Railway
2. Обновить файл `server.properties` на сервере (требует перезапуска)
3. Перезапустить сервер для применения изменений

**Важно:** Изменение настроек мира требует перезапуска сервера и может привести к потере несохраненных данных, если мир уже создан.

## Логика автосохранения

### Реализация на сервере

Сервер уже настроен для автосохранения через скрипт `autosave.sh`:

1. **Автосохранение по расписанию:**
   - Скрипт запускается в фоне
   - Каждые N минут (задается через `AUTO_SAVE_INTERVAL`) проверяет количество игроков
   - Если игроков нет (0), создает бэкап

2. **Автосохранение при остановке:**
   - Обработчик сигналов в `start.sh` перехватывает SIGTERM/SIGINT
   - Перед остановкой создает финальный бэкап

3. **Хранение бэкапов:**
   - Бэкапы сохраняются в `/minecraft/backups/`
   - Формат имени: `world_YYYYMMDD_HHMMSS.tar.gz`
   - Автоматическое удаление старых бэкапов (больше `MAX_BACKUPS`)

### Интеграция с веб-интерфейсом

Веб-интерфейс должен:

1. **Отображать список бэкапов:**
   - Получать список файлов из Railway Volume (через API или напрямую)
   - Показывать дату, время, размер каждого бэкапа

2. **Скачивание бэкапов:**
   - Предоставить прямую ссылку для скачивания
   - Или использовать Railway API для получения файла

3. **Восстановление бэкапа:**
   - Загрузить выбранный бэкап
   - Распаковать в директорию `/minecraft/world`
   - Перезапустить сервер

4. **Ручное сохранение:**
   - Отправить команду на сервер (через RCON или API)
   - Или напрямую вызвать скрипт создания бэкапа

## Использование облачного хранилища Lovable

**ВАЖНО:** Все файлы (модпаки, бэкапы мира) хранятся в облачном хранилище Lovable, а не на Railway Volume.

### Преимущества:
- Централизованное хранение данных
- Легкий доступ через веб-интерфейс
- Независимость от Railway инфраструктуры
- Возможность синхронизации между серверами

### Процесс работы:

1. **Загрузка модпака:**
   - Пользователь загружает файл через веб-интерфейс
   - Файл сохраняется в Lovable Storage
   - Получается публичный URL
   - URL сохраняется в Railway переменную `CUSTOM_SERVER_URL`

2. **Создание бэкапа:**
   - Сервер создает архив мира локально
   - Архив загружается в Lovable Storage через веб-интерфейс
   - Метаданные сохраняются в базу данных Lovable
   - Локальный файл удаляется

3. **Восстановление бэкапа:**
   - Пользователь выбирает бэкап из списка
   - Файл скачивается из Lovable Storage
   - Загружается на сервер
   - Сервер распаковывает и перезапускается

Подробности в файле `LOVABLE_STORAGE_INTEGRATION.md`

## Примеры кода для веб-интерфейса

### Обновление переменной окружения

```typescript
async function updateRailwayVariable(
  variableId: string,
  value: string,
  apiKey: string
) {
  const response = await fetch(
    `https://api.railway.app/v1/variables/${variableId}`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ value }),
    }
  );
  
  return response.json();
}
```

### Получение логов сервера

```typescript
async function getServerLogs(
  deploymentId: string,
  apiKey: string
) {
  const response = await fetch(
    `https://api.railway.app/v1/deployments/${deploymentId}/logs`,
    {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    }
  );
  
  return response.text();
}
```

### Перезапуск сервера

```typescript
async function restartServer(
  deploymentId: string,
  apiKey: string
) {
  const response = await fetch(
    `https://api.railway.app/v1/deployments/${deploymentId}/restart`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    }
  );
  
  return response.json();
}
```

## Безопасность

- Хранить Railway API Key в переменных окружения (не в коде)
- Использовать HTTPS для всех запросов
- Валидировать все пользовательские вводы
- Ограничить доступ к API ключам только авторизованным пользователям

## Дополнительные возможности

1. **RCON для управления сервером:**
   - Включить RCON в `server.properties`
   - Использовать RCON библиотеку для отправки команд
   - Это позволит отправлять команды `/save-all`, `/list` и т.д.

2. **WebSocket для логов в реальном времени:**
   - Подключиться к Railway WebSocket для логов
   - Отображать логи в реальном времени без обновления страницы

3. **Уведомления:**
   - Email уведомления о статусе сервера
   - Push уведомления в браузере

