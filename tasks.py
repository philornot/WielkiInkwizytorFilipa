# tasks.py
import asyncio
import datetime
import logging
import os
import traceback

import pytz

from bot_config import get_update_interval
from message_updater import update_bugs_message
from reports import send_daily_report

logger = logging.getLogger('jira-discord-bot')


async def bugs_update_loop(client):
    """
    Pętla okresowo aktualizująca informacje o bugach.

    Args:
        client (discord.Client): Klient Discord
    """
    try:
        # Czekaj, aż klient Discord będzie gotowy
        await client.wait_until_ready()
        logger.info("Rozpoczęto pętlę aktualizacji bugów")

        failures_count = 0
        MAX_FAILURES = 5

        while not client.is_closed():
            try:
                # Pobierz aktualny interwał (może zmienić się w trakcie działania)
                update_interval = get_update_interval()

                # Aktualizacja wiadomości z bugami
                success = await update_bugs_message(client)

                if success:
                    # Resetuj licznik błędów po udanej aktualizacji
                    failures_count = 0
                    logger.info(f"Aktualizacja bugów zakończona pomyślnie. Następna za {update_interval} sekund.")
                else:
                    # Zwiększ licznik błędów
                    failures_count += 1
                    logger.warning(f"Aktualizacja bugów nie powiodła się (błąd {failures_count}/{MAX_FAILURES})")

                    # Jeśli przekroczyliśmy limit błędów, zwiększ interwał
                    if failures_count >= MAX_FAILURES:
                        longer_interval = min(update_interval * 2, 3600)  # max 1 godzina
                        logger.warning(
                            f"Zbyt wiele błędów, tymczasowe zwiększenie interwału do {longer_interval} sekund")
                        await asyncio.sleep(longer_interval)
                        continue

                # Czekaj do następnej aktualizacji
                await asyncio.sleep(update_interval)

            except asyncio.CancelledError:
                logger.info("Pętla aktualizacji bugów została anulowana")
                break
            except Exception as e:
                failures_count += 1
                logger.error(f"Błąd w pętli aktualizacji bugów: {e}")
                logger.error(traceback.format_exc())
                # Po błędzie czekaj krócej przed następną próbą
                retry_interval = min(60 * failures_count, 600)  # max 10 minut
                logger.info(f"Ponowna próba aktualizacji za {retry_interval} sekund")
                await asyncio.sleep(retry_interval)
    except Exception as e:
        logger.critical(f"Krytyczny błąd w pętli aktualizacji bugów: {e}")
        logger.critical(traceback.format_exc())


async def schedule_daily_report(client):
    """
    Planuje wysyłanie dziennych raportów.

    Args:
        client (discord.Client): Klient Discord
    """
    try:
        # Czekaj, aż klient Discord będzie gotowy
        await client.wait_until_ready()
        logger.info("Rozpoczęto planowanie dziennych raportów")

        # Pobierz strefę czasową z konfiguracji
        timezone_str = os.getenv('TIMEZONE', 'Europe/Warsaw')
        timezone = pytz.timezone(timezone_str)
        logger.info(f"Używanie strefy czasowej: {timezone_str}")

        # Godzina i minuta raportu - domyślnie 21:37
        report_hour = int(os.getenv('REPORT_HOUR', '21'))
        report_minute = int(os.getenv('REPORT_MINUTE', '37'))
        logger.info(f"Raporty zaplanowane na godzinę {report_hour}:{report_minute:02d}")

        failures_count = 0

        while not client.is_closed():
            try:
                # Pobierz aktualny czas w skonfigurowanej strefie czasowej
                now = datetime.datetime.now(timezone)

                # Oblicz czas następnego raportu
                next_report = now.replace(hour=report_hour, minute=report_minute, second=0, microsecond=0)

                # Jeśli czas już minął dzisiaj, zaplanuj na jutro
                if next_report <= now:
                    next_report += datetime.timedelta(days=1)

                # Oblicz czas oczekiwania
                wait_time = (next_report - now).total_seconds()
                logger.info(f"Następny raport zaplanowano na {next_report}, oczekiwanie {wait_time} sekund")

                # Czekaj do czasu następnego raportu
                await asyncio.sleep(wait_time)

                # Wyślij raport
                await send_daily_report(client)
                # Po udanym wysłaniu raportu resetuj licznik błędów
                failures_count = 0

            except asyncio.CancelledError:
                logger.info("Planowanie raportów zostało anulowane")
                break
            except Exception as e:
                failures_count += 1
                logger.error(f"Błąd w planowaniu raportu: {e}")
                logger.error(traceback.format_exc())
                # Poczekaj minutę przed ponowną próbą w przypadku błędu
                retry_time = min(60 * failures_count, 900)  # max 15 minut
                logger.info(f"Ponowna próba planowania za {retry_time} sekund")
                await asyncio.sleep(retry_time)
    except Exception as e:
        logger.critical(f"Krytyczny błąd w planowaniu raportów: {e}")
        logger.critical(traceback.format_exc())