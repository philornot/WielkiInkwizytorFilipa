# leaderboard.py
import logging
import os
import traceback
from datetime import datetime, timedelta
from typing import List, Dict

import discord
import pytz

from discord_embeds import _get_name_mapping
from jira_client import get_jira_client

logger = logging.getLogger('WielkiInkwizytorFilipa')


def debug_name_mapping():
    """
    Funkcja diagnostyczna do wypisania mapowania imion.
    Pomoże zrozumieć jakie mapowania są faktycznie wczytywane.
    """
    logger.info("---- DIAGNOSTYKA MAPOWANIA IMION ----")

    try:
        name_mapping_str = os.getenv('NAME_MAPPING', '')
        logger.info(f"Zawartość zmiennej NAME_MAPPING: '{name_mapping_str}'")

        if not name_mapping_str:
            logger.warning("Zmienna NAME_MAPPING jest pusta!")
            return

        pairs = name_mapping_str.split(';')
        logger.info(f"Znaleziono {len(pairs)} par w mapowaniu")

        for i, pair in enumerate(pairs):
            logger.info(f"Para {i + 1}: '{pair}'")

            if ':' in pair:
                full_name, short_name = pair.split(':', 1)
                logger.info(f"  -> Mapowanie: '{full_name.strip()}' na '{short_name.strip()}'")
            else:
                logger.warning(f"  -> Nieprawidłowy format pary (brak znaku ':'): '{pair}'")

    except Exception as e:
        logger.error(f"Błąd podczas analizy mapowania imion: {e}")
        logger.error(traceback.format_exc())

    logger.info("---- KONIEC DIAGNOSTYKI MAPOWANIA ----")


