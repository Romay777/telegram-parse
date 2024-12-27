from pyrogram import Client
from dotenv import load_dotenv
import asyncio
import os
import logging

from pyrogram.errors import PhoneCodeInvalid, SessionPasswordNeeded, FloodWait
from pyrogram.raw.functions.messages import DeleteHistory

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# Загрузка переменных из .env
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

# Path to the sessions folder
sessions_folder = "sessions"
os.makedirs(sessions_folder, exist_ok=True)  # Ensure the sessions folder exists

# Get the list of session files
sessions = [
    os.path.splitext(file)[0]  # Extract the file name without the extension
    for file in os.listdir(sessions_folder)
    if file.endswith(".session")  # Only include .session files
]

# Check if sessions are found
if sessions:
    print("\n\033[32mНайдены сессии: \033[0m")
    for session in sessions:
        print(session)
else:
    print("\n\033[37mНайдены сессии: \033[0m")

# Ask the user if they want to create a new session
create_new_session = input("Хотите создать новую сессию? (да/нет): ").strip().lower()

if create_new_session == "да":
    # Create a new session
    session_name = input("Введите имя новой сессии (например, mysession): ").strip()
    session_path = os.path.join(sessions_folder, session_name)

    # Create a new client for the session
    app = Client(session_path, api_id=api_id, api_hash=api_hash)


    # Start the client to initiate login
    async def create_session():
        try:
            await app.start()
            print("Сессия успешно создана и сохранена.")
        except PhoneCodeInvalid:
            print("Ошибка: Неверный код подтверждения.")
        except SessionPasswordNeeded:
            password = input("Введите пароль для двухфакторной аутентификации: ")
            await app.check_password(password)
            print("Аутентификация прошла успешно.")
        except FloodWait as e:
            print(f"Ошибка: Слишком много запросов. Подождите {e} секунд.")
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            await app.stop()


    # Run the session creation function
    asyncio.run(create_session())

    # Add the new session to the list of available sessions
    sessions.append(session_name)

# If the user doesn't want to create a new session, proceed with existing sessions
if not sessions:
    print("Сессии не найдены. Создайте файл сессии перед использованием.")
    exit()  # Exit the program if no sessions are available

# Prompt the user to select an existing session
while True:
    session_file = input("Введите название файла сессии (например, mysession): ")

    if session_file in sessions:
        session_path = os.path.join(sessions_folder, session_file)
        print(f"Используем сессию: {session_path}")
        # Create the client with the selected session
        app = Client(session_path, api_id=api_id, api_hash=api_hash)
        break  # Exit the loop if a valid session is selected
    else:
        print(f"Ошибка: Сессия '{session_file}' не найдена. Попробуйте ещё раз.")


async def main():
    while True:
        print("\nДействие:\n1. Показать список диалогов (узнать ID)\n2. Скачать последние сообщения из чата\n"
              "3. Посмотреть участников группы\n4. Посмотреть каналы и ботов\n5. Удалить переписку\n6. Показать "
              "только ЛС\n0. Выход")

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
            text_only = bool(int(input("Только текст? [0/1]: ")))
            await get_history(chat_id, limit, text_only)
        elif do == 3:
            chat_id = input("Введите ID группы: ")
            limit = int(input("Введите количество участников для получения (0 для всех): "))
            await get_chat_members_list(chat_id, limit)
        elif do == 4:
            limit = int(input("Введите количество чатов для получения (0 для всех): "))
            await get_dialogs(limit, "other")
        elif do == 5:
            chat_id = input("Введите ID или username чата: ")
            await delete_chat_history(chat_id)
        elif do == 6:
            limit = int(input("Введите количество чатов для получения (0 для всех): "))
            await get_dialogs(limit, "private")
        else:
            print("Ошибка: выберите действие от 0 до 6")


