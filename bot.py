import os
import asyncio
import random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv
from telegram import Bot

from parser import check_availability


def within_working_window(now: datetime) -> bool:
    hour = now.hour
    return 7 <= hour <= 23 or 0 <= hour <= 1


async def safe_send_message(bot, chat_id: int, text: str):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print(f"Не удалось отправить сообщение: {e}")


def get_next_random_time_in_hour(from_time: datetime) -> datetime:
    """Возвращает случайное время в ПОЛНОМ СЛЕДУЮЩЕМ часе (не текущем!)."""
    next_hour_start = (from_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    random_minutes = random.randint(0, 59)
    random_seconds = random.randint(0, 59)
    return next_hour_start.replace(minute=random_minutes, second=random_seconds)


async def main() -> None:
    load_dotenv()

    username = os.getenv("SPMI_USERNAME")
    password = os.getenv("SPMI_PASSWORD")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    user_ids = list(map(int,os.getenv("TELEGRAM_USER_IDS").split(",")))

    if not all([username, password, bot_token, user_ids]):
        missing = [
            name for name, val in [
                ("SPMI_USERNAME", username),
                ("SPMI_PASSWORD", password),
                ("TELEGRAM_BOT_TOKEN", bot_token),
                ("TELEGRAM_USER_ID", user_ids),
            ] if not val
        ]
        raise RuntimeError(f"Missing required .env variables: {', '.join(missing)}")

    bot = Bot(token=bot_token)
    session = requests.Session()
    loop = asyncio.get_running_loop()

    # Инициализируем следующее случайное время
    next_run = get_next_random_time_in_hour(datetime.now())

    while True:
        now = datetime.now()
        if now >= next_run:
            if within_working_window(now):
                try:
                    is_available = await loop.run_in_executor(
                        None,
                        check_availability,
                        username,
                        password,
                        session
                    )
                except Exception as e:
                    for user_id in user_ids:
                        await safe_send_message(bot, user_id, f"Ошибка проверки: {e}")
                else:
                    for user_id in user_ids:
                        status_text = "Есть свободные записи" if is_available else "Свободных записей нет"
                        await safe_send_message(bot, user_id, status_text)

            # Планируем следующий запуск — случайное время в следующем часе
            next_run = get_next_random_time_in_hour(now)

        # Спим до следующего запланированного времени
        now = datetime.now()
        sleep_seconds = (next_run - now).total_seconds()
        if sleep_seconds <= 0:
            sleep_seconds = 1  # маленькая пауза, чтобы избежать busy-wait
        await asyncio.sleep(sleep_seconds)


if __name__ == "__main__":
    asyncio.run(main())