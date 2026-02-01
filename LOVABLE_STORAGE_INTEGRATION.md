# Интеграция с облачным хранилищем Lovable

## Обзор

Все файлы (модпаки, бэкапы мира, конфигурации) должны храниться в облачном хранилище Lovable, а не на Railway Volume. Это обеспечивает:
- Централизованное хранение данных
- Легкий доступ через веб-интерфейс
- Независимость от Railway инфраструктуры
- Возможность синхронизации между несколькими серверами

## Структура хранения в Lovable

### Директории:

1. **`/modpacks/`** - кастомные сборки Minecraft
   - Формат: `{name}_{version}.jar`
   - Метаданные: название, версия, дата загрузки, размер

2. **`/backups/`** - бэкапы мира
   - Формат: `world_{YYYYMMDD}_{HHMMSS}.tar.gz`
   - Метаданные: дата создания, размер, версия мира

3. **`/configs/`** - конфигурационные файлы
   - `server.properties` - настройки сервера
   - `world_settings.json` - настройки мира

## API для работы с Lovable Storage

### 1. Загрузка файла

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

### 2. Получение списка файлов

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

### 3. Скачивание файла

```typescript
async function downloadFromLovableStorage(
  fileUrl: string
): Promise<Blob> {
  const response = await fetch(fileUrl);
  return response.blob();
}
```

### 4. Удаление файла

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

## Работа с модпаками

### Загрузка модпака:

1. Пользователь загружает файл через веб-интерфейс
2. Валидация файла (.jar, размер)
3. Загрузка в Lovable Storage: `/modpacks/{filename}.jar`
4. Получение публичного URL
5. Сохранение URL в Railway переменную `CUSTOM_SERVER_URL`
6. Сохранение метаданных в базу данных Lovable

### Использование модпака:

1. При запуске сервера Railway читает `CUSTOM_SERVER_URL`
2. Сервер скачивает файл по URL из Lovable Storage
3. Сервер запускается с загруженной сборкой

## Работа с бэкапами мира

### Создание бэкапа:

1. Сервер создает архив мира: `world_YYYYMMDD_HHMMSS.tar.gz`
2. Сервер отправляет файл на веб-интерфейс (через Railway API или WebSocket)
3. Веб-интерфейс загружает файл в Lovable Storage: `/backups/world_YYYYMMDD_HHMMSS.tar.gz`
4. Сохранение метаданных в базу данных Lovable
5. Удаление локального файла с сервера

### Восстановление бэкапа:

1. Пользователь выбирает бэкап из списка
2. Веб-интерфейс получает публичный URL из Lovable Storage
3. Веб-интерфейс загружает файл на сервер через Railway API
4. Сервер распаковывает архив в директорию `/minecraft/world`
5. Перезапуск сервера

## База данных Lovable для метаданных

### Таблица: `modpacks`

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

### Таблица: `backups`

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

## Синхронизация между сервером и Lovable

### Автоматическая синхронизация бэкапов:

1. Сервер создает бэкап локально
2. Сервер отправляет HTTP запрос на веб-интерфейс с файлом
3. Веб-интерфейс загружает в Lovable Storage
4. Веб-интерфейс подтверждает успешную загрузку
5. Сервер удаляет локальный файл

### API endpoint для приема бэкапов:

```typescript
// Backend endpoint в Lovable приложении
app.post('/api/backups/upload', async (req, res) => {
  const file = req.files.backup;
  const publicUrl = await uploadToLovableStorage(
    file,
    '/backups',
    process.env.LOVABLE_API_KEY
  );
  
  // Сохранить метаданные в БД
  await db.backups.create({
    filename: file.name,
    storage_path: `/backups/${file.name}`,
    public_url: publicUrl,
    size: file.size,
  });
  
  res.json({ success: true, url: publicUrl });
});
```

## Безопасность

- Использовать Lovable API ключи для аутентификации
- Валидировать все загружаемые файлы
- Ограничить размер файлов (модпаки до 500MB, бэкапы до 2GB)
- Проверять типы файлов перед загрузкой
- Использовать HTTPS для всех запросов

## Примеры использования

### Загрузка модпака через веб-интерфейс:

```typescript
const handleModpackUpload = async (file: File) => {
  // 1. Валидация
  if (!file.name.endsWith('.jar')) {
    throw new Error('Только .jar файлы разрешены');
  }
  
  // 2. Загрузка в Lovable Storage
  const publicUrl = await uploadToLovableStorage(
    file,
    '/modpacks',
    LOVABLE_API_KEY
  );
  
  // 3. Сохранение метаданных
  await db.modpacks.create({
    name: file.name.replace('.jar', ''),
    filename: file.name,
    storage_path: `/modpacks/${file.name}`,
    public_url: publicUrl,
    size: file.size,
  });
  
  // 4. Обновление Railway переменной
  await updateRailwayVariable(
    CUSTOM_SERVER_URL_VARIABLE_ID,
    publicUrl,
    RAILWAY_API_KEY
  );
  
  toast.success('Модпак успешно загружен!');
};
```

### Список бэкапов:

```typescript
const fetchBackups = async () => {
  // Получить список из базы данных
  const backups = await db.backups.findAll({
    order: [['created_at', 'DESC']],
  });
  
  return backups;
};
```

### Восстановление бэкапа:

```typescript
const restoreBackup = async (backupId: string) => {
  // 1. Получить информацию о бэкапе
  const backup = await db.backups.findByPk(backupId);
  
  // 2. Скачать файл из Lovable Storage
  const blob = await downloadFromLovableStorage(backup.public_url);
  
  // 3. Загрузить на сервер через Railway API
  // (требует специального endpoint на сервере или через SSH)
  
  // 4. Перезапустить сервер
  await restartServer(DEPLOYMENT_ID, RAILWAY_API_KEY);
};
```

## Альтернативный подход: Прямая интеграция сервера с Lovable

Если веб-интерфейс не может принимать файлы напрямую от сервера, можно настроить сервер для прямой загрузки в Lovable:

1. Добавить Lovable API ключ в переменные окружения Railway
2. Модифицировать `autosave.sh` для загрузки бэкапов напрямую в Lovable Storage
3. Использовать curl для загрузки файлов через Lovable API

Это упрощает процесс, но требует хранения API ключей на сервере.