async def get_dialogs(limit, search_type):
    """Выводит список диалогов и сохраняет их в файл"""
    async with app:
        # Создаем папку output если её нет
        os.makedirs("output", exist_ok=True)

        # Создаем папку для текущей сессии
        session_folder = os.path.join("output", session_file)
        os.makedirs(session_folder, exist_ok=True)

        # Путь к файлу с диалогами
        if search_type == "dialogs":
            output_file = os.path.join(session_folder, "dialogs.txt")
        elif search_type == "other":
            output_file = os.path.join(session_folder, "channels.txt")
        else:
            output_file = os.path.join(session_folder, "privates.txt")

        # Открываем файл для записи
        with open(output_file, "w", encoding="utf-8") as f:
            async for dialog in app.get_dialogs(limit=limit):
                last_message_date = dialog.top_message.date.strftime(
                    "%Y-%m-%d %H:%M:%S") if dialog.top_message else "Нет сообщений"

                if search_type == "dialogs":
                    if dialog.chat.type.name in ["PRIVATE", "GROUP", "SUPERGROUP"]:
                        output = f"{dialog.chat.title or dialog.chat.first_name} (ID: {dialog.chat.id}) ({dialog.chat.type.name}) | Last Message: {last_message_date}"
                        print(output)  # Выводим в консоль
                        f.write(output + "\n")  # Записываем в файл

                if search_type == "other":
                    if dialog.chat.type.name in ["CHANNEL", "BOT"]:
                        output = f"{dialog.chat.title or dialog.chat.first_name} (ID: {dialog.chat.id}) ({dialog.chat.type.name})"
                        print(output)  # Выводим в консоль
                        f.write(output + "\n")  # Записываем в файл

                if search_type == "private":
                    if dialog.chat.type.name == "PRIVATE":
                        output = f"{dialog.chat.title or dialog.chat.first_name} (ID: {dialog.chat.id}) ({dialog.chat.type.name}) | Last Message: {last_message_date}"
                        print(output)  # Выводим в консоль
                        f.write(output + "\n")  # Записываем в файл

        print(f"\n\033[32mРезультаты сохранены в файл: {output_file}\033[0m")


async def get_history(chat_id, limit, text_only: False):
    """Получение истории сообщений из указанного чата и сохранение в текстовый файл."""
    async with app:  # Открываем клиент
        messages = []  # Список для накопления сообщений

        # Получаем информацию о чате
        chat = await app.get_chat(chat_id)
        chat_name = chat.title or chat.username or chat.first_name or f"Unknown_{chat_id}"

        # Генерация пути для сохранения файлов
        # Создаём папку output если её нет
        os.makedirs("output", exist_ok=True)

        # Создаём папку сессии если её нет
        session_folder = os.path.join("output", session_file)
        os.makedirs(session_folder, exist_ok=True)

        # Создаём папку для чата
        chat_folder = os.path.join(session_folder, f"chat_{chat_name}")
        os.makedirs(chat_folder, exist_ok=True)

        print("Собираю сообщения..")
        counter = 0

        # Сбор сообщений
        async for message in app.get_chat_history(chat_id, limit=limit):
            messages.append(message)
            counter += 1
            logging.info(f"Собрано: [{counter}/{limit}]")

        # Сохраняем до Х сообщения с конца
        # messages = messages[30000:]

        # Генерация имени текстового файла
        file_name = os.path.join(chat_folder, f"{chat_name}.txt".replace(" ", "_"))

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
                        file.write(
                            f"[FWD] {message.forward_from_chat.title or message.forward_from_chat.first_name or message.forward_from_chat.username} ")
                    else:
                        file.write("[FWD] Неизвестный источник ")

                if message.voice:
                    voice_file_name = os.path.join(
                        chat_folder,
                        f"V_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username if message.from_user else chat_name}_{message.voice.file_unique_id}.ogg"
                    )
                    if not text_only:
                        await message.download(file_name=voice_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: Голосовое сообщение сохранено как {voice_file_name}\n"
                    )
                elif message.photo:
                    photo_file_name = os.path.join(
                        chat_folder,
                        f"P_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username if message.from_user else chat_name}_{message.photo.file_unique_id}.jpg"
                    )
                    if not text_only:
                        await message.download(file_name=photo_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: Фото сохранено как {photo_file_name}\n"
                    )
                elif message.video_note:
                    note_file_name = os.path.join(
                        chat_folder,
                        f"VN_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username if message.from_user else chat_name}_{message.video_note.file_unique_id}.mp4"
                    )
                    if not text_only:
                        await message.download(file_name=note_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: Кружок сохранен как {note_file_name}\n"
                    )
                elif message.video:
                    video_file_name = os.path.join(
                        chat_folder,
                        f"VID_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username if message.from_user else chat_name}_{message.video.file_unique_id}.mp4"
                    )
                    if not text_only:
                        await message.download(file_name=video_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: Видео сохранено как {video_file_name}\n"
                    )
                elif message.sticker:
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: {'[Стикер]'}\n"
                    )
                elif message.document:
                    doc_file_name = os.path.join(
                        chat_folder,
                        f"DOC_{message.date.strftime("%d_%m_%Y_%H%M%S")}_{message.from_user.username if message.from_user else chat_name}.pdf"
                    )
                    if not text_only:
                        await message.download(file_name=doc_file_name)
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: Документ сохранен как {doc_file_name}\n"
                    )
                elif message.animation:
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: {'animation'}\n"
                    )
                elif message.audio:
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: {'audio'}\n"
                    )
                else:  # Обычный текст
                    file.write(
                        f"[{message.date}] {message.from_user.username if message.from_user else chat_name or 'Unknown'}: {message.text}\n"
                    )
                counter += 1
                if not counter == len(messages):
                    logging.info(f"Сохранено: [{counter}/{len(messages)}]")

        print(f"\n\033[32mСообщения сохранены в файл: {file_name}\033[0m")
        os.startfile(chat_folder)


