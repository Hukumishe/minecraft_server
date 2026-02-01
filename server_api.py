#!/usr/bin/env python3
"""
Простой HTTP API сервер для управления Minecraft сервером
Запускается на том же контейнере, что и Minecraft сервер
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import subprocess
import shutil
import tarfile
import zipfile
import tempfile
import cgi
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import threading

# Конфигурация
# Используем порт из переменной окружения Railway или 8080 по умолчанию
API_PORT = int(os.environ.get('API_PORT', os.environ.get('PORT', 8080)))
MINECRAFT_DIR = "/minecraft"
WORLD_DIR = f"{MINECRAFT_DIR}/world"
BACKUP_DIR = f"{MINECRAFT_DIR}/backups"
SERVER_PROPERTIES = f"{MINECRAFT_DIR}/server.properties"

class MinecraftAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Обработка CORS preflight"""
        # Логируем CORS preflight запросы
        client_ip = self.client_address[0]
        self.log_message(f"OPTIONS {self.path} - IP: {client_ip} - CORS preflight")
        
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def send_json_response(self, data, status=200):
        """Отправка JSON ответа"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_error_response(self, message, status=400):
        """Отправка ошибки"""
        self.send_json_response({"error": message}, status)
    
    def log_message(self, format, *args):
        """Логирование запросов к API"""
        # Логируем в файл и в stdout
        log_entry = format % args
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_log = f"[{timestamp}] {log_entry}\n"
        
        # Выводим в stdout (будет видно в логах Railway)
        print(full_log, end='')
        
        # Также сохраняем в файл логов API
        api_log_file = f"{MINECRAFT_DIR}/api.log"
        try:
            with open(api_log_file, 'a', encoding='utf-8') as f:
                f.write(full_log)
        except:
            pass  # Игнорируем ошибки записи в файл
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/status":
            self.get_server_status()
        elif path == "/api/logs":
            self.get_logs()
        elif path == "/api/backups":
            self.list_backups()
        elif path.startswith("/api/backup/"):
            backup_name = path.split("/")[-1]
            self.download_backup(backup_name)
        else:
            self.send_error_response("Not found", 404)
    
    def do_POST(self):
        """Обработка POST запросов"""
        # Логируем запрос
        client_ip = self.client_address[0]
        user_agent = self.headers.get('User-Agent', 'Unknown')
        content_length = self.headers.get('Content-Length', '0')
        self.log_message(f"POST {self.path} - IP: {client_ip} - Size: {content_length} bytes - User-Agent: {user_agent}")
        
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/backup/create":
            self.create_backup()
        elif path == "/api/backup/restore":
            self.restore_backup()
        elif path == "/api/command":
            self.execute_command()
        elif path == "/api/upload/modpack":
            self.upload_modpack()
        elif path == "/api/version/change":
            self.change_version()
        else:
            self.send_error_response("Not found", 404)
    
    def do_DELETE(self):
        """Обработка DELETE запросов"""
        # Логируем запрос
        client_ip = self.client_address[0]
        user_agent = self.headers.get('User-Agent', 'Unknown')
        self.log_message(f"DELETE {self.path} - IP: {client_ip} - User-Agent: {user_agent}")
        
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith("/api/backup/"):
            backup_name = path.split("/")[-1]
            self.delete_backup(backup_name)
        else:
            self.send_error_response("Not found", 404)
    
    def get_server_status(self):
        """Получение статуса сервера"""
        # Проверяем, запущен ли процесс Java (Minecraft сервер)
        try:
            result = subprocess.run(
                ["pgrep", "-f", "server.jar"],
                capture_output=True,
                text=True
            )
            is_running = result.returncode == 0
            
            # Получаем количество игроков из логов
            players_online = self.get_players_count()
            
            # Получаем версию из логов
            version = self.get_minecraft_version()
            
            self.send_json_response({
                "running": is_running,
                "players_online": players_online,
                "version": version,
                "world_exists": os.path.exists(WORLD_DIR)
            })
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def get_logs(self):
        """Получение последних логов"""
        log_file = f"{MINECRAFT_DIR}/logs/latest.log"
        lines = 100  # Последние 100 строк
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    logs = ''.join(recent_lines)
            else:
                logs = "Логи пока недоступны"
            
            self.send_json_response({"logs": logs})
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def get_players_count(self):
        """Получение количества игроков из логов"""
        log_file = f"{MINECRAFT_DIR}/logs/latest.log"
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Ищем последнее упоминание о количестве игроков
                    for line in reversed(lines):
                        if "There are" in line and "players online" in line:
                            import re
                            match = re.search(r'There are (\d+)', line)
                            if match:
                                return int(match.group(1))
        except:
            pass
        return 0
    
    def get_minecraft_version(self):
        """Получение версии Minecraft из логов"""
        log_file = f"{MINECRAFT_DIR}/logs/latest.log"
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if "Starting minecraft server version" in line:
                            import re
                            match = re.search(r'version ([\d.]+)', line)
                            if match:
                                return match.group(1)
        except:
            pass
        return "unknown"
    
    def list_backups(self):
        """Список бэкапов"""
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            backups = []
            
            for filename in os.listdir(BACKUP_DIR):
                if filename.endswith('.tar.gz'):
                    filepath = os.path.join(BACKUP_DIR, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        "name": filename,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            # Сортируем по дате создания (новые первыми)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            self.send_json_response({"backups": backups})
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def create_backup(self):
        """Создание бэкапа мира"""
        try:
            if not os.path.exists(WORLD_DIR):
                self.send_error_response("Мир не найден", 404)
                return
            
            os.makedirs(BACKUP_DIR, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"world_{timestamp}.tar.gz"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            
            # Создаем архив
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(WORLD_DIR, arcname="world")
            
            stat = os.stat(backup_path)
            
            self.send_json_response({
                "success": True,
                "backup": {
                    "name": backup_name,
                    "size": stat.st_size,
                    "created_at": datetime.now().isoformat()
                }
            })
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def download_backup(self, backup_name):
        """Скачивание бэкапа"""
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        if not os.path.exists(backup_path):
            self.send_error_response("Бэкап не найден", 404)
            return
        
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/gzip')
            self.send_header('Content-Disposition', f'attachment; filename="{backup_name}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with open(backup_path, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def restore_backup(self):
        """Восстановление бэкапа"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            backup_name = data.get('backup_name')
            if not backup_name:
                self.send_error_response("Не указано имя бэкапа", 400)
                return
            
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            if not os.path.exists(backup_path):
                self.send_error_response("Бэкап не найден", 404)
                return
            
            # Распаковываем бэкап
            if os.path.exists(WORLD_DIR):
                shutil.rmtree(WORLD_DIR)
            
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(MINECRAFT_DIR)
            
            self.send_json_response({"success": True, "message": "Мир восстановлен"})
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def delete_backup(self, backup_name):
        """Удаление бэкапа"""
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        if not os.path.exists(backup_path):
            self.send_error_response("Бэкап не найден", 404)
            return
        
        try:
            os.remove(backup_path)
            self.send_json_response({"success": True, "message": "Бэкап удален"})
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def execute_command(self):
        """Выполнение команды на сервере (через RCON или файл команд)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            command = data.get('command')
            if not command:
                self.send_error_response("Команда не указана", 400)
                return
            
            # Если включен RCON, можно использовать его
            # Иначе сохраняем команду в файл для обработки
            commands_file = f"{MINECRAFT_DIR}/commands.txt"
            with open(commands_file, 'a') as f:
                f.write(f"{command}\n")
            
            self.send_json_response({"success": True, "message": "Команда отправлена"})
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def upload_modpack(self):
        """Загрузка и установка модпака (ZIP архив)"""
        try:
            
            # Парсим multipart/form-data
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error_response("Требуется multipart/form-data", 400)
                return
            
            # Читаем данные
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Парсим multipart данные
            form = cgi.FieldStorage(
                fp=tempfile.BytesIO(post_data),
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            if 'modpack' not in form:
                self.send_error_response("Файл модпака не найден", 400)
                return
            
            file_item = form['modpack']
            if not file_item.filename.endswith('.zip'):
                self.send_error_response("Требуется ZIP архив", 400)
                return
            
            # Сохраняем временный файл
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            file_item.file.seek(0)
            temp_zip.write(file_item.file.read())
            temp_zip.close()
            
            # Распаковываем ZIP
            modpack_dir = f"{MINECRAFT_DIR}/modpack"
            if os.path.exists(modpack_dir):
                shutil.rmtree(modpack_dir)
            os.makedirs(modpack_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                zip_ref.extractall(modpack_dir)
            
            # Ищем server.jar в распакованном архиве
            server_jar = None
            for root, dirs, files in os.walk(modpack_dir):
                if 'server.jar' in files:
                    server_jar = os.path.join(root, 'server.jar')
                    break
            
            if not server_jar:
                # Если server.jar не найден, ищем любой .jar файл
                for root, dirs, files in os.walk(modpack_dir):
                    for file in files:
                        if file.endswith('.jar'):
                            server_jar = os.path.join(root, file)
                            break
                    if server_jar:
                        break
            
            if not server_jar:
                shutil.rmtree(modpack_dir)
                os.unlink(temp_zip.name)
                self.send_error_response("server.jar не найден в архиве", 400)
                return
            
            # Копируем server.jar в основную директорию
            target_jar = f"{MINECRAFT_DIR}/server.jar"
            if os.path.exists(target_jar):
                # Делаем бэкап старого сервера
                backup_jar = f"{MINECRAFT_DIR}/server.jar.backup"
                shutil.copy2(target_jar, backup_jar)
            
            shutil.copy2(server_jar, target_jar)
            
            # Копируем остальные файлы из модпака (моды, конфиги и т.д.)
            for root, dirs, files in os.walk(modpack_dir):
                for file in files:
                    if file != 'server.jar' and not file.endswith('.jar'):
                        src = os.path.join(root, file)
                        rel_path = os.path.relpath(src, modpack_dir)
                        dst = os.path.join(MINECRAFT_DIR, rel_path)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
            
            # Удаляем временные файлы
            shutil.rmtree(modpack_dir)
            os.unlink(temp_zip.name)
            
            self.send_json_response({
                "success": True,
                "message": "Модпак успешно установлен",
                "server_jar": os.path.basename(server_jar)
            })
        except zipfile.BadZipFile:
            self.send_error_response("Некорректный ZIP архив", 400)
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def get_version(self):
        """Получение текущей версии Minecraft"""
        try:
            version_file = f"{MINECRAFT_DIR}/.minecraft_version"
            current_version = "unknown"
            
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    current_version = f.read().strip()
            else:
                # Пытаемся определить из логов
                current_version = self.get_minecraft_version()
            
            # Получаем доступные версии
            try:
                version_manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
                result = subprocess.run(
                    ["curl", "-s", version_manifest_url],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                manifest = json.loads(result.stdout)
                available_versions = [v["id"] for v in manifest["versions"][:20]]  # Последние 20 версий
                latest_version = manifest["latest"]["release"]
            except:
                available_versions = []
                latest_version = "unknown"
            
            self.send_json_response({
                "current_version": current_version,
                "latest_version": latest_version,
                "available_versions": available_versions
            })
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def change_version(self):
        """Изменение версии Minecraft"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            new_version = data.get('version')
            if not new_version:
                self.send_error_response("Версия не указана", 400)
                return
            
            # Сохраняем версию в файл
            version_file = f"{MINECRAFT_DIR}/.minecraft_version"
            with open(version_file, 'w') as f:
                f.write(new_version)
            
            # Удаляем старый server.jar, чтобы скачался новый
            old_jar = f"{MINECRAFT_DIR}/server.jar"
            if os.path.exists(old_jar):
                backup_jar = f"{MINECRAFT_DIR}/server.jar.backup"
                if os.path.exists(backup_jar):
                    os.remove(backup_jar)
                shutil.copy2(old_jar, backup_jar)
                os.remove(old_jar)
            
            self.send_json_response({
                "success": True,
                "message": f"Версия изменена на {new_version}. Перезапустите сервер для применения изменений.",
                "version": new_version
            })
        except Exception as e:
            self.send_error_response(str(e), 500)


def run_api_server():
    """Запуск API сервера"""
    server_address = ('', API_PORT)
    httpd = HTTPServer(server_address, MinecraftAPIHandler)
    print(f"API сервер запущен на порту {API_PORT}")
    print(f"Доступен по адресу: http://0.0.0.0:{API_PORT}/api")
    httpd.serve_forever()


if __name__ == "__main__":
    # Запускаем API сервер
    run_api_server()

