import html
import logging
import os

import discord

logger = logging.getLogger('discord_bot')

async def send_telegram_msg(bot,message):
    #embed czy tekst
    if isinstance(message, discord.Embed):
        title = f"<b>{html.escape(message.title or '')}</b>"
        desc = html.escape(message.description or "")
        telegram_text = f"{title}\n{desc}"
        if telegram_text:
            for field in message.fields:
                if field.name and field.value:
                    telegram_text += f"\n<b>{html.escape(field.name)}</b>: {html.escape(field.value)}"
    else:
        telegram_text = f"<b>Przypomnienie:</b>\n{html.escape(str(message))}"



    token = os.getenv('TELEGRAM_API_TOKEN')
    chat_id = os.getenv('OWNER_TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": telegram_text,
        "parse_mode": "HTML"
    }

    try:
        async with bot.session.post(url, json=payload, timeout=5) as response:
            if response.status != 200:
                logger.warning(f"Błąd Telegrama: {response.status}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

async def send_system_alert(bot, message):
    """Pomocnicza funkcja do wysyłania powiadomień (tekst lub embed)."""
    owner_id = os.getenv('OWNER_DISCORD_ID')
    if not owner_id:
        return

    user = bot.get_user(int(owner_id)) or await bot.fetch_user(int(owner_id))
    if user:
        try:
            if isinstance(message, discord.Embed):
                await user.send(embed=message)
                #embed nie dziala dla telegrama ---- TO FIX LATER
                await send_telegram_msg(bot,message)
            else:
                await user.send(message)
                await send_telegram_msg(bot,message)
                
        except Exception as e:
            print(f"Błąd wysyłania alertu: {e}")