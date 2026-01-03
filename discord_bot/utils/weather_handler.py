import datetime
import json
import logging
import os
import sqlite3
from urllib.parse import quote

import discord
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger('discord_bot')

def get_weather_chart_url(db_path):
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT temperature, hour FROM weather 
            ORDER BY date DESC, hour DESC LIMIT 12
        """)
        rows = cursor.fetchall()[::-1] # odwrocenie zeby było chronologicznie 

    if not rows:
        return None

    temps = [row[0] for row in rows]
    labels = [f"{row[1]}:00" for row in rows]

    # Konfiguracja wykresu dla QuickChart (Chart.js)
    chart_config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Temperatura (°C)",
                "data": temps,
                "fill": True,
                "backgroundColor": "rgba(54, 162, 235, 0.2)",
                "borderColor": "rgb(54, 162, 235)",
                "tension": 0.4
            }]
        },
        "options": {
            "title": {"display": True, "text": "Trend temperatury"}
        }
    }

    encoded_config = quote(json.dumps(chart_config))
    return f"https://quickchart.io/chart?c={encoded_config}"

async def fetch_and_save_weather(db_path, session):
    url = os.getenv("WEATHER_API") #https://danepubliczne.imgw.pl/api/data/synop/id/XxX
    if not url:
        return

    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            data = await response.json()

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO weather (station,date, hour, temperature, wind, rainfall)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    data.get('stacja', 'Nieznana'),
                    data.get('data_pomiaru', "0"),
                    int(data.get('godzina_pomiaru', 0)),
                    float(data.get('temperatura', 0)),
                    float(data.get('predkosc_wiatru', 0)),
                    float(data.get('suma_opadu', 0))
                ))
                conn.commit()
            logger.info("Pogoda zaktualizowana.")
    except Exception as e:
        logger.error(f"Błąd podczas pobierania/zapisu pogody: {e}")

async def get_latest_weather_from_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM weather
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)

def create_weather_embed(data):
    if not data:
        return discord.Embed(title="Błąd", description="Brak danych pogodowych.", color=discord.Color.red())

    embed = discord.Embed(
        title=f"Pogoda dla: {data.get('station', 'Nieznana stacja')}",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="Temperatura", value=f"{data['temperature']}°C", inline=True)
    embed.add_field(name="Wiatr", value=f"{data['wind']} km/h", inline=True)
    embed.add_field(name="Opady", value=f"{data['rainfall']} mm", inline=True)
    embed.set_footer(text=f"Pomiar z godziny: {data['hour']}:00")
    
    return embed