async def fetch_user_statistics(days: int = 30) -> List[Dict]:
    """
    Pobiera statystyki zadań ukończonych przez użytkowników w określonym okresie.
    Uwzględnia również zadania nieprzypisane i przypisane do innych użytkowników.
    Pomija epiki w statystykach.

    Args:
        days (int): Liczba dni wstecz do analizy (domyślnie 30)

    Returns:
        List[Dict]: Lista słowników ze statystykami użytkowników
    """
    try:
        # Diagnostyka mapowania imion
        debug_name_mapping()

        jira_project = os.environ.get('JIRA_PROJECT')
        jira = get_jira_client()

        # Pobierz strefę czasową z konfiguracji
        timezone_str = os.getenv('TIMEZONE', 'Europe/Warsaw')
        timezone = pytz.timezone(timezone_str)

        # Obliczanie przedziału czasowego
        end_time = datetime.now(timezone)
        start_time = end_time - timedelta(days=days)

        # Formatowanie dat dla zapytania JQL
        start_date = start_time.strftime('%Y-%m-%d')
        end_date = end_time.strftime('%Y-%m-%d')

        # Zapytanie JQL o zadania ukończone w określonym okresie
        # Usuwamy warunek przypisania żeby zobaczyć wszystkie zadania
        jql_query = (
            f'project = "{jira_project}" '
            f'AND status = Done '
            f'AND resolved >= "{start_date}" '
            f'AND resolved <= "{end_date} 23:59" '
            f'ORDER BY assignee ASC'
        )

        logger.info(f"Pobieranie zadań dla leaderboard z okresu: {start_date} - {end_date}")
        logger.info(f"Zapytanie JQL: {jql_query}")

        # Zwiększamy maksymalną liczbę wyników, aby pobrać wszystkie zadania
        all_tasks = []
        start_at = 0
        max_results = 100  # Pobieraj po 100 zadań na raz (typowy limit Jira API)
        max_total = 1000  # Maksymalna liczba zadań do pobrania (zabezpieczenie)
        total_loaded = 0

        # Ulepszony kod paginacji
        while True:
            logger.info(f"Pobieranie strony zadań: startAt={start_at}, maxResults={max_results}")
            tasks_batch = jira.search_issues(jql_query, startAt=start_at, maxResults=max_results)

            if not tasks_batch:
                logger.info("Otrzymano pustą partię zadań, kończenie pobierania")
                break

            batch_size = len(tasks_batch)
            logger.info(f"Pobrano partię {batch_size} zadań")

            all_tasks.extend(tasks_batch)
            total_loaded += batch_size

            # Jeśli liczba pobranych zadań jest mniejsza niż max_results, to znaczy że pobrano wszystkie
            if batch_size < max_results:
                logger.info(f"Pobrano mniej zadań niż maxResults ({batch_size} < {max_results}), kończenie pobierania")
                break

            # Przechodzimy do następnej strony
            start_at += batch_size

            # Zabezpieczenie przed nieskończoną pętlą
            if total_loaded >= max_total:
                logger.warning(f"Osiągnięto maksymalną liczbę zadań do pobrania ({max_total}), przerywanie")
                break

        logger.info(f"Pobrano łącznie {len(all_tasks)} zadań do analizy")

        # Pobierz mapowanie nazw użytkowników
        name_mapping = _get_name_mapping()
        logger.info(f"Wczytano {len(name_mapping)} mapowań imion")

        # Debug - wypisz wszystkie odwrotne mapowania dla lepszej diagnostyki
        inverted_mapping = {v: k for k, v in name_mapping.items()}
        logger.info(f"Odwrotne mapowanie imion: {inverted_mapping}")

        # Zbieranie statystyk według użytkowników
        user_stats = {}
        skipped_epics = 0
        skipped_unassigned = 0

        # Dodaj wartość do mapowania dla zadań nieprzypisanych
        unassigned_name = "Nieprzypisane zadania"
        unassigned_id = "unassigned"

        # Utwórz pustą statystykę dla unassigned, żeby zawsze się pojawiało
        user_stats[unassigned_id] = {
            "name": unassigned_name,
            "tasks_total": 0,
            "task_types": {},
            "tasks": []
        }

        # Dodaj puste statystyki dla wszystkich użytkowników w mapowaniu
        # To zapewni, że każdy z zespołu będzie widoczny nawet bez zadań
        for full_name, short_name in name_mapping.items():
            user_id = f"mapped_{full_name}"  # Unikalny identyfikator
            user_stats[user_id] = {
                "name": short_name,
                "tasks_total": 0,
                "task_types": {},
                "tasks": []
            }
            logger.info(f"Dodano pustą statystykę dla użytkownika {short_name} ({full_name})")

        for task in all_tasks:
            try:
                # Sprawdź czy to nie jest epik
                issue_type = task.fields.issuetype.name
                if issue_type.lower() == "epic":
                    skipped_epics += 1
                    logger.info(f"Pomijam epik: {task.key} - {task.fields.summary}")
                    continue

                # Pobieranie informacji o przypisanym użytkowniku
                assignee = None
                assignee_name = "Nieprzypisany"
                assignee_id = unassigned_id

                if hasattr(task.fields, 'assignee') and task.fields.assignee:
                    assignee = task.fields.assignee
                    assignee_name = assignee.displayName

                    logger.info(f"Przetwarzanie zadania {task.key} przypisanego do '{assignee_name}'")

                    # Sprawdź czy istnieje mapowanie nazwy
                    if assignee_name in name_mapping:
                        logger.info(f"Znaleziono mapowanie dla '{assignee_name}' -> '{name_mapping[assignee_name]}'")
                        assignee_name = name_mapping[assignee_name]
                        assignee_id = f"mapped_{assignee.displayName}"  # Używamy oryginalnej nazwy jako ID
                    else:
                        logger.warning(f"Brak mapowania dla '{assignee_name}'. Dostępne mapowania: {name_mapping}")
                        # Jeśli nie ma mapowania, używamy oryginalnej nazwy
                        assignee_id = f"original_{assignee.displayName}"
                else:
                    # Dla nieprzypisanych zadań używamy unassigned_id
                    logger.info(f"Zadanie {task.key} nie ma przypisanego użytkownika")
                    skipped_unassigned += 1
                    # Tym razem NIE pomijamy zadań nieprzypisanych
                    # continue

                # Inicjalizacja statystyk dla nowego użytkownika
                if assignee_id not in user_stats:
                    user_stats[assignee_id] = {
                        "name": assignee_name,
                        "tasks_total": 0,
                        "task_types": {},
                        "tasks": []
                    }
                    logger.info(f"Utworzono nową statystykę dla użytkownika {assignee_name} (ID: {assignee_id})")

                # Zwiększenie liczby ukończonych zadań
                user_stats[assignee_id]["tasks_total"] += 1

                # Zliczanie typów zadań
                if issue_type not in user_stats[assignee_id]["task_types"]:
                    user_stats[assignee_id]["task_types"][issue_type] = 0
                user_stats[assignee_id]["task_types"][issue_type] += 1

                # Dodanie zadania do listy
                user_stats[assignee_id]["tasks"].append({
                    "key": task.key,
                    "summary": task.fields.summary,
                    "type": issue_type,
                    "resolved": getattr(task.fields, 'resolutiondate', 'unknown')
                })

            except Exception as task_error:
                logger.error(f"Błąd podczas przetwarzania zadania {task.key}: {task_error}")
                logger.error(traceback.format_exc())
                continue

        # Konwersja statystyk na listę i sortowanie według liczby zadań
        stats_list = []
        for user_id, stats in user_stats.items():
            # Dodaj tylko użytkowników, którzy mają zadania (chyba że to ID z mapowania)
            if stats["tasks_total"] > 0 or user_id.startswith("mapped_"):
                stats["user_id"] = user_id
                stats_list.append(stats)
                logger.info(f"Dodano do rankingu: {stats['name']} (zadania: {stats['tasks_total']})")
            else:
                logger.info(f"Pominięto w rankingu: {stats['name']} (brak zadań)")

        stats_list.sort(key=lambda x: x["tasks_total"], reverse=True)

        logger.info(f"Znaleziono statystyki dla {len(stats_list)} użytkowników")
        logger.info(f"Pominięto epików: {skipped_epics}, nieprzypisanych zadań: {skipped_unassigned}")

        # Wypisz statystyki dla debugowania
        for user in stats_list:
            logger.debug(f"Użytkownik: {user['name']}, Liczba zadań: {user['tasks_total']}")
            for task_type, count in user['task_types'].items():
                logger.debug(f"  - {task_type}: {count}")

        return stats_list

    except Exception as e:
        logger.error(f"Błąd podczas pobierania statystyk użytkowników: {e}")
        logger.error(traceback.format_exc())
        return []


