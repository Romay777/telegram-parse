from pyrogram import Client
from dotenv import load_dotenv
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# Загрузка переменных из .env
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

# Файл сессии
session_file = input("Введите название файла сессии (например, mysession): ")

# Создаём клиент с api_id, api_hash и файлом сессии
app = Client(session_file, api_id=api_id, api_hash=api_hash)


async def main():
    while True:
        print("\nДействие:\n 1. Показать список диалогов (узнать ID)\n2. Скачать последние сообщения из чата\n3. "
              "Перезагрузить истекшие файлы (Error 400)\n4. Посмотреть участников группы\n5. Посмотреть каналы и "
              "ботов\n0. Выход")

        try:
            do = int(input("\nВведите номер действия: "))
        except ValueError:
            print("Ошибка формата ввода")
            continue

        if do == 0:
            print("Выход из программы...")
            break
        if do == 1:
            limit = int(input("Введите количество чатов для получения: "))
            await get_dialogs(limit, "dialogs")
        elif do == 2:
            chat_id = input("Введите ID или username чата: ")
            limit = int(input("Введите количество сообщений для получения: "))
            await get_history(chat_id, limit)
        elif do == 3:
            chat_id = input("Введите ID или username чата: ")
            limit = int(input("Введите количество сообщений для получения: "))
            folder_files = input("Введите полный путь к папке с поврежденными файлами: ")
            await redownload_expired_files(chat_id, limit, folder_files)
        elif do == 4:
            chat_id = input()
            limit = int(input())
        elif do == 5:
            limit = int(input("Введите количество чатов для получения:"))
            await get_dialogs(limit, "other")
        else:
            print("Ошибка: выберите действие от 0 до 5")


async def get_dialogs(limit, search_type):
    async with app:
        async for dialog in app.get_dialogs(limit=limit):
            if search_type == "dialogs":
                if dialog.chat.type.name in ["PRIVATE", "GROUP", "SUPERGROUP"]:
                    print(f"{dialog.chat.title or dialog.chat.first_name} (ID: {dialog.chat.id}) ({dialog.chat.type.name})")
            if search_type == "other":
                if dialog.chat.type.name in ["CHANNEL", "BOT"]:
                    print(f"{dialog.chat.title or dialog.chat.first_name} (ID: {dialog.chat.id}) ({dialog.chat.type.name})")


