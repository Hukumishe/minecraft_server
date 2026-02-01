# Полное руководство: Веб-интерфейс управления Minecraft сервером на Lovable

## ПРОМПТ ДЛЯ LOVABLE

Создай современное веб-приложение для управления Minecraft сервером на Railway с темной темой в стиле Minecraft.

---

## СТРУКТУРА ПРИЛОЖЕНИЯ

### 1. Dashboard (/) - главная страница:
- Карточка со статусом сервера (зеленый/красный/желтый индикатор)
- Быстрые действия: Запустить/Остановить/Перезапустить
- График использования ресурсов (CPU, память)
- Последние события/логи
- Навигация на все страницы

### 2. Загрузка сборки (/upload):
- Drag & Drop или выбор файла для загрузки модпака (ZIP архив)
- Валидация файла (должен быть .zip архив)
- Проверка размера файла (максимум, например, 500MB)
- Индикатор загрузки с прогрессом
- Сообщения об успехе/ошибке
- Загрузка ZIP архива напрямую в облачное хранилище Lovable (используй Lovable Storage API)
- После загрузки сохраняй метаданные в базу данных Lovable (название, размер, дата загрузки)
- Отправка файла на сервер через POST /api/upload/modpack (multipart/form-data)
- Сервер распаковывает ZIP и использует server.jar из архива
- Список загруженных модпаков из Lovable Storage:
  * Название модпака
  * Размер архива
  * Дата загрузки
  * Кнопка "Активировать" (отправить на сервер)
  * Кнопка "Удалить" (из Lovable Storage)
- Только один активный модпак может быть на сервере

### 3. Настройки мира (/world-settings):
- Название мира (input, по умолчанию "world")
- Seed (input, опционально)
- Режим игры (select): Survival, Creative, Adventure, Spectator
- Сложность (select): Peaceful, Easy, Normal, Hard
- Toggle переключатели:
  * Разрешить PvP
  * Генерировать структуры
  * Разрешить Nether
  * Разрешить End
- Максимальное количество игроков (number, по умолчанию 5)
- Расстояние прорисовки (slider 4-32)
- Расстояние симуляции (slider 4-32)
- Кнопка "Сохранить настройки" - сохраняет в базу данных Lovable
- Кнопка "Сбросить к умолчаниям"

### 4. Управление сервером (/server):
- Статус сервера с индикатором (получай через GET /api/status)
- Кнопки управления: Запустить/Остановить/Перезапустить (через команды на сервере)
- Просмотр логов в реальном времени (получай через GET /api/logs, обновляй каждые 2-3 секунды)
- Фильтрация логов по уровню (INFO, WARN, ERROR) - на клиенте
- Информация о сервере (из GET /api/status):
  * Версия Minecraft
  * Игроки онлайн
  * Статус запуска
- TCP Proxy адрес с кнопкой "Копировать" (вводится вручную или из настроек)
- QR код для быстрого подключения (опционально)

### 5. Сохранения (/backups):
- Toggle "Автосохранение при выходе всех игроков"
- Toggle "Автосохранение при остановке сервера"
- Интервал автосохранения (select): 5, 10, 15, 30 минут
- Кнопка "Сохранить мир сейчас" (POST /api/backup/create)
- Список сохранений:
  * Получай список с сервера (GET /api/backups)
  * И синхронизируй с Lovable Storage
  * Для каждого бэкапа:
    - Дата и время
    - Размер файла
    - Кнопка "Скачать с сервера" (GET /api/backup/{name})
    - Кнопка "Загрузить в Lovable" (скачать с сервера → загрузить в Lovable Storage)
    - Кнопка "Восстановить" (POST /api/backup/restore) - если файл в Lovable, сначала скачай на сервер
    - Кнопка "Удалить с сервера" (DELETE /api/backup/{name})
    - Кнопка "Удалить из Lovable" (через Lovable Storage API)
- Настройка максимального количества сохранений (сохраняется в Lovable БД)
- Toggle "Автоматическое удаление старых сохранений"
- Все бэкапы синхронизируются между сервером и Lovable Storage