def get_roast_for_inactive_member(name: str) -> str:
    """
    Zwraca humorystyczny "roast" dla nieaktywnego członka zespołu.

    Args:
        name (str): Imię członka zespołu

    Returns:
        str: Humorystyczny tekst
    """
    roasts = [
        f"{name} - widziani ostatnio: nigdy. Może są na wakacjach... które trwają cały rok?",
        f"{name} wykonał tyle zadań, ile jest jednorożców na świecie.",
        f"{name} - legenda głosi, że kiedyś coś zrobił, ale nikt tego nie widział.",
        f"{name} osiągnął idealne zero. Brawo za konsekwencję!",
        f"{name} ma ciekawą strategię: \"nie można zrobić błędu w zadaniu, jeśli się go nie podejmie\".",
        f"{name} prawdopodobnie myśli, że Jira to gatunek kawy.",
        f"{name} - ekspert od delegowania zadań... sobie samemu w przyszłości.",
        f"{name} traktuje deadline'y jak wskazówki, a nie zobowiązania.",
        f"{name} - mistrz prokrastynacji roku!",
        f"{name} ma tyle samo zadań co smutny Excel bez danych.",
        f"{name} występuje w projekcie na takiej samej zasadzie jak John Cena - nikt go nie widzi.",
        f"{name} to ekspert w sztuce niedotrzymywania terminów.",
        f"{name} pobiera pensję za mistrzowskie udawanie, że pracuje.",
        f"{name} podobno wciąż poszukuje przycisku \"Start\" w Jirze.",
        f"{name} ma na koncie więcej wymówek niż zadań.",
        f"{name} - dział HR wciąż sprawdza, czy faktycznie istnieje.",
        f"{name} traktuje zadania jak UFO - wierzy, że istnieją, ale nigdy ich nie widział.",
        f"{name} myśli, że \"sprint\" to konkurencja lekkoatletyczna, a nie termin na zadania.",
        f"{name} będzie dostępny kiedy skończy oglądać \"jeszcze jeden odcinek\".",
        f"{name} osiągnął stan nirwany produkcyjnej - pełna pustka.",
        f"{name} - status projektów: dane wrażliwe, nikt nie może ich zobaczyć.",
        f"{name} - według naukowców, jego produktywność jest mniejsza niż u kamienia.",
        f"{name} - gdyby lenistwo było olimpijską dyscypliną, miałby złoty medal.",
        f"{name} spędza więcej czasu na pisaniu wymówek niż na faktycznej pracy.",
        f"{name} myśli, że \"deadline\" to nazwa nowego filmu akcji.",
        f"{name} - nawet Bot spędza więcej czasu przy komputerze.",
        f"{name} jest jak WiFi w tunelu - straciliśmy połączenie.",
        f"{name} - Wielki Inkwizytor Filipa wysyła mu już trzecie wezwanie do pracy.",
        f"{name} używa projektu jak statusu na LinkedIn - jest tam, ale nic nie robi.",
        f"{name} uważa, że \"backlog\" to nowa restauracja w mieście.",
        f"{name} myśli, że \"pull request\" to prośba o wyciągnięcie go z łóżka.",
        f"{name} - jedyne co ciągnie, to wagary od projektu.",
        f"{name} mógłby wystąpić w \"Gdzie jest Waldo?\" projektu.",
        f"{name} jest jak yeti projektu - wszyscy o nim słyszeli, ale nikt go nie widział.",
        f"{name} ma więcej nieukończonych zadań niż Tolkien niedokończonych historii.",
        f"{name} - uśpiony agent, wciąż czeka na kod aktywacyjny.",
        f"{name} uczestniczy w projekcie jak duch - wszyscy wiedzą, że gdzieś jest, ale nikt go nie widzi.",
        f"{name} wnosi do zespołu tyle samo, co pusty kubek do kolekcji kawy.",
        f"{name} ma więcej wykrętów niż szwajcarski scyzoryk funkcji.",
        f"{name} - jego ulubiony film to \"Zniknięcie\" a ulubiona piosenka \"Sound of Silence\".",
        f"{name} to jedyna osoba, która traktuje pracę jak starą znajomą - odwiedza ją raz na rok.",
        f"{name} - odkrył sposób na pracę bez pracy. Naukowcy są zaskoczeni!",
        f"{name} myśli, że GitHub to serwis społecznościowy dla kotów.",
        f"{name} - gdyby prokrastynacja była walutą, byłby miliarderem.",
        f"{name} nie wierzy w żadną religię, ale święcie wierzy, że zadania rozwiążą się same.",
        f"{name} podchodzi do terminów jak pirat do kodeksu - traktuje je bardziej jak wytyczne.",
        f"{name} ma na koncie mniej commitów niż przeciętny kamień.",
        f"{name} używa \"zajęty\" jako statusu permanentnego, mimo braku dowodów na to zajęcie.",
        f"{name} - nawet BOT ma wyższy wskaźnik aktywności.",
        f"{name} pomaga projektowi przez niezabieranie czasu innym.",
        f"{name} myśli, że \"klient\" to postać z bajki, a \"deadline\" to miejsce, gdzie umierają marzenia.",
        f"{name} istnieje w projekcie na zasadzie placebo - niby jest, ale efektów brak.",
        f"{name} uważa commita za rodzaj zobowiązania którego powinien unikać.",
        f"{name} przeżywa obecnie najdłuższy urlop w historii korporacji.",
        f"{name} pojawia się w projekcie rzadziej niż zaćmienie słońca.",
        f"{name} - w konkurencji na najrzadziej widzianego członka zespołu, zajmuje pierwsze miejsce.",
        f"{name} ma tyle samo ukończonych zadań co pingwin lotów transatlantyckich.",
        f"{name} myśli, że \"dokumentacja\" to nowy horror na Netflixie.",
        f"{name} został oficjalnie dodany do słownika jako synonim słowa \"nieobecny\".",
        f"{name} - jedyne, co push'uje, to przycisk \"snooze\" w budziku.",
        f"{name} jest jak ofiara w horrorze - wszyscy wiedzą, że nie przetrwa do końca projektu.",
        f"{name} ma najczystszą historię commitów - idealnie pustą.",
        f"{name} - jego wkład w projekt jest jak wkład homeopatyczny - teoretycznie istnieje.",
        f"{name} przechodzi przez całe życie używając jednego wymówienia: \"Zaraz do tego wrócę\".",
        f"{name} to mistrz w znajdowaniu wymówek, dlaczego nie może wykonać zadania.",
        f"{name} buduje swoje portfolio składające się głównie z pustych obietnic.",
        f"{name} jest tak zajęty \"planowaniem pracy\", że nie ma czasu na jej wykonanie.",
        f"{name} traktuje zadania jak dobre chęci - ma je, ale nic z nimi nie robi.",
        f"{name} - specjalista od deadlinów... pośmiertnych.",
        f"{name} - gdyby prokrastynacja była pracą, byłby prezesem firmy.",
        f"{name} ma więcej pustych obietnic niż pusty automat z przekąskami.",
        f"{name} prawdopodobnie myśli, że \"bug\" to tylko nieprzyjemne stworzenie.",
        f"{name} wykorzystuje system zarządzania projektem jak Facebooka - tylko podgląda.",
        f"{name} - już dwa stanowiska zajęte przez jego ghosting.",
        f"{name} ciągle pracuje zdalnie... od pracy.",
        f"{name} czeka na idealny moment, który nigdy nie nadejdzie.",
        f"{name} pojawia się w projekcie rzadziej niż kometa Halleya.",
        f"{name} opracował nową metodologię: NADA (Never Actually Do Anything).",
        f"{name} udowadnia, że można być częścią zespołu bez bycia częścią pracy zespołowej.",
        f"{name} prawdopodobnie myśli, że \"sprint\" to tylko sposób na szybkie bieganie.",
        f"{name} jest ekspertem w sztuce bycia niewidocznym w projekcie.",
        f"{name} został oficjalnie uznany za legendę miejską projektu.",
        f"{name} - badacze wciąż szukają dowodów na jego wkład w projekt.",
        f"{name} myśli, że \"milestone\" to nazwa zespołu rockowego.",
        f"{name} traktuje zadania jak swoje urodziny - pamięta o nich raz w roku.",
        f"{name} ma w grafiku więcej wolnego niż nauczyciel w wakacje.",
        f"{name} ma więcej nieobecności niż obecności.",
        f"{name} myśli, że \"feedback\" to nazwa nowego fast foodu.",
        f"{name} jest jak Schrödinger's Dev - teoretycznie pracuje i nie pracuje jednocześnie.",
        f"{name} osiągnął perfekcję w sztuce unikania odpowiedzialności.",
        f"{name} jest tak dobry w ukrywaniu się, że nawet satelity go nie widzą.",
        f"{name} - ostatni raz widziany podczas rekrutacji.",
        f"{name} jest niczym ninja - nigdy nie wiesz, czy jest, czy go nie ma. Zazwyczaj go nie ma.",
        f"{name} myśli, że Jira to egzotyczne danie kuchni tajskiej.",
        f"{name} - jego ostatni commit jest już zabytkiem archeologicznym.",
        f"{name} ma mniej aktywności w projekcie niż średniowieczny mnich w internecie.",
        f"{name} pojawia się w pracy rzadziej niż deszcz na Saharze.",
        f"{name} wykonał imponującą liczbę zadań: 0. Tylko nieliczni potrafią utrzymać taką konsekwencję!",
        f"{name} stosuje metodologię pracy: \"Zostawię to dla przyszłego mnie, który i tak tego nie zrobi.\"",
        f"{name} - prawdopodobnie myśli, że \"deployment\" to rodzaj dekoracji.",
        f"{name} osiągnął zen poprzez całkowity brak jakiejkolwiek produkcji."
    ]
    import random
    return random.choice(roasts)


