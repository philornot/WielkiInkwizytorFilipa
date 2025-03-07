# tasks.py
import asyncio
import datetime
import logging
import traceback

import pytz

from bot_config import (
    get_update_interval, is_reports_enabled, is_leaderboard_enabled,
    get_report_time, get_leaderboard_time
)
from message_updater import update_bugs_message
from reports import send_daily_report

logger = logging.getLogger('WielkiInkwizytorFilipa')


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
    Planuje wysyłanie dziennych raportów z poprawną obsługą strefy czasowej.

    Args:
        client (discord.Client): Klient Discord
    """
    try:
        # Czekaj, aż klient Discord będzie gotowy
        await client.wait_until_ready()
        logger.info("Rozpoczęto planowanie dziennych raportów")

        # Pobierz strefę czasową z konfiguracji - zawsze używamy Warsaw
        timezone_str = 'Europe/Warsaw'
        timezone = pytz.timezone(timezone_str)
        logger.info(f"Używanie strefy czasowej: {timezone_str} dla raportów")

        failures_count = 0

        while not client.is_closed():
            try:
                # Sprawdź czy raporty są włączone
                if not is_reports_enabled():
                    logger.info("Raporty są wyłączone. Sprawdzam ponownie za 5 minut...")
                    await asyncio.sleep(300)  # Sprawdź ponownie za 5 minut
                    continue

                # Godzina i minuta raportu - pobierz aktualne ustawienia
                report_hour, report_minute = get_report_time()

                # Pobierz aktualny czas w strefie czasowej Warszawy
                warsaw_now = datetime.datetime.now(timezone)
                logger.info(f"Aktualny czas warszawski: {warsaw_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

                # Oblicz czas następnego raportu
                next_report = warsaw_now.replace(hour=report_hour, minute=report_minute, second=0, microsecond=0)

                # Jeśli czas już minął dzisiaj, zaplanuj na jutro
                if next_report <= warsaw_now:
                    next_report += datetime.timedelta(days=1)

                # Oblicz czas oczekiwania
                wait_time = (next_report - warsaw_now).total_seconds()
                next_report_str = next_report.strftime('%Y-%m-%d %H:%M:%S %Z')
                logger.info(f"Następny raport zaplanowano na {next_report_str}, oczekiwanie {wait_time} sekund")

                # Czekaj do czasu następnego raportu
                await asyncio.sleep(wait_time)

                # Sprawdź ponownie, czy raporty są nadal włączone
                if not is_reports_enabled():
                    logger.info("Raporty zostały wyłączone w trakcie oczekiwania. Pomijam wysyłanie raportu.")
                    continue

                # Dla pewności sprawdź jeszcze raz aktualny czas przed wysłaniem
                current_time = datetime.datetime.now(timezone)
                logger.info(f"Czas przed wysłaniem raportu: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

                # Wyślij raport
                logger.info("Rozpoczęto wysyłanie codziennego raportu...")
                success = await send_daily_report(client)

                if success:
                    logger.info("Codzienny raport wysłany pomyślnie")
                    # Po udanym wysłaniu raportu resetuj licznik błędów
                    failures_count = 0
                else:
                    logger.error("Nie udało się wysłać codziennego raportu")
                    failures_count += 1

                # Nawet jeśli wystąpił błąd, poczekaj co najmniej 1 minutę przed próbą ponownego uruchomienia pętli
                # To zapobiega zapętleniu w przypadku stałego błędu
                await asyncio.sleep(60)

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


async def schedule_weekly_leaderboard(client):
    """
    Planuje wysyłanie tygodniowej tablicy wyników.

    Args:
        client (discord.Client): Klient Discord
    """
    try:
        # Czekaj, aż klient Discord będzie gotowy
        await client.wait_until_ready()
        logger.info("Rozpoczęto planowanie tygodniowej tablicy wyników")

        # Pobierz strefę czasową - zawsze Warsaw
        timezone_str = 'Europe/Warsaw'
        timezone = pytz.timezone(timezone_str)
        logger.info(f"Używanie strefy czasowej: {timezone_str} dla tablicy wyników")

        failures_count = 0

        while not client.is_closed():
            try:
                # Sprawdź czy leaderboard jest włączony
                if not is_leaderboard_enabled():
                    logger.info("Tablica wyników jest wyłączona. Sprawdzam ponownie za 5 minut...")
                    await asyncio.sleep(300)  # Sprawdź ponownie za 5 minut
                    continue

                # Pobierz konfigurację tablicy wyników
                leaderboard_day, leaderboard_hour, leaderboard_minute = get_leaderboard_time()

                # Pobierz aktualny czas w strefie czasowej Warszawy
                warsaw_now = datetime.datetime.now(timezone)
                logger.info(f"Aktualny czas warszawski: {warsaw_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

                # Znajdź następny dzień tygodnia, w którym ma być wysłana tablica
                days_ahead = leaderboard_day - warsaw_now.weekday()
                if days_ahead < 0:  # To już był ten dzień w tym tygodniu
                    days_ahead += 7
                elif days_ahead == 0 and (warsaw_now.hour > leaderboard_hour or
                                          (
                                                  warsaw_now.hour == leaderboard_hour and warsaw_now.minute >= leaderboard_minute)):
                    # To dziś, ale już po czasie wysłania
                    days_ahead = 7

                # Oblicz czas następnej tablicy
                next_leaderboard = warsaw_now.replace(hour=leaderboard_hour, minute=leaderboard_minute,
                                                      second=0, microsecond=0) + datetime.timedelta(days=days_ahead)

                # Oblicz czas oczekiwania
                wait_time = (next_leaderboard - warsaw_now).total_seconds()
                next_leaderboard_str = next_leaderboard.strftime('%Y-%m-%d %H:%M:%S %Z')
                logger.info(
                    f"Następna tablica wyników zaplanowana na {next_leaderboard_str}, oczekiwanie {wait_time} sekund")

                # Czekaj do czasu następnej tablicy
                await asyncio.sleep(wait_time)

                # Sprawdź ponownie, czy leaderboard jest nadal włączony
                if not is_leaderboard_enabled():
                    logger.info("Tablica wyników została wyłączona w trakcie oczekiwania. Pomijam wysyłanie.")
                    continue

                # Dla pewności sprawdź jeszcze raz aktualny czas przed wysłaniem
                current_time = datetime.datetime.now(timezone)
                logger.info(f"Czas przed wysłaniem tablicy: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

                # Wyślij tablicę wyników
                from leaderboard import send_leaderboard_to_channel
                logger.info("Rozpoczęto wysyłanie tygodniowej tablicy wyników...")
                success = await send_leaderboard_to_channel(client)

                if success:
                    logger.info("Tygodniowa tablica wyników wysłana pomyślnie")
                    # Po udanym wysłaniu resetuj licznik błędów
                    failures_count = 0
                else:
                    logger.error("Nie udało się wysłać tygodniowej tablicy wyników")
                    failures_count += 1

                # Nawet jeśli wystąpił błąd, poczekaj co najmniej 1 minutę przed próbą ponownego uruchomienia pętli
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("Planowanie tablicy wyników zostało anulowane")
                break
            except Exception as e:
                failures_count += 1
                logger.error(f"Błąd w planowaniu tablicy wyników: {e}")
                logger.error(traceback.format_exc())
                # Poczekaj przed ponowną próbą w przypadku błędu
                retry_time = min(60 * failures_count, 900)  # max 15 minut
                logger.info(f"Ponowna próba planowania za {retry_time} sekund")
                await asyncio.sleep(retry_time)
    except Exception as e:
        logger.critical(f"Krytyczny błąd w planowaniu tablicy wyników: {e}")
        logger.critical(traceback.format_exc())
