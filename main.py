# main.py
import asyncio
import logging
import os
import sys
import traceback

import discord
from dotenv import load_dotenv, find_dotenv

from bot_config import setup_bot_and_config
from commands import register_commands
from jira_client import get_jira_client
from tasks import bugs_update_loop, schedule_daily_report

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jira_discord_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('jira-discord-bot')


def load_environment_variables():
    """
    Ładuje zmienne środowiskowe z pliku .env
    z dokładniejszą diagnostyką potencjalnych problemów.
    """
    try:
        # Pobierz ścieżkę bieżącego pliku i katalog
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Bieżący katalog: {current_dir}")

        # Sprawdź czy plik .env istnieje w tym katalogu
        env_path = os.path.join(current_dir, '.env')
        if os.path.exists(env_path):
            logger.info(f"Znaleziono plik .env: {env_path}")

            # Próba bezpośredniego wczytania pliku dla diagnostyki
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_content = f.read()
                    logger.info(f"Plik .env odczytany, rozmiar: {len(env_content)} bajtów")

                    # Sprawdź czy plik zawiera podstawowe zmienne
                    has_discord = 'DISCORD_TOKEN' in env_content
                    has_jira = 'JIRA_SERVER' in env_content and 'JIRA_USERNAME' in env_content

                    if not has_discord:
                        logger.warning("Plik .env nie zawiera zmiennej DISCORD_TOKEN")
                    if not has_jira:
                        logger.warning("Plik .env nie zawiera podstawowych zmiennych Jira")
            except Exception as e:
                logger.error(f"Błąd podczas próby odczytu pliku .env: {e}")
        else:
            logger.error(f"Nie znaleziono pliku .env w katalogu: {current_dir}")
            # Próba znalezienia pliku .env w innych lokalizacjach
            dotenv_path = find_dotenv()
            if dotenv_path:
                logger.info(f"Znaleziono plik .env w innej lokalizacji: {dotenv_path}")
            else:
                logger.error("Nie znaleziono pliku .env w żadnej lokalizacji")
                return False

        # Załaduj zmienne środowiskowe
        loaded = load_dotenv(override=True)
        if loaded:
            logger.info("Zmienne środowiskowe załadowane pomyślnie")

            # Sprawdź czy kluczowe zmienne zostały faktycznie załadowane
            critical_vars = {
                'Discord': 'DISCORD_TOKEN',
                'Jira Server': 'JIRA_SERVER',
                'Jira Username': 'JIRA_USERNAME',
                'Jira API Token': 'JIRA_API_TOKEN'
            }

            for name, var in critical_vars.items():
                value = os.getenv(var)
                if not value:
                    logger.error(f"Nie załadowano zmiennej {var} ({name})")
                else:
                    # Nie loguj pełnych wartości wrażliwych danych
                    if var in ['DISCORD_TOKEN', 'JIRA_API_TOKEN']:
                        masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                        logger.info(f"Zmienna {var} załadowana pomyślnie (wartość: {masked})")
                    else:
                        logger.info(f"Zmienna {var} załadowana pomyślnie (wartość: {value})")

            # Sprawdź czy zmienne są dostępne bezpośrednio przez os.environ
            if 'JIRA_SERVER' not in os.environ:
                logger.warning("Zmienna JIRA_SERVER nie jest dostępna przez os.environ, próba ręcznego ustawienia")
                jira_server = os.getenv('JIRA_SERVER')
                if jira_server:
                    os.environ['JIRA_SERVER'] = jira_server
                    logger.info("Ręcznie ustawiono JIRA_SERVER w os.environ")

            return True
        else:
            logger.error("load_dotenv() zwróciło False - problem z ładowaniem zmiennych")
            return False

    except Exception as e:
        logger.error(f"Błąd podczas ładowania zmiennych środowiskowych: {e}")
        logger.error(traceback.format_exc())
        return False