def create_leaderboard_embed(stats_list: List[Dict], days: int) -> discord.Embed:
    """
    Tworzy embed z tablicą wyników.

    Args:
        stats_list (List[Dict]): Lista statystyk użytkowników
        days (int): Okres w dniach, za który generowana jest tablica

    Returns:
        discord.Embed: Embed z tablicą wyników
    """
    try:
        # Pobierz strefę czasową z konfiguracji
        timezone_str = os.getenv('TIMEZONE', 'Europe/Warsaw')
        timezone = pytz.timezone(timezone_str)

        # Aktualna data i czas
        now = datetime.now(timezone)

        # Usuwamy "Nieprzypisane zadania" z rankingu
        stats_list = [user for user in stats_list if user["name"] != "Nieprzypisane zadania"]

        # Znajdź aktywnych i nieaktywnych użytkowników
        active_users = [user for user in stats_list if user["tasks_total"] > 0]
        inactive_users = [user for user in stats_list if user["tasks_total"] == 0]

        # Sortujemy aktywnych użytkowników według liczby zadań
        active_users.sort(key=lambda x: x["tasks_total"], reverse=True)

        # Tworzenie embeda
        embed = discord.Embed(
            title=f"🏆 Tablica wyników - ostatnie {days} dni",
            description=f"Ranking zaangażowania członków zespołu od {(now - timedelta(days=days)).strftime('%d.%m.%Y')} do {now.strftime('%d.%m.%Y')}",
            color=0x00AAFF  # Niebieski kolor
        )

        if not active_users:
            embed.add_field(
                name="Brak danych",
                value="Nie znaleziono ukończonych zadań w analizowanym okresie.",
                inline=False
            )
            return embed

        # Generowanie rankingu aktywnych użytkowników
        leaderboard_text = ""
        for index, user in enumerate(active_users):
            # Emoji dla top 3
            position_emoji = "🥇" if index == 0 else "🥈" if index == 1 else "🥉" if index == 2 else f"{index + 1}."

            # Tekst z liczbą zadań
            task_text = f"{user['tasks_total']} zadań"

            # Dodanie wpisu dla użytkownika
            leaderboard_text += f"{position_emoji} **{user['name']}**: {task_text}\n"

        embed.add_field(
            name="Ranking ukończonych zadań",
            value=leaderboard_text,
            inline=False
        )

        # Dodanie informacji o typach zadań dla top 3 (maksymalnie)
        for index, user in enumerate(active_users[:3]):
            if index >= len(active_users):
                break

            # Przygotowanie tekstu o typach zadań
            task_types_text = ""
            for task_type, count in user["task_types"].items():
                # Pomijamy epiki
                if task_type.lower() != "epic":
                    task_types_text += f"{task_type}: {count}\n"

            medal = "🥇" if index == 0 else "🥈" if index == 1 else "🥉"
            embed.add_field(
                name=f"{medal} {user['name']} - szczegóły",
                value=task_types_text if task_types_text else "Brak zadań",
                inline=True
            )

        # Dodaj roasty dla nieaktywnych użytkowników
        if inactive_users:
            inactive_text = ""
            for user in inactive_users:
                inactive_text += f"• {get_roast_for_inactive_member(user['name'])}\n"

            embed.add_field(
                name="⚠️ Ściana wstydu ⚠️",
                value=inactive_text,
                inline=False
            )

        # Dodanie stopki
        embed.set_footer(text=f"Wygenerowano {now.strftime('%d.%m.%Y %H:%M:%S')} • Wielki Inkwizytor Filipa")

        return embed

    except Exception as e:
        logger.error(f"Błąd podczas tworzenia embeda z tablicą wyników: {e}")
        logger.error(traceback.format_exc())

        # Utworzenie embeda błędu
        error_embed = discord.Embed(
            title="⚠️ Błąd tablicy wyników",
            description=f"Wystąpił błąd podczas generowania tablicy wyników: {str(e)}",
            color=discord.Color.orange()
        )
        return error_embed


