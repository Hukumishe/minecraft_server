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
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import threading

# Конфигурация
API_PORT = 8080
MINECRAFT_DIR = "/minecraft"
WORLD_DIR = f"{MINECRAFT_DIR}/world"
BACKUP_DIR = f"{MINECRAFT_DIR}/backups"
SERVER_PROPERTIES = f"{MINECRAFT_DIR}/server.properties"

class MinecraftAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Обработка CORS preflight"""
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
        """Отключение стандартного логирования"""
        pass
    
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
        else:
            self.send_error_response("Not found", 404)
    
    def do_DELETE(self):
        """Обработка DELETE запросов"""
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
        """Загрузка модпака"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            # В реальности здесь будет обработка multipart/form-data
            # Для простоты принимаем URL файла
            file_url = data.get('file_url')
            if not file_url:
                self.send_error_response("URL файла не указан", 400)
                return
            
            # Сохраняем URL в переменную окружения или файл
            modpack_url_file = f"{MINECRAFT_DIR}/modpack_url.txt"
            with open(modpack_url_file, 'w') as f:
                f.write(file_url)
            
            self.send_json_response({
                "success": True,
                "message": "URL модпака сохранен",
                "url": file_url
            })
        except Exception as e:
            self.send_error_response(str(e), 500)


def run_api_server():
    """Запуск API сервера"""
    server_address = ('', API_PORT)
    httpd = HTTPServer(server_address, MinecraftAPIHandler)
    print(f"API сервер запущен на порту {API_PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    # Запускаем API сервер в отдельном потоке
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    api_thread.join()

