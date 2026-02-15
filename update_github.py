#!/usr/bin/env python3
"""
🚀 Автоматическое обновление проекта на GitHub
Использование: python update_github.py [путь_к_проекту] [сообщение_коммита]
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI цвета для терминала"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color


def print_success(message):
    """Вывод успешного сообщения"""
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")


def print_warning(message):
    """Вывод предупреждения"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")


def print_error(message):
    """Вывод ошибки"""
    print(f"{Colors.RED}❌ {message}{Colors.NC}")


def run_command(command, cwd=None, check=True):
    """Выполнение команды в терминале"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def main():
    # Определяем путь к проекту
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1]).resolve()
    else:
        project_path = Path.cwd()

    # Проверяем существование директории
    if not project_path.exists() or not project_path.is_dir():
        print_error(f"Директория не найдена: {project_path}")
        sys.exit(1)

    # Проверяем, что это git репозиторий
    git_dir = project_path / ".git"
    if not git_dir.exists():
        print_error("Это не git репозиторий!")
        sys.exit(1)

    print_success(f"Найден проект: {project_path}")

    # Получаем сообщение коммита
    if len(sys.argv) > 2:
        commit_message = " ".join(sys.argv[2:])
    else:
        commit_message = f"Обновление проекта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    print_warning(f"Сообщение коммита: {commit_message}")

    # Проверяем статус репозитория
    print()
    print_warning("Проверка изменений...")
    success, stdout, stderr = run_command("git status --short", cwd=project_path, check=False)
    if stdout:
        print(stdout)

    # Проверяем, есть ли изменения
    success, stdout, stderr = run_command("git status --porcelain", cwd=project_path, check=False)
    if not stdout.strip():
        print_warning("Нет изменений для коммита")
        sys.exit(0)

    # Добавляем все изменения
    print()
    print_warning("Добавление всех изменений...")
    success, stdout, stderr = run_command("git add .", cwd=project_path)
    if not success:
        print_error("Ошибка при добавлении файлов")
        print_error(stderr)
        sys.exit(1)

    print_success("Файлы добавлены")

    # Создаем коммит
    print()
    print_warning("Создание коммита...")
    success, stdout, stderr = run_command(
        f'git commit -m "{commit_message}"',
        cwd=project_path
    )
    if not success:
        print_error("Ошибка при создании коммита")
        print_error(stderr)
        sys.exit(1)

    print_success("Коммит создан")

    # Получаем имя текущей ветки
    success, stdout, stderr = run_command("git branch --show-current", cwd=project_path)
    current_branch = stdout.strip() if success else "main"
    print_warning(f"Текущая ветка: {current_branch}")

    # Пушим изменения
    print()
    print_warning("Отправка изменений на GitHub...")
    success, stdout, stderr = run_command(
        f"git push origin {current_branch}",
        cwd=project_path
    )
    if not success:
        print_error("Ошибка при отправке на GitHub")
        print_warning("Возможно, нужно настроить удаленный репозиторий:")
        print_warning("git remote add origin https://github.com/username/repo.git")
        print_error(stderr)
        sys.exit(1)

    print_success("Изменения успешно отправлены на GitHub!")
    print()
    print_success(f"Проект обновлен: {project_path}")
    print_success(f"Ветка: {current_branch}")
    print_success(f"Коммит: {commit_message}")


if __name__ == "__main__":
    main()