# Функция для вывода участников чата
async def get_chat_members_list(chat_id, limit):
    """Выводит участников чата и сохраняет их список в файл."""
    async with app:
        try:
            # Получаем информацию о чате
            chat = await app.get_chat(chat_id)
            chat_name = chat.title or chat.username or f"Unknown_{chat_id}"

            # Создаём папку output если её нет
            os.makedirs("output", exist_ok=True)

            # Создаём папку сессии если её нет
            session_folder = os.path.join("output", session_file)
            os.makedirs(session_folder, exist_ok=True)

            # Генерируем имя файла
            file_name = os.path.join(session_folder, f"members_chat_{chat_name}.txt")

            print(f"Получение участников чата {chat_id}...")
            members = []

            async for member in app.get_chat_members(chat_id, limit=limit):
                members.append(member)

            # Сохраняем информацию в файл
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(f"Участники чата: {chat_name}\n")
                file.write(f"Всего участников: {len(members)}\n\n")

                for member in members:
                    user = member.user
                    member_info = f"ID: {user.id}, Имя: {user.first_name or 'Неизвестное'} {user.last_name or ''}, Username: {user.username or 'Неизвестное'}"
                    print(member_info)
                    file.write(member_info + "\n")  # Записываем в файл

            print(f"\n\033[32mСписок участников сохранен в файл: {file_name}\033[0m")

        except Exception as e:
            print(f"Ошибка при получении участников: {e}")


async def delete_chat_history(chat_id):
    async with app:
        try:
            # Вызов метода DeleteHistory
            result = await app.invoke(DeleteHistory(
                peer=await app.resolve_peer(chat_id),  # Преобразование ID чата в объект Peer
                just_clear=False,  # False означает, что удаляем сообщения для обеих сторон
                revoke=True,  # True для удаления сообщений у собеседника
                max_id=0  # Удаляем все сообщения до самого первого
            ))
            print(f"\n\033[37mИстория сообщений в чате {chat_id} удалена. Всего: {result.pts_count}\033[0m")
        except Exception as e:
            print(f"Ошибка при удалении истории сообщений: {e}")


app.run(main())
