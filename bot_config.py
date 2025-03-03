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
UPDATE_INTERVAL = None


def setup_bot_and_config():
    """
    Inicjalizuje bota Discord i ustawia konfigurację.
    Zwraca: (discord.Client, app_commands.CommandTree)
    """
    try:
        global current_bugs_channel_id, current_reports_channel_id, UPDATE_INTERVAL

        # Konfiguracja Discord
        logger.info("Inicjalizacja konfiguracji bota Discord...")

        # Kanały
        BUGS_CHANNEL_ID = int(os.getenv('DISCORD_BUGS_CHANNEL_ID', '0'))
        REPORTS_CHANNEL_ID = int(os.getenv('DISCORD_REPORTS_CHANNEL_ID', '0'))
        current_bugs_channel_id = BUGS_CHANNEL_ID
        current_reports_channel_id = REPORTS_CHANNEL_ID

        # Interwał aktualizacji
        UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '300'))  # Interwał aktualizacji bugów w sekundach

        # Konfiguracja bota Discord
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)

        logger.info(
            f"Konfiguracja bota gotowa: Bugs channel: {current_bugs_channel_id}, Reports channel: {current_reports_channel_id}")
        logger.info(f"Interwał aktualizacji: {UPDATE_INTERVAL} sekund")

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
        channel_type (str): 'bugs' lub 'reports'

    Returns:
        int: ID kanału
    """
    if channel_type == 'bugs':
        return current_bugs_channel_id
    elif channel_type == 'reports':
        return current_reports_channel_id
    else:
        logger.error(f"Nieznany typ kanału: {channel_type}")
        return None


def set_channel_id(channel_type, channel_id):
    """
    Ustawia ID kanału na podstawie typu.

    Args:
        channel_type (str): 'bugs' lub 'reports'
        channel_id (int): Nowe ID kanału

    Returns:
        bool: True jeśli ustawiono pomyślnie
    """
    global current_bugs_channel_id, current_reports_channel_id, last_message_id

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