async def get_history(chat_id, limit):
    """Получение истории сообщений из указанного чата и сохранение в текстовый файл."""
    async with app:  # Открываем клиент
        messages = []  # Список для накопления сообщений

        # Получаем информацию о чате
        chat = await app.get_chat(chat_id)
        chat_name = chat.title or chat.username or f"Unknown {chat_id}"

        # Генерация пути для сохранения файлов
        folder_name = f"chats\\{chat_name}"
        os.makedirs(folder_name, exist_ok=True)  # Создаём папку, если её нет

        print("Собираю сообщения..")
        counter = 0

        # Сбор сообщений
        async for message in app.get_chat_history(chat_id):
            messages.append(message)
            counter += 1
            logging.info(f"Собрано: [{counter}/{limit}]")
            if len(messages) >= limit:
                break

        # Сохраняем до Х сообщения с конца
        # messages = messages[:15000]

        # Генерация имени текстового файла
        file_name = os.path.join(folder_name, f"{chat_name}.txt".replace(" ", "_"))

        print("Сохраняю в файл...")
        counter = 0

        # Сохранение сообщений в файл
        with open(file_name, "w", encoding="utf-8") as file:
            for message in reversed(messages):  # Обратный порядок
                # Если файл истёк, обновляем сообщение
                if message.voice or message.photo or message.video_note or message.video or message.document:
                    message = await app.get_messages(chat_id, message.id)  # Обновляем сообщение

                # Проверка на пересланное сообщение
                if message.forward_date:
                    if message.forward_from:  # Если доступна информация о пользователе
                        file.write(f"[FWD] {message.forward_from.first_name or message.forward_from.username} ")
                    elif message.forward_from_chat:  # Если переслано из чата или канала
                        file.write(f"[FWD] {message.forward_from_chat.title} ")
                    else:
                        file.write("[FWD] Неизвестный источник ")

                if message.voice:
                    voice_file_name = os.path.join(
                        folder_name, f"V_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.ogg"
                    )
                    await message.download(file_name=voice_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username or 'Unknown'}: Голосовое сообщение сохранено как {voice_file_name}\n"
                    )
                elif message.photo:
                    photo_file_name = os.path.join(
                        folder_name, f"P_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.jpg"
                    )
                    await message.download(file_name=photo_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username or 'Unknown'}: Фото сохранено как {photo_file_name}\n"
                    )
                elif message.video_note:
                    note_file_name = os.path.join(
                        folder_name, f"VN_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.mp4"
                    )
                    await message.download(file_name=note_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username or 'Unknown'}: Кружок сохранен как {note_file_name}\n"
                    )
                elif message.video:
                    video_file_name = os.path.join(
                        folder_name, f"VID_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.mp4"
                    )
                    await message.download(file_name=video_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username or 'Unknown'}: Видео сохранено как {video_file_name}\n"
                    )
                elif message.sticker:
                    file.write(
                        f"[{message.date}] {message.from_user.username or 'Unknown'}: {'[Стикер]'}\n"
                    )
                elif message.document:
                    doc_file_name = os.path.join(
                        folder_name, f"DOC_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.pdf"
                    )
                    await message.download(file_name=doc_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username or 'Unknown'}: Документ сохранен как {doc_file_name}\n"
                    )
                else:  # Обычный текст
                    file.write(
                        f"[{message.date}] {message.from_user.username or 'Unknown'}: {message.text or ''}\n"
                    )
                counter += 1
                logging.info(f"Сохранено: [{counter}/{len(messages)}]")

        print(f"Сообщения сохранены в файл: {file_name}")


async def redownload_expired_files(chat_id, limit, expired_folder):
    """Повторная загрузка файлов, названия которых есть в папке expired."""
    async with app:  # Открываем клиент
        # Получаем список файлов в папке expired
        expired_files = os.listdir(expired_folder)
        expired_files_set = set(expired_files)  # Для быстрого поиска

        logging.info(f"Найдено {len(expired_files)} файлов в папке expired. Начинаю повторное скачивание...")
        await asyncio.sleep(1)

        # Создаём папку для сохранения повторно скачанных файлов
        redownload_folder = os.path.join(expired_folder, "redownloaded")
        os.makedirs(redownload_folder, exist_ok=True)

        messages = []
        print("Собираю сообщения..")
        counter = 0

        async for message in app.get_chat_history(chat_id):
            messages.append(message)
            counter += 1
            logging.info(f"Собрано: [{counter}/{limit}]")
            if len(messages) >= limit:
                break

        counter = 0
        # Итерируемся по сообщениям чата
        for message in reversed(messages):
            # Проверяем все медиа-файлы в сообщении
            if message.voice or message.photo or message.video_note or message.video or message.document:
                # Генерируем имя файла в соответствии с форматом
                file_name = None
                if message.voice:
                    file_name = f"V_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.ogg"
                elif message.photo:
                    file_name = f"P_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.jpg"
                elif message.video_note:
                    file_name = f"VN_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.mp4"
                elif message.video:
                    file_name = f"VID_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.mp4"
                elif message.document:
                    file_name = f"DOC_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username}.pdf"

                # Если имя файла найдено в списке expired_files
                if file_name and file_name in expired_files_set:
                    try:
                        counter += 1
                        logging.info(f"Обработка: [{counter}/{len(messages)}]")
                        logging.info(f"Повторно скачиваю файл: {file_name}")
                        new_file_path = os.path.join(redownload_folder, file_name)
                        await message.download(file_name=new_file_path)
                        logging.info(f"Файл успешно скачан: {file_name}")
                    except Exception as e:
                        logging.info(f"Ошибка при скачивании файла {file_name}: {e}")

        logging.info(f"Повторное скачивание завершено. Файлы сохранены в папке: {redownload_folder}")
        logging.info(f"Медиафайлы сохранены в папке: {redownload_folder}")


app.run(main())