# Główna funkcja uruchamiająca bota
async def main():
    try:
        logger.info("Uruchamianie bota Jira-Discord...")

        # Ładowanie zmiennych środowiskowych
        if not load_environment_variables():
            logger.error("Nie udało się załadować zmiennych środowiskowych. Bot może nie działać poprawnie.")

        # Inicjalizacja zmiennych bezpośrednio z os.environ (bez użycia os.getenv)
        # Możliwe że os.getenv nie działa poprawnie w Twoim środowisku
        global JIRA_SERVER, JIRA_USERNAME, JIRA_API_TOKEN, JIRA_PROJECT
        try:
            JIRA_SERVER = os.environ.get('JIRA_SERVER')
            JIRA_USERNAME = os.environ.get('JIRA_USERNAME')
            JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
            JIRA_PROJECT = os.environ.get('JIRA_PROJECT')

            # Ustaw te zmienne globalnie na wypadek, gdyby problem był z ich zasięgiem
            os.environ['JIRA_SERVER'] = JIRA_SERVER if JIRA_SERVER else ""
            os.environ['JIRA_USERNAME'] = JIRA_USERNAME if JIRA_USERNAME else ""
            os.environ['JIRA_API_TOKEN'] = JIRA_API_TOKEN if JIRA_API_TOKEN else ""
            os.environ['JIRA_PROJECT'] = JIRA_PROJECT if JIRA_PROJECT else ""

            logger.info(f"Zmienne Jira: SERVER={JIRA_SERVER}, USERNAME={JIRA_USERNAME}, PROJECT={JIRA_PROJECT}")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji zmiennych Jira: {e}")

        # Sprawdzenie czy token jest dostępny
        DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
        if not DISCORD_TOKEN:
            logger.error("Brak tokenu Discord. Upewnij się, że plik .env zawiera DISCORD_TOKEN.")
            return

        # Inicjalizacja konfiguracji bota
        client, tree = setup_bot_and_config()

        # Testowe połączenie z Jirą
        try:
            jira = get_jira_client()
            jira_user = jira.myself()
            logger.info(
                f"Połączenie z Jirą nawiązane pomyślnie jako {jira_user['displayName']} ({jira_user['emailAddress']})")
            logger.info(f"URL Jira: {JIRA_SERVER}")
            logger.info(f"Projekt Jira: {JIRA_PROJECT}")
        except ValueError as ve:
            # ValueError jest rzucany, gdy brakuje zmiennych konfiguracyjnych
            logger.error(f"Błąd konfiguracji Jira: {ve}")
            logger.warning("Bot uruchomi się, ale funkcje Jiry nie będą działać")
        except Exception as e:
            # Inne błędy mogą wskazywać na problemy z połączeniem, błędne dane logowania itp.
            logger.error(f"Test połączenia z Jirą nie powiódł się: {e}")
            logger.error(traceback.format_exc())
            logger.warning("Bot uruchomi się, ale funkcje Jiry mogą nie działać poprawnie")

        # Rejestracja komend
        register_commands(tree)

        # Event handler dla on_ready
        @client.event
        async def on_ready():
            try:
                logger.info(f'{client.user} połączony z Discord!')

                # Synchronizacja komend dla wszystkich serwerów
                await tree.sync()
                logger.info("Komendy slash zostały zsynchronizowane globalnie")

                # Opcjonalna szybka synchronizacja dla jednego serwera
                guild_id = int(os.environ.get('DISCORD_GUILD_ID', '0'))
                if guild_id != 0:
                    guild = discord.Object(id=guild_id)
                    await tree.sync(guild=guild)
                    logger.info(f"Komendy slash zostały zsynchronizowane dla serwera {guild_id}")

                # Uruchomienie pętli aktualizacji bugów
                client.loop.create_task(bugs_update_loop(client))

                # Uruchomienie planowania raportów dziennych
                client.loop.create_task(schedule_daily_report(client))
            except Exception as e:
                logger.error(f"Błąd podczas inicjalizacji bota: {e}")
                logger.error(traceback.format_exc())

        # Uruchomienie bota
        await client.start(DISCORD_TOKEN)

    except Exception as e:
        logger.critical(f"Krytyczny błąd podczas uruchamiania bota: {e}")
        logger.critical(traceback.format_exc())


# Uruchomienie bota z obsługą przerwania
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot zatrzymany przez użytkownika (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Nieoczekiwany błąd: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)