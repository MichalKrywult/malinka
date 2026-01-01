import asyncio
import html
import logging
import os

import aiohttp

logger = logging.getLogger('discord_bot')

# Definiuje timeout jako obiekt
TELEG_TIMEOUT = aiohttp.ClientTimeout(total=5)

async def send_telegram_msg(text):
   
    text="Przypomnienie: \n" + text
    full_text = html.escape(text)
    token = os.getenv('TELEGRAM_API_TOKEN')
    chat_id = os.getenv('OWNER_TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": full_text,
        "parse_mode": "HTML"
    }

    try:
        async with aiohttp.ClientSession(timeout=TELEG_TIMEOUT) as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    # Pobiera tresc błedu
                    err_resp = await response.text()
                    logger.warning(f"Błąd Telegrama: {response.status} - {err_resp}")
                    print(f"Błąd Telegrama: {response.status} - {err_resp}")
    except asyncio.TimeoutError:
        logger.warning("Błąd Telegrama: Timeout (5s).")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd Telegrama: {e}")

async def send_system_alert(bot, message):
    """Pomocnicza funkcja do wysyłania powiadomień."""
    owner_id = os.getenv('OWNER_DISCORD_ID')
    if owner_id:
        user = bot.get_user(int(owner_id)) or await bot.fetch_user(int(owner_id))
        if user:
            try:
                await user.send(message)
                await send_telegram_msg(message)
            except Exception as e:
                print(f"Błąd wysyłania alertu: {e}")
