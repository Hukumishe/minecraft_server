# Интеграция веб-интерфейса с Minecraft сервером через собственный API

## Обзор

Веб-интерфейс на Lovable взаимодействует напрямую с Minecraft сервером через собственный HTTP API, который запускается на том же контейнере. Не требуется использование Railway API.

## API Endpoints

Базовый URL: `http://ваш-railway-домен:8080/api` или через TCP Proxy

### 1. Статус сервера
```
GET /api/status
```

Ответ:
```json
{
  "running": true,
  "players_online": 2,
  "version": "1.21.11",
  "world_exists": true
}
```

### 2. Получение логов
```
GET /api/logs
```

Ответ:
```json
{
  "logs": "текст логов..."
}
```

### 3. Список бэкапов
```
GET /api/backups
```

Ответ:
```json
{
  "backups": [
    {
      "name": "world_20240101_120000.tar.gz",
      "size": 1048576,
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

### 4. Создание бэкапа
```
POST /api/backup/create
```

Ответ:
```json
{
  "success": true,
  "backup": {
    "name": "world_20240101_120000.tar.gz",
    "size": 1048576,
    "created_at": "2024-01-01T12:00:00"
  }
}
```

### 5. Скачивание бэкапа
```
GET /api/backup/{backup_name}
```

Возвращает файл .tar.gz для скачивания.

### 6. Восстановление бэкапа
```
POST /api/backup/restore
Body: {
  "backup_name": "world_20240101_120000.tar.gz"
}
```

Ответ:
```json
{
  "success": true,
  "message": "Мир восстановлен"
}
```

### 7. Удаление бэкапа
```
DELETE /api/backup/{backup_name}
```

Ответ:
```json
{
  "success": true,
  "message": "Бэкап удален"
}
```

### 8. Выполнение команды
```
POST /api/command
Body: {
  "command": "save-all"
}
```

Ответ:
```json
{
  "success": true,
  "message": "Команда отправлена"
}
```

### 9. Загрузка модпака
```
POST /api/upload/modpack
Content-Type: multipart/form-data
Body: {
  "modpack": <ZIP файл>
}
```

Ответ:
```json
{
  "success": true,
  "message": "Модпак успешно установлен",
  "server_jar": "server.jar"
}
```

**Важно:** 
- Принимает только ZIP архивы
- ZIP должен содержать server.jar
- Архив распаковывается, server.jar копируется в основную директорию
- Остальные файлы из архива (моды, конфиги) также копируются

## Примеры использования в веб-интерфейсе

### Получение статуса сервера

```typescript
async function getServerStatus(apiUrl: string) {
  const response = await fetch(`${apiUrl}/api/status`);
  return response.json();
}
```

### Создание бэкапа

```typescript
async function createBackup(apiUrl: string) {
  const response = await fetch(`${apiUrl}/api/backup/create`, {
    method: 'POST',
  });
  return response.json();
}
```

### Скачивание бэкапа

```typescript
async function downloadBackup(apiUrl: string, backupName: string) {
  const response = await fetch(`${apiUrl}/api/backup/${backupName}`);
  const blob = await response.blob();
  
  // Загрузить в Lovable Storage
  const formData = new FormData();
  formData.append('file', blob, backupName);
  
  // Загрузить в Lovable Storage
  const lovableUrl = await uploadToLovableStorage(formData, '/backups');
  
  return lovableUrl;
}
```

### Восстановление бэкапа

```typescript
async function restoreBackup(apiUrl: string, backupName: string) {
  // 1. Скачать из Lovable Storage
  const backupBlob = await downloadFromLovableStorage(backupUrl);
  
  // 2. Загрузить на сервер (через multipart upload)
  const formData = new FormData();
  formData.append('backup', backupBlob, backupName);
  
  const response = await fetch(`${apiUrl}/api/backup/restore`, {
    method: 'POST',
    body: JSON.stringify({ backup_name: backupName }),
    headers: { 'Content-Type': 'application/json' },
  });
  
  return response.json();
}
```

## Работа с модпаками

### Загрузка модпака

```typescript
async function uploadModpack(file: File) {
  // 1. Валидация
  if (!file.name.endsWith('.zip')) {
    throw new Error('Требуется ZIP архив');
  }
  
  // 2. Загрузить в Lovable Storage
  const lovableUrl = await uploadToLovableStorage(file, '/modpacks');
  
  // 3. Сохранить метаданные в БД
  await db.modpacks.create({
    name: file.name.replace('.zip', ''),
    filename: file.name,
    storage_path: `/modpacks/${file.name}`,
    public_url: lovableUrl,
    size: file.size,
    uploaded_at: new Date(),
  });
  
  // 4. Отправить на сервер для установки
  const formData = new FormData();
  formData.append('modpack', file);
  
  const response = await fetch(`${API_URL}/api/upload/modpack`, {
    method: 'POST',
    body: formData,
  });
  
  return response.json();
}
```

### Активация модпака

```typescript
async function activateModpack(modpackId: string) {
  // 1. Получить модпак из Lovable Storage
  const modpack = await db.modpacks.findByPk(modpackId);
  
  // 2. Скачать из Lovable Storage
  const blob = await downloadFromLovableStorage(modpack.public_url);
  const file = new File([blob], modpack.filename, { type: 'application/zip' });
  
  // 3. Отправить на сервер
  const formData = new FormData();
  formData.append('modpack', file);
  
  const response = await fetch(`${API_URL}/api/upload/modpack`, {
    method: 'POST',
    body: formData,
  });
  
  return response.json();
}
```

## Настройка API сервера

API сервер запускается автоматически вместе с Minecraft сервером. Он слушает на порту 8080 (или другом, указанном в переменной окружения).

Для доступа к API через Railway:
- Используйте TCP Proxy домен Railway
- Или используйте HTTP домен с портом 8080

## Безопасность

- API не требует аутентификации (для простоты)
- В продакшене рекомендуется добавить API ключ
- Используйте HTTPS через Railway
- Валидируйте все входящие данные

## Интеграция с автосохранением

API сервер может автоматически создавать бэкапы:
- При выходе всех игроков
- При остановке сервера
- По расписанию

Бэкапы создаются локально, затем могут быть загружены в Lovable Storage через веб-интерфейс.

