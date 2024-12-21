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

# Путь к папке с сессиями
sessions_folder = "sessions"

# Получение списка файлов в папке
sessions = [
    os.path.splitext(file)[0]  # Извлекаем имя файла без расширения
    for file in os.listdir(sessions_folder)
    if file.endswith(".session")  # Оставляем только файлы с расширением .session
]

# Проверяем, найдены ли сессии
if sessions:
    print("Найдены сессии:")
    for session in sessions:
        print(session)

    while True:  # Цикл для повторного ввода при ошибке
        session_file = input("Введите название файла сессии (например, mysession): ")

        if session_file in sessions:
            session_path = os.path.join(sessions_folder, session_file)
            print(f"Используем сессию: {session_path}")
            # Создаём клиент с api_id, api_hash и файлом сессии
            app = Client(session_path, api_id=api_id, api_hash=api_hash)
            break  # Выходим из цикла при успешном вводе
        else:
            print(f"Ошибка: Сессия '{session_file}' не найдена. Попробуйте ещё раз.")
else:
    print("Сессии не найдены. Создайте файл сессии перед использованием.")
    exit()  # Завершаем выполнение программы, если сессий нет


async def main():
    while True:
        print("\nДействие:\n1. Показать список диалогов (узнать ID)\n2. Скачать последние сообщения из чата\n"
              "3. Посмотреть участников группы\n4. Посмотреть каналы и ботов\n0. Выход")

        try:
            do = int(input("\nВведите номер действия: "))
        except ValueError:
            print("Ошибка формата ввода")
            continue

        if do == 0:
            print("Выход из программы...")
            break
        if do == 1:
            limit = int(input("Введите количество чатов для получения (0 для всех): "))
            await get_dialogs(limit, "dialogs")
        elif do == 2:
            chat_id = input("Введите ID или username чата: ")
            limit = int(input("Введите количество сообщений для получения (0 для всех): "))
            await get_history(chat_id, limit)
        elif do == 3:
            chat_id = input("Введите ID группы: ")
            limit = int(input("Введите количество участников для получения (0 для всех): "))
            await get_chat_members_list(chat_id, limit)
        elif do == 4:
            limit = int(input("Введите количество чатов для получения (0 для всех): "))
            await get_dialogs(limit, "other")
        else:
            print("Ошибка: выберите действие от 0 до 4")


async def get_dialogs(limit, search_type):
    """Выводит список диалогов"""
    async with app:
        async for dialog in app.get_dialogs(limit=limit):
            if search_type == "dialogs":
                if dialog.chat.type.name in ["PRIVATE", "GROUP", "SUPERGROUP"]:
                    print(
                        f"{dialog.chat.title or dialog.chat.first_name} (ID: {dialog.chat.id}) ({dialog.chat.type.name})")
            if search_type == "other":
                if dialog.chat.type.name in ["CHANNEL", "BOT"]:
                    print(
                        f"{dialog.chat.title or dialog.chat.first_name} (ID: {dialog.chat.id}) ({dialog.chat.type.name})")


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
        async for message in app.get_chat_history(chat_id, limit=limit):
            messages.append(message)
            counter += 1
            logging.info(f"Собрано: [{counter}/{limit}]")

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


# Функция для вывода участников чата
async def get_chat_members_list(chat_id, limit):
    """Выводит участников чата."""
    async with app:
        try:
            print(f"Получение участников чата {chat_id}...")
            members = []

            async for member in app.get_chat_members(chat_id, limit=limit):
                members.append(member)

            # Вывод участников
            print(f"Найдено {len(members)} участников:")
            for member in members:
                user = member.user
                print(
                    f"ID: {user.id}, Имя: {user.first_name or 'Неизвестное'} {user.last_name or ''}, Username: {user.username or 'Неизвестное'}")

        except Exception as e:
            print(f"Ошибка при получении участников: {e}")


app.run(main())
