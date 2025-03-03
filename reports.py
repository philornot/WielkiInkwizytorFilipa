# reports.py
import datetime
import logging
import os
import traceback

import discord
import pytz

from bot_config import get_channel_id
from jira_client import get_completed_tasks_for_report
from discord_embeds import create_completed_tasks_report, create_error_embed

logger = logging.getLogger('WielkiInkwizytorFilipa')


async def generate_on_demand_report(period="day", custom_start=None, custom_end=None):
    """
    Generuje raport ukończonych zadań na żądanie.

    Args:
        period (str): Okres raportu: 'day', 'week', 'month', 'custom'
        custom_start (str, optional): Własna data początkowa w formacie YYYY-MM-DD
        custom_end (str, optional): Własna data końcowa w formacie YYYY-MM-DD

    Returns:
        discord.Embed: Embed z raportem
    """
    try:
        # Ustawienie strefy czasowej na Warsaw
        timezone_str = 'Europe/Warsaw'
        timezone = pytz.timezone(timezone_str)
        now = datetime.datetime.now(timezone)
        logger.info(f"Generowanie raportu na żądanie o {now.strftime('%Y-%m-%d %H:%M:%S %Z')} dla okresu {period}")

        # Obliczanie przedziału czasowego w zależności od wybranego okresu
        if period == "custom" and custom_start and custom_end:
            # Użyj własnego zakresu dat
            try:
                # Parsuj daty podane przez użytkownika
                start_time = datetime.datetime.strptime(custom_start, '%Y-%m-%d').replace(tzinfo=timezone)
                end_time = datetime.datetime.strptime(custom_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59,
                                                                                      tzinfo=timezone)

                # Formatowanie dat dla zapytania JQL
                start_date_time = custom_start + " 00:00"
                end_date_time = custom_end + " 23:59"
            except ValueError as date_error:
                logger.error(f"Błąd formatu daty: {date_error}")
                return create_error_embed(
                    "Błąd formatu daty",
                    "Podaj daty w formacie YYYY-MM-DD (np. 2023-12-31)"
                )
        elif period == "day":
            # Domyślny przedział (od 21:37 wczoraj do 21:36 dziś/jutro)
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
        elif period == "week":
            # Ostatnie 7 dni
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=0)
            start_time = (end_time - datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

            # Formatowanie dat dla zapytania JQL
            start_date_time = start_time.strftime('%Y-%m-%d %H:%M')
            end_date_time = end_time.strftime('%Y-%m-%d %H:%M')
        elif period == "month":
            # Ostatnie 30 dni
            end_time = now.replace(hour=23, minute=59, second=59, microsecond=0)
            start_time = (end_time - datetime.timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)

            # Formatowanie dat dla zapytania JQL
            start_date_time = start_time.strftime('%Y-%m-%d %H:%M')
            end_date_time = end_time.strftime('%Y-%m-%d %H:%M')
        else:
            # Nieznany okres, użyj domyślnego (dzień)
            logger.warning(f"Nieznany okres: {period}, używam domyślnego (dzień)")
            return await generate_on_demand_report()  # Wywołaj rekurencyjnie z domyślnymi parametrami

        logger.info(f"Pobieranie zadań ukończonych w okresie: {start_date_time} - {end_date_time}")
        logger.info(f"Używając strefy czasowej: {timezone_str}")

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
        bool: True, jeśli wysłanie się powiodło, False w przeciwnym razie
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

        # Ustaw strefę czasową na Warsaw
        timezone = pytz.timezone('Europe/Warsaw')
        now = datetime.datetime.now(timezone)
        logger.info(
            f"Generowanie dziennego raportu dla kanału {channel.name} (ID: {channel_id}) o {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # Generuj raport - domyślny okres "day"
        report_embed = await generate_on_demand_report()

        # Dodaj informację o automatycznym wygenerowaniu
        if isinstance(report_embed, discord.Embed):
            if report_embed.footer:
                current_footer = report_embed.footer.text
                new_footer = f"{current_footer} | Wygenerowano automatycznie"
                report_embed.set_footer(text=new_footer)
            else:
                report_embed.set_footer(text="Wygenerowano automatycznie")

        # Wysłij raport
        await channel.send(embed=report_embed)
        logger.info(f"Wysłano dzienny raport na kanał {channel.name}")

        # Sprawdź, czy mamy również tablicę wyników do wysłania
        try:
            from leaderboard import send_leaderboard_to_channel
            weekly_day = int(os.getenv('LEADERBOARD_WEEKLY_DAY', '1'))  # Domyślnie poniedziałek (0=pon, 6=niedz)

            # Jeśli dzisiaj jest dzień tygodnia ustawiony dla tablicy wyników, wyślij ją
            if now.weekday() == weekly_day:
                logger.info("Dzisiaj jest dzień wysyłania tygodniowej tablicy wyników")
                await send_leaderboard_to_channel(client, channel_id)

        except ImportError:
            logger.warning("Moduł leaderboard nie jest dostępny, pomijanie wysyłania tablicy wyników")
        except Exception as leaderboard_error:
            logger.error(f"Błąd podczas wysyłania tablicy wyników: {leaderboard_error}")
            logger.error(traceback.format_exc())

        return True
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania dziennego raportu: {e}")
        logger.error(traceback.format_exc())
        return False