---

## ТЕХНИЧЕСКИЙ СТЕК

- React 18+ с TypeScript
- Tailwind CSS или shadcn/ui для UI
- Zustand для state management
- React Query для API запросов
- Axios для HTTP
- React Hook Form + Zod для форм и валидации

---

## ИНТЕГРАЦИЯ С МИНЕКРАФТ СЕРВЕРОМ

### Настройка подключения

На сервере запущен собственный HTTP API на порту 8080. Для доступа используйте:

**Вариант 1: Через HTTP домен Railway**
- Базовый URL: `http://minecraftserver-production-f41c.up.railway.app:8080/api`
- Порт 8080 должен быть доступен через HTTP домен

**Вариант 2: Через TCP Proxy (рекомендуется)**
- TCP Proxy: `gondola.proxy.rlwy.net:21644`
- Внутренний порт: 25565 (для Minecraft)
- Для API используйте тот же TCP Proxy, но обратите внимание, что API на порту 8080
- Возможно, потребуется создать отдельный TCP Proxy для порта 8080

**Важно:** Убедитесь, что порт 8080 доступен через Railway. Если нет, используйте переменную окружения для настройки порта API.

### API Endpoints

Все endpoints возвращают JSON (кроме скачивания файлов). CORS включен для всех запросов.

#### 1. Статус сервера
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

#### 2. Получение логов
```
GET /api/logs
```

Ответ:
```json
{
  "logs": "текст логов..."
}
```

#### 3. Список бэкапов
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

#### 4. Создание бэкапа
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

#### 5. Скачивание бэкапа
```
GET /api/backup/{backup_name}
```

Возвращает файл .tar.gz для скачивания.

#### 6. Восстановление бэкапа
```
POST /api/backup/restore
Content-Type: application/json
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

#### 7. Удаление бэкапа
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

#### 8. Выполнение команды
```
POST /api/command
Content-Type: application/json
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

#### 9. Загрузка модпака
```
POST /api/upload/modpack
Content-Type: multipart/form-data
Body: {
  "modpack": <ZIP файл>
}
```

**Важно:** 
- Принимает только ZIP архивы
- ZIP должен содержать server.jar
- Архив распаковывается, server.jar копируется в основную директорию
- Остальные файлы из архива (моды, конфиги) также копируются

Ответ:
```json
{
  "success": true,
  "message": "Модпак успешно установлен",
  "server_jar": "server.jar"
}
```

---

## РАБОТА С ДАННЫМИ

### Хранение файлов

Все файлы (модпаки, бэкапы) хранятся в облачном хранилище Lovable:
- Модпаки: `/modpacks/` в Lovable Storage
- Бэкапы: `/backups/` в Lovable Storage
- Метаданные (списки файлов, настройки) хранятся в базе данных Lovable

### Процесс работы

**Загрузка модпака:**
1. Пользователь загружает ZIP через веб-интерфейс
2. Файл сохраняется в Lovable Storage
3. Метаданные сохраняются в БД Lovable
4. ZIP отправляется на сервер через API
5. Сервер распаковывает и устанавливает модпак

**Создание бэкапа:**
1. Сервер создает архив через API
2. Веб-интерфейс скачивает бэкап с сервера
3. Загружает в Lovable Storage
4. Сохраняет метаданные в БД
5. Удаляет локальный файл с сервера (опционально)

**Восстановление бэкапа:**
1. Пользователь выбирает бэкап из Lovable Storage
2. Файл скачивается из Lovable Storage
3. Загружается на сервер через API
4. Сервер распаковывает и восстанавливает мир

---

## ИНТЕГРАЦИЯ С LOVABLE STORAGE

### API для работы с файлами

#### 1. Загрузка файла

```typescript
async function uploadToLovableStorage(
  file: File,
  directory: string,
  apiKey: string
): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('directory', directory);
  
  const response = await fetch('https://api.lovable.dev/storage/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
    },
    body: formData,
  });
  
  const data = await response.json();
  return data.publicUrl; // Публичный URL для доступа к файлу
}
```

