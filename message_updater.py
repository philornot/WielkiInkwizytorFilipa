# message_updater.py
import datetime
import logging
import traceback

import discord
import pytz

from bot_config import get_channel_id, get_last_message_id, set_last_message_id
from discord_embeds import create_bugs_embeds
from jira_client import fetch_jira_bugs

logger = logging.getLogger('WielkiInkwizytorFilipa')


def get_warsaw_timestamp():
    """
    Zwraca aktualny timestamp w strefie czasowej Warszawy.

    Returns:
        str: Sformatowana data i czas w strefie czasowej Warszawy
    """
    timezone = pytz.timezone('Europe/Warsaw')
    now = datetime.datetime.now(timezone)
    return now.strftime('%d.%m.%Y %H:%M:%S')


async def clear_previous_bug_messages(client, channel):
    """
    Czyści poprzednie wiadomości z bugami wysłane przez bota na danym kanale.

    Args:
        client (discord.Client): Klient Discord
        channel (discord.TextChannel): Kanał Discord do wyczyszczenia

    Returns:
        int: Liczba usuniętych wiadomości
    """
    try:
        logger.info(f"Czyszczenie poprzednich wiadomości z bugami na kanale {channel.name}")

        # W nowszych wersjach Discord.py (2.0+) history() zwraca asynchroniczny iterator
        bot_id = client.user.id
        deleted_count = 0

        # Iteracja przez asynchroniczny iterator historii (limit 30 wiadomości)
        async for message in channel.history(limit=30):
            # Sprawdź, czy wiadomość jest od tego bota
            if message.author.id == bot_id:
                # Sprawdź, czy wiadomość zawiera embedy, które wyglądają jak listy bugów
                for embed in message.embeds:
                    if embed.title and ("Aktualna lista bugów" in embed.title):
                        logger.info(f"Usuwanie starej wiadomości z bugami (ID: {message.id})")
                        await message.delete()
                        deleted_count += 1
                        break  # Przerwij po usunięciu, aby uniknąć sprawdzania innych embedów

        logger.info(f"Usunięto {deleted_count} starych wiadomości z bugami")
        return deleted_count

    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia starych wiadomości: {e}")
        logger.error(traceback.format_exc())
        return 0


async def update_bugs_message(client):
    """
    Aktualizuje wiadomość z bugami na odpowiednim kanale.

    Args:
        client (discord.Client): Klient Discord

    Returns:
        bool: True, jeśli aktualizacja się powiodła, False w przeciwnym razie
    """
    try:
        channel_id = get_channel_id('bugs')
        if not channel_id:
            logger.error("Nie ustawiono ID kanału bugów")
            return False

        channel = client.get_channel(channel_id)
        if not channel:
            logger.error(f"Nie można znaleźć kanału bugów o ID {channel_id}")
            return False

        # Pobieranie bugów
        logger.info(f"Pobieranie bugów z Jiry dla kanału {channel.name} (ID: {channel_id})")
        issues = await fetch_jira_bugs()
        embeds = create_bugs_embeds(issues)

        last_message_id = get_last_message_id()

        if last_message_id:
            # Próba pobrania i edycji istniejącej wiadomości
            try:
                message = await channel.fetch_message(last_message_id)
                logger.info(f"Znaleziono istniejącą wiadomość z bugami (ID: {last_message_id})")

                # Discord pozwala tylko na jeden embed na aktualizację wiadomości,
                # więc usuwamy starą wiadomość i wysyłamy nową, jeśli mamy wiele embedów
                if len(embeds) > 1:
                    logger.info("Wykryto wiele embedów, usuwanie starej wiadomości i wysyłanie nowych")
                    try:
                        await message.delete()
                        logger.info(f"Usunięto starą wiadomość (ID: {last_message_id})")
                    except Exception as delete_error:
                        logger.warning(f"Nie można usunąć starej wiadomości: {delete_error}")

                    # Wysyłanie nowych wiadomości
                    new_message_id = None
                    for i, embed in enumerate(embeds):
                        new_message = await channel.send(embed=embed)
                        if i == len(embeds) - 1:  # zapisujemy ID tylko ostatniej wiadomości
                            new_message_id = new_message.id

                    set_last_message_id(new_message_id)
                    logger.info(f"Wysłano {len(embeds)} nowych wiadomości z bugami, ID ostatniej: {new_message_id}")
                else:
                    # Jeśli jest tylko jeden embed, po prostu aktualizujemy wiadomość
                    await message.edit(embed=embeds[0])
                    logger.info(
                        f"Zaktualizowano istniejącą wiadomość z bugami (ID: {last_message_id}) o {get_warsaw_timestamp()}")

            except discord.NotFound:
                logger.warning(f"Wiadomość o ID {last_message_id} nie została znaleziona, wysyłanie nowej")

                # Wyczyść poprzednie wiadomości z bugami przed wysłaniem nowych
                await clear_previous_bug_messages(client, channel)

                # Wysyłanie nowych wiadomości
                new_message_id = None
                for i, embed in enumerate(embeds):
                    new_message = await channel.send(embed=embed)
                    if i == len(embeds) - 1:  # zapisujemy ID tylko ostatniej wiadomości
                        new_message_id = new_message.id

                set_last_message_id(new_message_id)
                logger.info(f"Wysłano {len(embeds)} nowych wiadomości z bugami, ID ostatniej: {new_message_id}")

            except Exception as e:
                logger.error(f"Nieoczekiwany błąd podczas aktualizacji wiadomości: {e}")
                logger.error(traceback.format_exc())
                # W przypadku błędu aktualizacji próbujemy wysłać nową wiadomość
                try:
                    logger.info("Próba wysłania nowej wiadomości po błędzie aktualizacji")

                    # Wyczyść poprzednie wiadomości z bugami przed wysłaniem nowych
                    await clear_previous_bug_messages(client, channel)

                    new_message_id = None
                    for i, embed in enumerate(embeds):
                        new_message = await channel.send(embed=embed)
                        if i == len(embeds) - 1:
                            new_message_id = new_message.id

                    set_last_message_id(new_message_id)
                    logger.info(
                        f"Wysłano {len(embeds)} nowych wiadomości z bugami po błędzie, ID ostatniej: {new_message_id}")
                except Exception as new_error:
                    logger.error(f"Nie można wysłać nowej wiadomości po błędzie: {new_error}")
                    logger.error(traceback.format_exc())
                    return False
        else:
            # Brak poprzedniej wiadomości (np. po restarcie bota)
            logger.info("Brak poprzedniej wiadomości, czyszczenie starych wiadomości z bugami")

            # Wyczyść poprzednie wiadomości z bugami przed wysłaniem nowych
            await clear_previous_bug_messages(client, channel)

            # Wysyłanie nowych wiadomości
            new_message_id = None
            for i, embed in enumerate(embeds):
                new_message = await channel.send(embed=embed)
                if i == len(embeds) - 1:  # zapisujemy ID tylko ostatniej wiadomości
                    new_message_id = new_message.id

            set_last_message_id(new_message_id)
            logger.info(f"Wysłano {len(embeds)} nowych wiadomości z bugami, ID ostatniej: {new_message_id}")

        return True
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji wiadomości z bugami: {e}")
        logger.error(traceback.format_exc())
        return False
