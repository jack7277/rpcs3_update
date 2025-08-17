import os
import shutil  # Для проверки наличия исполняемого файла
import subprocess  # Для запуска внешних команд

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- Конфигурация ---
START_URL = "https://rpcs3.net/quickstart"
# Путь к каталогу для распаковки
EXTRACT_PATH = r"C:\Games\rpcs3"

# Путь к исполняемому файлу 7-Zip. Попробуем найти его в PATH.
# Если не найден, укажите полный путь, например: r"C:\Program Files\7-Zip\7z.exe"
SEVEN_ZIP_PATH = shutil.which("7z") or shutil.which("7za")  # Попробуем '7z' или '7za'

if not SEVEN_ZIP_PATH:
    # Если не найден в PATH, задайте путь вручную
    SEVEN_ZIP_PATH = r"C:\Program Files\7-Zip\7z.exe"  # <-- Укажите путь, если нужно

print(f"Путь к 7-Zip: {SEVEN_ZIP_PATH}")


# --- Функции ---

def find_download_link_selenium(url):
    """Находит ссылку на архив, используя Selenium."""
    print("Запуск Firefox (headless) для поиска ссылки на скачивание...")
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    try:
        driver.get(url)
        print(f"Страница загружена: {url}")
        wait = WebDriverWait(driver, 10)
        # Ищем ссылку с 'win64' и '.7z' в href
        download_link_element = wait.until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'win64') and contains(@href, '.7z')]"))
        )
        download_url = download_link_element.get_attribute("href")
        print(f"Найдена ссылка для скачивания: {download_url}")
        return download_url
    except Exception as e:
        print(f"Ошибка при поиске ссылки с помощью Selenium: {e}")
        return None
    finally:
        driver.quit()
        print("Браузер закрыт.")


def download_file(url, local_filename):
    """Скачивает файл по URL."""
    print(f"Начало скачивания файла: {url}")
    try:
        with requests.get(url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            os.makedirs(os.path.dirname(local_filename), exist_ok=True)
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Файл успешно скачан: {local_filename}")
        return True
    except Exception as e:
        print(f"Ошибка при скачивании файла: {e}")
        return False


def extract_7z_with_external_tool(archive_path, extract_to, seven_zip_executable):
    """
    Распаковывает 7z архив с помощью внешней утилиты 7-Zip.
    """
    print(f"Начало распаковки архива с помощью {seven_zip_executable}: {archive_path} в {extract_to}")

    # Проверка существования утилиты 7-Zip
    if not os.path.isfile(seven_zip_executable):
        print(f"Ошибка: Исполняемый файл 7-Zip не найден по пути: {seven_zip_executable}")
        return False

    # Проверка существования архива
    if not os.path.isfile(archive_path):
        print(f"Ошибка: Архив не найден по пути: {archive_path}")
        return False

    # Создание папки назначения, если она не существует
    os.makedirs(extract_to, exist_ok=True)

    # Команда для 7-Zip: `7z x <архив> -o<папка_назначения>`
    # -aoa: Перезаписывать все существующие файлы без запроса
    command = [seven_zip_executable, 'x', archive_path, f'-o{extract_to}', '-aoa']

    try:
        # Запуск команды и ожидание завершения
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Архив успешно распакован с помощью 7-Zip.")
        print(result.stdout)  # Вывод лога 7-Zip (если есть)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при распаковке архива с помощью 7-Zip: {e}")
        print(f"Код возврата: {e.returncode}")
        print(f"Вывод stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Ошибка: Не удалось запустить {seven_zip_executable}. Убедитесь, что путь корректен.")
        return False


# --- Основная логика ---
if __name__ == "__main__":
    # 1. Найти ссылку на скачивание
    download_url = find_download_link_selenium(START_URL)

    if not download_url:
        print("Не удалось найти ссылку на архив.")
    else:
        # 2. Определить имя файла из URL
        ARCHIVE_FILENAME = os.path.basename(download_url)
        print(f"Имя файла для скачивания: {ARCHIVE_FILENAME}")

        # Путь для сохранения скачанного архива
        local_archive_path = os.path.join(os.getcwd(), ARCHIVE_FILENAME)

        # 3. Скачать файл
        if download_file(download_url, local_archive_path):
            # 4. Распаковать файл с помощью внешней утилиты 7-Zip
            if extract_7z_with_external_tool(local_archive_path, EXTRACT_PATH, SEVEN_ZIP_PATH):
                print(f"RPCS3 успешно установлен (распакован) в {EXTRACT_PATH}")
                # Опционально: удалить архив после распаковки
                # try:
                #     os.remove(local_archive_path)
                #     print(f"Архив {local_archive_path} удален.")
                # except OSError as e:
                #     print(f"Не удалось удалить архив: {e}")
            else:
                print("Ошибка при распаковке архива с помощью внешней утилиты.")
        else:
            print("Ошибка при скачивании файла.")
