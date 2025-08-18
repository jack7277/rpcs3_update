import asyncio
import aiohttp
import aiofiles
import os
import subprocess
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Конфигурация ---
START_URL = "https://rpcs3.net/quickstart"
EXTRACT_PATH = r"C:\Games\rpcs3"
SEVEN_ZIP_PATH = shutil.which("7z") or shutil.which("7za") or r"C:\Program Files\7-Zip\7z.exe"


# --- Функции (остаются синхронными или адаптируются) ---

def find_download_link_selenium(url):
    """Находит ссылку на архив, используя Selenium. (Синхронная функция)"""
    print("Запуск Firefox (headless) для поиска ссылки на скачивание...")
    options = Options()
    options.add_argument("--headless")
    # Убедитесь, что geckodriver доступен
    driver = webdriver.Firefox(options=options)
    try:
        driver.get(url)
        print(f"Страница загружена: {url}")
        wait = WebDriverWait(driver, 10)
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


# --- Асинхронные функции ---

async def download_file_async(session: aiohttp.ClientSession, url: str, local_filename: str):
    """Асинхронно скачивает файл по URL."""
    print(f"Начало асинхронного скачивания файла: {url}")
    try:
        timeout = aiohttp.ClientTimeout(total=3600)  # 1 час таймаут
        async with session.get(url, allow_redirects=True, timeout=timeout) as response:
            response.raise_for_status()  # Проверка на ошибки HTTP
            # Убедимся, что папка для скачивания существует
            os.makedirs(os.path.dirname(local_filename), exist_ok=True)

            # Используем aiofiles для асинхронной записи
            async with aiofiles.open(local_filename, 'wb') as f:
                # Читаем и пишем чанками
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
        print(f"Файл успешно асинхронно скачан: {local_filename}")
        return True
    except Exception as e:
        print(f"Ошибка при асинхронном скачивании файла: {e}")
        return False


async def extract_7z_with_external_tool_async(archive_path: str, extract_to: str, seven_zip_executable: str):
    """
    Асинхронно распаковывает 7z архив с помощью внешней утилиты 7-Zip.
    """
    print(f"Начало асинхронной распаковки архива с помощью {seven_zip_executable}: {archive_path} в {extract_to}")

    if not os.path.isfile(seven_zip_executable):
        print(f"Ошибка: Исполняемый файл 7-Zip не найден по пути: {seven_zip_executable}")
        return False

    if not os.path.isfile(archive_path):
        print(f"Ошибка: Архив не найден по пути: {archive_path}")
        return False

    os.makedirs(extract_to, exist_ok=True)

    command = [seven_zip_executable, 'x', archive_path, f'-o{extract_to}', '-aoa']

    try:
        # Используем asyncio.create_subprocess_exec для асинхронного запуска
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Ждем завершения процесса
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            print("Архив успешно распакован с помощью 7-Zip.")
            print(stdout.decode()) # Опционально: вывод лога 7-Zip
            os.remove(archive_path)
            return True
        else:
            print(f"Ошибка при распаковке архива с помощью 7-Zip. Код возврата: {process.returncode}")
            print(f"Вывод stderr: {stderr.decode()}")
            return False

    except FileNotFoundError:
        print(f"Ошибка: Не удалось запустить {seven_zip_executable}. Убедитесь, что путь корректен.")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка при запуске 7-Zip: {e}")
        return False


# --- Основная асинхронная логика ---

async def main():
    """Главная асинхронная функция."""
    # 1. Найти ссылку (пока синхронно, можно обернуть в asyncio.to_thread если нужно)
    # download_url = find_download_link_selenium(START_URL)

    # Альтернатива: обернуть синхронную функцию в поток
    loop = asyncio.get_event_loop()
    download_url = await loop.run_in_executor(None, find_download_link_selenium, START_URL)

    if not download_url:
        print("Не удалось найти ссылку на архив.")
        return  # Завершаем асинхронную функцию

    # 2. Определить имя файла
    ARCHIVE_FILENAME = os.path.basename(download_url)
    print(f"Имя файла для скачивания: {ARCHIVE_FILENAME}")
    local_archive_path = os.path.join(os.getcwd(), ARCHIVE_FILENAME)

    # 3. Скачать файл (асинхронно)
    # Создаем aiohttp сессию
    timeout = aiohttp.ClientTimeout(total=3600)  # Общий таймаут для сессии
    async with aiohttp.ClientSession(timeout=timeout) as session:
        download_success = await download_file_async(session, download_url, local_archive_path)

    if not download_success:
        print("Ошибка при асинхронном скачивании файла.")
        return

    # 4. Распаковать файл (асинхронно)
    extract_success = await extract_7z_with_external_tool_async(local_archive_path, EXTRACT_PATH, SEVEN_ZIP_PATH)

    if not extract_success:
        print("Ошибка при асинхронной распаковке архива.")
        return

    print(f"RPCS3 успешно установлен (скачан и распакован) в {EXTRACT_PATH}")


# --- Точка входа ---
if __name__ == "__main__":
    # Запускаем асинхронную главную функцию
    asyncio.run(main())
