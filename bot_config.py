# bot_config.py
import logging
import os
import traceback

import discord
from discord import app_commands

logger = logging.getLogger('WielkiInkwizytorFilipa')

# Zmienne globalne
last_message_id = None
current_bugs_channel_id = None
current_reports_channel_id = None
current_leaderboard_channel_id = None
UPDATE_INTERVAL = None

# Nowe zmienne do śledzenia stanu
REPORTS_ENABLED = True
LEADERBOARD_ENABLED = True

# Konfiguracja czasu
REPORT_HOUR = 21
REPORT_MINUTE = 36
LEADERBOARD_HOUR = 9
LEADERBOARD_MINUTE = 0
LEADERBOARD_DAY = 0  # Poniedziałek


def setup_bot_and_config():
    """
    Inicjalizuje bota Discord i ustawia konfigurację.
    Zwraca: (discord.Client, app_commands.CommandTree)
    """
    try:
        global current_bugs_channel_id, current_reports_channel_id, current_leaderboard_channel_id
        global UPDATE_INTERVAL, REPORTS_ENABLED, LEADERBOARD_ENABLED
        global REPORT_HOUR, REPORT_MINUTE, LEADERBOARD_HOUR, LEADERBOARD_MINUTE, LEADERBOARD_DAY

        # Konfiguracja Discord
        logger.info("Inicjalizacja konfiguracji bota Discord...")

        # Kanały
        BUGS_CHANNEL_ID = int(os.getenv('DISCORD_BUGS_CHANNEL_ID', '0'))
        REPORTS_CHANNEL_ID = int(os.getenv('DISCORD_REPORTS_CHANNEL_ID', '0'))
        LEADERBOARD_CHANNEL_ID = int(os.getenv('DISCORD_LEADERBOARD_CHANNEL_ID', '0'))

        current_bugs_channel_id = BUGS_CHANNEL_ID
        current_reports_channel_id = REPORTS_CHANNEL_ID
        current_leaderboard_channel_id = LEADERBOARD_CHANNEL_ID if LEADERBOARD_CHANNEL_ID != 0 else REPORTS_CHANNEL_ID

        # Interwał aktualizacji
        UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '300'))  # Interwał aktualizacji bugów w sekundach

        # Konfiguracja raportów i leaderboardu
        REPORTS_ENABLED = os.getenv('REPORTS_ENABLED', 'true').lower() == 'true'
        LEADERBOARD_ENABLED = os.getenv('LEADERBOARD_ENABLED', 'true').lower() == 'true'

        # Czasy raportów
        REPORT_HOUR = int(os.getenv('REPORT_HOUR', '21'))
        REPORT_MINUTE = int(os.getenv('REPORT_MINUTE', '36'))

        # Czasy leaderboardu
        LEADERBOARD_HOUR = int(os.getenv('LEADERBOARD_HOUR', '9'))
        LEADERBOARD_MINUTE = int(os.getenv('LEADERBOARD_MINUTE', '0'))
        LEADERBOARD_DAY = int(os.getenv('LEADERBOARD_WEEKLY_DAY', '0'))

        # Konfiguracja bota Discord
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)

        logger.info(
            f"Konfiguracja bota gotowa: Bugs channel: {current_bugs_channel_id}, Reports channel: {current_reports_channel_id}, Leaderboard channel: {current_leaderboard_channel_id}")
        logger.info(f"Interwał aktualizacji: {UPDATE_INTERVAL} sekund")
        logger.info(
            f"Raporty: {'włączone' if REPORTS_ENABLED else 'wyłączone'}, czas: {REPORT_HOUR}:{REPORT_MINUTE:02d}")
        logger.info(
            f"Leaderboard: {'włączone' if LEADERBOARD_ENABLED else 'wyłączone'}, dzień: {LEADERBOARD_DAY} (0=pon), czas: {LEADERBOARD_HOUR}:{LEADERBOARD_MINUTE:02d}")

        return client, tree

    except Exception as e:
        logger.error(f"Błąd podczas konfiguracji bota: {e}")
        logger.error(traceback.format_exc())
        # W przypadku błędu tworzymy minimalną konfigurację, żeby bot mógł się uruchomić
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)
        return client, tree


def get_channel_id(channel_type):
    """
    Pobiera aktualne ID kanału na podstawie typu.

    Args:
        channel_type (str): 'bugs', 'reports' lub 'leaderboard'

    Returns:
        int: ID kanału
    """
    if channel_type == 'bugs':
        return current_bugs_channel_id
    elif channel_type == 'reports':
        return current_reports_channel_id
    elif channel_type == 'leaderboard':
        return current_leaderboard_channel_id or current_reports_channel_id  # Fallback do kanału raportów
    else:
        logger.error(f"Nieznany typ kanału: {channel_type}")
        return None


def set_channel_id(channel_type, channel_id):
    """
    Ustawia ID kanału na podstawie typu.

    Args:
        channel_type (str): 'bugs', 'reports' lub 'leaderboard'
        channel_id (int): Nowe ID kanału

    Returns:
        bool: True jeśli ustawiono pomyślnie
    """
    global current_bugs_channel_id, current_reports_channel_id, current_leaderboard_channel_id, last_message_id

    try:
        if channel_type == 'bugs':
            current_bugs_channel_id = channel_id
            last_message_id = None  # Reset ID wiadomości po zmianie kanału
            os.environ['DISCORD_BUGS_CHANNEL_ID'] = str(channel_id)
            return True
        elif channel_type == 'reports':
            current_reports_channel_id = channel_id
            os.environ['DISCORD_REPORTS_CHANNEL_ID'] = str(channel_id)
            return True
        elif channel_type == 'leaderboard':
            current_leaderboard_channel_id = channel_id
            os.environ['DISCORD_LEADERBOARD_CHANNEL_ID'] = str(channel_id)
            return True
        else:
            logger.error(f"Nieznany typ kanału: {channel_type}")
            return False
    except Exception as e:
        logger.error(f"Błąd podczas ustawiania ID kanału: {e}")
        logger.error(traceback.format_exc())
        return False