async def generate_leaderboard(days: int = 30) -> discord.Embed:
    """
    Główna funkcja generująca tablicę wyników.

    Args:
        days (int): Liczba dni wstecz do analizy (domyślnie 30)

    Returns:
        discord.Embed: Wygenerowana tablica wyników
    """
    try:
        logger.info(f"Generowanie tablicy wyników za ostatnie {days} dni")

        # Pobierz statystyki użytkowników
        stats = await fetch_user_statistics(days)

        # Utwórz embed z tablicą wyników
        embed = create_leaderboard_embed(stats, days)

        logger.info(f"Tablica wyników wygenerowana pomyślnie dla {len(stats)} użytkowników")
        return embed

    except Exception as e:
        logger.error(f"Błąd podczas generowania tablicy wyników: {e}")
        logger.error(traceback.format_exc())

        # Utworzenie embeda błędu
        error_embed = discord.Embed(
            title="⚠️ Błąd tablicy wyników",
            description=f"Wystąpił błąd podczas generowania tablicy wyników: {str(e)}",
            color=discord.Color.orange()
        )
        return error_embed


async def send_leaderboard_to_channel(client, channel_id=None):
    """
    Wysyła tablicę wyników na określony kanał.

    Args:
        client (discord.Client): Klient Discord
        channel_id (int, optional): ID kanału, na który ma być wysłana tablica.
            Jeśli nie podano, używany jest kanał raportów.

    Returns:
        bool: True jeśli wysłanie się powiodło, False w przeciwnym razie
    """
    try:
        from bot_config import get_channel_id

        # Jeśli nie podano ID kanału, użyj kanału raportów
        if not channel_id:
            channel_id = get_channel_id('reports')

        if not channel_id:
            logger.error("Nie ustawiono ID kanału dla tablicy wyników")
            return False

        channel = client.get_channel(channel_id)
        if not channel:
            logger.error(f"Nie można znaleźć kanału o ID {channel_id}")
            return False

        # Generuj tablicę wyników
        logger.info(f"Generowanie tablicy wyników dla kanału {channel.name} (ID: {channel_id})")
        leaderboard_embed = await generate_leaderboard()

        # Wysłanie tablicy
        await channel.send(embed=leaderboard_embed)
        logger.info(f"Wysłano tablicę wyników na kanał {channel.name}")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas wysyłania tablicy wyników: {e}")
        logger.error(traceback.format_exc())
        return False
