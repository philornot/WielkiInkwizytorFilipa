# reports.py
import datetime
import logging
import os
import traceback

import pytz

from bot_config import get_channel_id
from jira_client import get_completed_tasks_for_report
from discord_embeds import create_completed_tasks_report, create_error_embed

logger = logging.getLogger('jira-discord-bot')


async def generate_on_demand_report():
    """
    Generuje raport ukończonych zadań na żądanie.

    Returns:
        discord.Embed: Embed z raportem
    """
    try:
        # Ustawienie strefy czasowej
        timezone_str = os.getenv('TIMEZONE', 'Europe/Warsaw')
        timezone = pytz.timezone(timezone_str)
        now = datetime.datetime.now(timezone)
        logger.info(f"Generowanie raportu na żądanie o {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # Obliczanie przedziału czasowego (od 21:37 wczoraj do 21:36 dziś)
        end_time = now.replace(hour=21, minute=36, second=0, microsecond=0)
        if now.hour < 21 or (now.hour == 21 and now.minute < 37):
            # Jeśli raport generowany jest przed 21:37, to kończymy o 21:36 dzisiaj
            end_date = end_time.strftime('%Y-%m-%d')
        else:
            # Jeśli raport generowany jest po 21:37, to kończymy o 21:36 jutro
            end_time = end_time + datetime.timedelta(days=1)
            end_date = end_time.strftime('%Y-%m-%d')

        # Czas początkowy zawsze jest o 21:37 dzień wcześniej
        start_time = end_time.replace(hour=21, minute=37) - datetime.timedelta(days=1)
        start_date = start_time.strftime('%Y-%m-%d')

        # Formatowanie dat dla zapytania JQL
        start_date_time = f"{start_date} 21:37"
        end_date_time = f"{end_date} 21:36"

        logger.info(f"Pobieranie zadań ukończonych w okresie: {start_date_time} - {end_date_time}")

        # Pobieranie zadań z Jiry
        tasks = await get_completed_tasks_for_report(start_date_time, end_date_time)

        # Tworzenie embeda z raportem
        jira_server = os.getenv('JIRA_SERVER')
        embed = create_completed_tasks_report(tasks, start_time, end_time, jira_server)
        logger.info(f"Wygenerowano raport z {len(tasks)} zadaniami")

        return embed
    except Exception as e:
        logger.error(f"Błąd podczas generowania raportu na żądanie: {e}")
        logger.error(traceback.format_exc())
        return create_error_embed(
            "Błąd raportu",
            f"Wystąpił błąd podczas generowania raportu: {str(e)}"
        )


async def send_daily_report(client):
    """
    Wysyła dzienny raport na skonfigurowany kanał Discord.

    Args:
        client (discord.Client): Klient Discord

    Returns:
        bool: True jeśli wysłanie się powiodło, False w przeciwnym razie
    """
    try:
        # Pobierz kanał raportów
        channel_id = get_channel_id('reports')
        if not channel_id:
            logger.error("Nie ustawiono ID kanału raportów")
            return False

        channel = client.get_channel(channel_id)
        if not channel:
            logger.error(f"Nie można znaleźć kanału raportów o ID {channel_id}")
            return False

        # Generuj raport
        logger.info(f"Generowanie dziennego raportu dla kanału {channel.name} (ID: {channel_id})")
        report_embed = await generate_on_demand_report()

        # Wysłij raport
        await channel.send(embed=report_embed)
        logger.info(f"Wysłano dzienny raport na kanał {channel.name}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania dziennego raportu: {e}")
        logger.error(traceback.format_exc())
        return False