def get_last_message_id():
    """Pobiera ID ostatniej wysłanej wiadomości z bugami"""
    return last_message_id


def set_last_message_id(message_id):
    """Ustawia ID ostatniej wysłanej wiadomości z bugami"""
    global last_message_id
    last_message_id = message_id


def get_update_interval():
    """Pobiera interwał aktualizacji bugów w sekundach"""
    return UPDATE_INTERVAL


def set_update_interval(seconds):
    """Ustawia interwał aktualizacji bugów w sekundach"""
    global UPDATE_INTERVAL
    try:
        UPDATE_INTERVAL = seconds
        os.environ['UPDATE_INTERVAL'] = str(seconds)
        logger.info(f"Ustawiono nowy interwał aktualizacji: {seconds} sekund")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas ustawiania interwału aktualizacji: {e}")
        logger.error(traceback.format_exc())
        return False


# Nowe funkcje do zarządzania stanem bota

def is_reports_enabled():
    """Zwraca czy raporty są włączone"""
    return REPORTS_ENABLED


def set_reports_enabled(enabled):
    """Włącza lub wyłącza raporty"""
    global REPORTS_ENABLED
    try:
        REPORTS_ENABLED = enabled
        os.environ['REPORTS_ENABLED'] = str(enabled).lower()
        logger.info(f"Raporty zostały {'włączone' if enabled else 'wyłączone'}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas {'włączania' if enabled else 'wyłączania'} raportów: {e}")
        logger.error(traceback.format_exc())
        return False


def is_leaderboard_enabled():
    """Zwraca czy tablica wyników jest włączona"""
    return LEADERBOARD_ENABLED


def set_leaderboard_enabled(enabled):
    """Włącza lub wyłącza tablicę wyników"""
    global LEADERBOARD_ENABLED
    try:
        LEADERBOARD_ENABLED = enabled
        os.environ['LEADERBOARD_ENABLED'] = str(enabled).lower()
        logger.info(f"Tablica wyników została {'włączona' if enabled else 'wyłączona'}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas {'włączania' if enabled else 'wyłączania'} tablicy wyników: {e}")
        logger.error(traceback.format_exc())
        return False


def set_report_time(hour, minute):
    """Ustawia czas wysyłania raportu"""
    global REPORT_HOUR, REPORT_MINUTE
    try:
        # Walidacja
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            logger.error(f"Nieprawidłowy czas raportu: {hour}:{minute}")
            return False

        REPORT_HOUR = hour
        REPORT_MINUTE = minute
        os.environ['REPORT_HOUR'] = str(hour)
        os.environ['REPORT_MINUTE'] = str(minute)
        logger.info(f"Ustawiono czas raportu na {hour}:{minute:02d}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas ustawiania czasu raportu: {e}")
        logger.error(traceback.format_exc())
        return False


def get_report_time():
    """Zwraca czas wysyłania raportu"""
    return REPORT_HOUR, REPORT_MINUTE


def set_leaderboard_time(day, hour, minute):
    """Ustawia dzień i czas wysyłania tablicy wyników"""
    global LEADERBOARD_DAY, LEADERBOARD_HOUR, LEADERBOARD_MINUTE
    try:
        # Walidacja
        if day < 0 or day > 6 or hour < 0 or hour > 23 or minute < 0 or minute > 59:
            logger.error(f"Nieprawidłowy czas tablicy wyników: dzień {day}, {hour}:{minute}")
            return False

        LEADERBOARD_DAY = day
        LEADERBOARD_HOUR = hour
        LEADERBOARD_MINUTE = minute
        os.environ['LEADERBOARD_WEEKLY_DAY'] = str(day)
        os.environ['LEADERBOARD_HOUR'] = str(hour)
        os.environ['LEADERBOARD_MINUTE'] = str(minute)
        logger.info(f"Ustawiono czas tablicy wyników na dzień {day} (0=pon), godzina {hour}:{minute:02d}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas ustawiania czasu tablicy wyników: {e}")
        logger.error(traceback.format_exc())
        return False


def get_leaderboard_time():
    """Zwraca dzień i czas wysyłania tablicy wyników"""
    return LEADERBOARD_DAY, LEADERBOARD_HOUR, LEADERBOARD_MINUTE


def get_bot_status():
    """
    Zwraca słownik ze szczegółowym stanem bota
    """
    try:
        status = {
            "bugs_channel_id": current_bugs_channel_id,
            "reports_channel_id": current_reports_channel_id,
            "leaderboard_channel_id": current_leaderboard_channel_id,
            "update_interval": UPDATE_INTERVAL,
            "reports_enabled": REPORTS_ENABLED,
            "leaderboard_enabled": LEADERBOARD_ENABLED,
            "report_time": f"{REPORT_HOUR}:{REPORT_MINUTE:02d}",
            "leaderboard_time": f"Dzień {LEADERBOARD_DAY} (0=pon), {LEADERBOARD_HOUR}:{LEADERBOARD_MINUTE:02d}",
            "jira_server": os.getenv('JIRA_SERVER', 'Nie skonfigurowano'),
            "jira_project": os.getenv('JIRA_PROJECT', 'Nie skonfigurowano'),
            "timezone": os.getenv('TIMEZONE', 'Europe/Warsaw')
        }
        return status
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statusu bota: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Wystąpił błąd: {str(e)}"}