#### 2. Получение списка файлов

```typescript
async function listLovableStorageFiles(
  directory: string,
  apiKey: string
): Promise<FileInfo[]> {
  const response = await fetch(
    `https://api.lovable.dev/storage/list?directory=${directory}`,
    {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    }
  );
  
  return response.json();
}

interface FileInfo {
  name: string;
  size: number;
  createdAt: string;
  publicUrl: string;
}
```

#### 3. Скачивание файла

```typescript
async function downloadFromLovableStorage(
  fileUrl: string
): Promise<Blob> {
  const response = await fetch(fileUrl);
  return response.blob();
}
```

#### 4. Удаление файла

```typescript
async function deleteFromLovableStorage(
  filePath: string,
  apiKey: string
): Promise<void> {
  await fetch(`https://api.lovable.dev/storage/delete`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ path: filePath }),
  });
}
```

---

## ПРИМЕРЫ КОДА

### Получение статуса сервера

```typescript
const API_BASE_URL = 'http://minecraftserver-production-f41c.up.railway.app:8080/api';
// Или через TCP Proxy, если настроен отдельный порт для API

async function getServerStatus() {
  const response = await fetch(`${API_BASE_URL}/status`);
  return response.json();
}
```

### Загрузка модпака

```typescript
async function uploadModpack(file: File) {
  // 1. Валидация
  if (!file.name.endsWith('.zip')) {
    throw new Error('Требуется ZIP архив');
  }
  
  if (file.size > 500 * 1024 * 1024) { // 500MB
    throw new Error('Файл слишком большой (максимум 500MB)');
  }
  
  // 2. Загрузить в Lovable Storage
  const lovableUrl = await uploadToLovableStorage(file, '/modpacks', LOVABLE_API_KEY);
  
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
  
  const response = await fetch(`${API_BASE_URL}/upload/modpack`, {
    method: 'POST',
    body: formData,
  });
  
  return response.json();
}
```

### Активация модпака из списка

```typescript
async function activateModpack(modpackId: string) {
  // 1. Получить модпак из БД
  const modpack = await db.modpacks.findByPk(modpackId);
  
  // 2. Скачать из Lovable Storage
  const blob = await downloadFromLovableStorage(modpack.public_url);
  const file = new File([blob], modpack.filename, { type: 'application/zip' });
  
  // 3. Отправить на сервер
  const formData = new FormData();
  formData.append('modpack', file);
  
  const response = await fetch(`${API_BASE_URL}/upload/modpack`, {
    method: 'POST',
    body: formData,
  });
  
  return response.json();
}
```

### Создание бэкапа

```typescript
async function createBackup() {
  // 1. Создать бэкап на сервере
  const response = await fetch(`${API_BASE_URL}/backup/create`, {
    method: 'POST',
  });
  
  const data = await response.json();
  const backupName = data.backup.name;
  
  // 2. Скачать бэкап с сервера
  const backupBlob = await fetch(`${API_BASE_URL}/backup/${backupName}`)
    .then(res => res.blob());
  
  // 3. Загрузить в Lovable Storage
  const file = new File([backupBlob], backupName, { type: 'application/gzip' });
  const lovableUrl = await uploadToLovableStorage(file, '/backups', LOVABLE_API_KEY);
  
  // 4. Сохранить метаданные в БД
  await db.backups.create({
    world_name: 'world',
    filename: backupName,
    storage_path: `/backups/${backupName}`,
    public_url: lovableUrl,
    size: file.size,
    created_at: new Date(),
  });
  
  // 5. Удалить с сервера (опционально)
  await fetch(`${API_BASE_URL}/backup/${backupName}`, {
    method: 'DELETE',
  });
  
  return { success: true, backup: data.backup };
}
```

### Восстановление бэкапа

```typescript
async function restoreBackup(backupId: string) {
  // 1. Получить информацию о бэкапе из БД
  const backup = await db.backups.findByPk(backupId);
  
  // 2. Скачать из Lovable Storage
  const blob = await downloadFromLovableStorage(backup.public_url);
  
  // 3. Загрузить на сервер (через multipart upload или напрямую)
  // Для простоты используем прямой путь - если бэкап уже на сервере
  // Или загружаем через специальный endpoint
  
  // 4. Восстановить
  const response = await fetch(`${API_BASE_URL}/backup/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ backup_name: backup.filename }),
  });
  
  return response.json();
}
```

### Просмотр логов в реальном времени

```typescript
function useServerLogs() {
  const [logs, setLogs] = useState('');
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const response = await fetch(`${API_BASE_URL}/logs`);
      const data = await response.json();
      setLogs(data.logs);
    }, 3000); // Обновление каждые 3 секунды
    
    return () => clearInterval(interval);
  }, []);
  
  return logs;
}
```

---

## БАЗА ДАННЫХ LOVABLE

### Таблица: modpacks

```sql
CREATE TABLE modpacks (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  version VARCHAR(50),
  filename VARCHAR(255) NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  public_url VARCHAR(500) NOT NULL,
  size BIGINT NOT NULL,
  uploaded_at TIMESTAMP DEFAULT NOW(),
  is_active BOOLEAN DEFAULT FALSE
);
```

### Таблица: backups

```sql
CREATE TABLE backups (
  id UUID PRIMARY KEY,
  world_name VARCHAR(255) NOT NULL,
  filename VARCHAR(255) NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  public_url VARCHAR(500) NOT NULL,
  size BIGINT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  minecraft_version VARCHAR(50),
  player_count INTEGER DEFAULT 0
);
```

### Таблица: world_settings

```sql
CREATE TABLE world_settings (
  id UUID PRIMARY KEY,
  world_name VARCHAR(255) NOT NULL DEFAULT 'world',
  seed VARCHAR(255),
  gamemode VARCHAR(20) DEFAULT 'survival',
  difficulty VARCHAR(20) DEFAULT 'normal',
  pvp_enabled BOOLEAN DEFAULT true,
  generate_structures BOOLEAN DEFAULT true,
  allow_nether BOOLEAN DEFAULT true,
  allow_end BOOLEAN DEFAULT true,
  max_players INTEGER DEFAULT 5,
  view_distance INTEGER DEFAULT 10,
  simulation_distance INTEGER DEFAULT 10,
  updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## ДИЗАЙН

- Темная тема в стиле Minecraft (зеленые акценты #55C55A)
- Современные карточки и компоненты
- Адаптивный дизайн (работает на десктопе и мобильных)
- Toast уведомления для всех действий (успех/ошибка)
- Индикаторы загрузки для долгих операций
- Плавные анимации и переходы
- Иконки для всех действий (Lucide React или Heroicons)

---

## БЕЗОПАСНОСТЬ

- Хранить Lovable API ключи в переменных окружения
- Валидировать все пользовательские вводы
- Ограничить размер файлов (модпаки до 500MB, бэкапы до 2GB)
- Проверять типы файлов перед загрузкой
- Использовать HTTPS для всех запросов (через Railway)

---

## НАЧАЛО РАБОТЫ

1. Создай структуру приложения с навигацией (sidebar)
2. Реализуй все страницы с базовой функциональностью
3. Интегрируй API сервера Minecraft для получения статуса и управления
4. Интегрируй Lovable Storage для хранения всех файлов (модпаки, бэкапы)
5. Настрой базу данных Lovable для метаданных
6. Используй современный UI с темной темой

API сервер уже запущен на сервере, просто подключайся к нему через Railway домен или TCP Proxy.

---

## ДОПОЛНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ

- При загрузке модпака сервер автоматически перезапустится с новой сборкой
- Бэкапы создаются автоматически при выходе всех игроков (если включено)
- Логи обновляются в реальном времени каждые 2-3 секунды
- Все файлы синхронизируются между сервером и Lovable Storage
- Настройки мира применяются при создании нового мира

