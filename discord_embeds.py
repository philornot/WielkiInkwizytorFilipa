# discord_embeds.py
import datetime
import logging
import traceback
import os
from typing import List, Dict

import discord
import pytz
from jira.resources import Issue

logger = logging.getLogger('jira-discord-bot')


def _get_name_mapping() -> Dict[str, str]:
    """
    Pobiera mapowanie pełnych nazw użytkowników na skrócone imiona z konfiguracji.
    Format w .env: NAME_MAPPING=pełne_imię_nazwisko:skrót;drugie_imię_nazwisko:skrót2

    Returns:
        Dict[str, str]: Słownik mapujący pełne nazwy na skrócone imiona
    """
    mapping = {}
    try:
        name_mapping_str = os.getenv('NAME_MAPPING', '')
        if name_mapping_str:
            pairs = name_mapping_str.split(';')
            for pair in pairs:
                if ':' in pair:
                    full_name, short_name = pair.split(':', 1)
                    mapping[full_name.strip()] = short_name.strip()
                    logger.debug(f"Dodano mapowanie imienia: {full_name} -> {short_name}")

        logger.info(f"Wczytano {len(mapping)} mapowań imion")
        return mapping
    except Exception as e:
        logger.error(f"Błąd podczas wczytywania mapowania imion: {e}")
        logger.error(traceback.format_exc())
        return {}


def _get_display_name(full_name: str) -> str:
    """
    Konwertuje pełną nazwę użytkownika na nazwę wyświetlaną, używając mapowania z .env.

    Args:
        full_name (str): Pełna nazwa użytkownika

    Returns:
        str: Nazwa wyświetlana (skrócona lub oryginalna jeśli nie ma mapowania)
    """
    mapping = _get_name_mapping()
    return mapping.get(full_name, full_name)


def create_bugs_embeds(issues: List[Issue]) -> List[discord.Embed]:
    """
    Tworzy listę embedów Discord z bugami z Jiry.

    Args:
        issues (List[Issue]): Lista bugów z Jiry

    Returns:
        List[discord.Embed]: Lista embedów do wysłania
    """
    try:
        embeds = []

        if not issues:
            # Uzyskaj aktualny czas w strefie czasowej Warszawy
            timezone = pytz.timezone('Europe/Warsaw')
            now = datetime.datetime.now(timezone)
            timestamp = now.strftime('%d.%m.%Y %H:%M:%S')

            embed = discord.Embed(
                title="Aktualna lista bugów",
                description=f"Ostatnia aktualizacja: {timestamp}",
                color=discord.Color.red()
            )
            embed.add_field(name="Brak bugów", value="Nie znaleziono żadnych bugów spełniających kryteria.",
                            inline=False)
            embeds.append(embed)
            return embeds

        # Aktualny timestamp dla wszystkich embedów w strefie czasowej Warszawy
        timezone = pytz.timezone('Europe/Warsaw')
        now = datetime.datetime.now(timezone)
        timestamp = now.strftime('%d.%m.%Y %H:%M:%S')

        # Grupowanie bugów według statusu
        status_groups = {}
        for issue in issues:
            try:
                status = issue.fields.status.name
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(issue)
            except AttributeError as ae:
                logger.warning(
                    f"Pominięto buga z powodu braku atrybutu: {ae} (Issue key: {issue.key if hasattr(issue, 'key') else 'unknown'})")
                continue

        # Pierwszy embed z tytułem i czasem aktualizacji
        current_embed = discord.Embed(
            title="Aktualna lista bugów",
            description=f"Ostatnia aktualizacja: {timestamp}",
            color=discord.Color.red()
        )

        # Dla każdego statusu dodaj bugi do embedów
        for status, bugs in status_groups.items():
            bug_chunks = []  # Lista kawałków tekstu dla danego statusu
            current_chunk = ""

            # Przygotuj wpisy dla wszystkich bugów w danym statusie
            for bug in bugs:
                try:
                    assignee = "Nieprzypisany"
                    if hasattr(bug.fields, 'assignee') and bug.fields.assignee:
                        full_name = bug.fields.assignee.displayName
                        assignee = _get_display_name(full_name)

                    # Formatowanie wpisu buga
                    bug_entry = f"• **{bug.key}** - {bug.fields.summary} "

                    # Dodanie info o przypisanej osobie w nowym formacie
                    if assignee != "Nieprzypisany":
                        bug_entry += f"(_Przypisany: {assignee}_)\n"
                    else:
                        bug_entry += f"(_Nieprzypisany_)\n"

                    # Sprawdź, czy dodanie nowego wpisu nie przekroczy limitu 1024 znaków
                    if len(current_chunk + bug_entry) > 1000:  # Limit bezpieczeństwa dla pojedynczego pola
                        bug_chunks.append(current_chunk)
                        current_chunk = bug_entry
                    else:
                        current_chunk += bug_entry
                except Exception as bug_error:
                    logger.error(
                        f"Błąd podczas przetwarzania buga {bug.key if hasattr(bug, 'key') else 'unknown'}: {bug_error}")
                    continue

            # Dodaj ostatni kawałek, jeśli nie jest pusty
            if current_chunk:
                bug_chunks.append(current_chunk)

            # Dodaj kawałki jako pola do embedów
            for i, chunk in enumerate(bug_chunks):
                field_name = f"{status}" if len(bug_chunks) == 1 else f"{status} (część {i + 1})"

                # Sprawdź, czy dodanie nowego pola nie przekroczy limitu pól (25) lub limitu rozmiaru (6000)
                # Discord ma limit 25 pól na embed
                if len(current_embed.fields) >= 24 or len(current_embed) + len(field_name) + len(chunk) > 5900:
                    # Jeśli tak, dodaj stopkę do bieżącego embeda
                    current_embed.set_footer(text="Aby odświeżyć ręcznie użyj /refresh | Bot Jira-Discord")
                    # Dodaj bieżący embed do listy
                    embeds.append(current_embed)
                    # Utwórz nowy embed
                    current_embed = discord.Embed(
                        title="Aktualna lista bugów (kontynuacja)",
                        description=f"Ostatnia aktualizacja: {timestamp}",
                        color=discord.Color.red()
                    )

                # Dodaj pole do bieżącego embeda
                current_embed.add_field(name=field_name, value=chunk, inline=False)

        # Dodaj stopkę do ostatniego embeda
        current_embed.set_footer(text="Aby odświeżyć ręcznie użyj /refresh | Bot Jira-Discord")
        # Dodaj ostatni embed do listy
        embeds.append(current_embed)

        logger.info(f"Utworzono {len(embeds)} embedów z bugami")
        return embeds

    except Exception as e:
        logger.error(f"Błąd podczas tworzenia embedów z bugami: {e}")
        logger.error(traceback.format_exc())
        # Zwróć podstawowy embed z informacją o błędzie
        error_embed = discord.Embed(
            title="Błąd podczas pobierania bugów",
            description=f"Wystąpił błąd podczas generowania listy bugów: {str(e)}",
            color=discord.Color.orange()
        )
        return [error_embed]


def create_completed_tasks_report(tasks: List[Issue], start_time: datetime.datetime, end_time: datetime.datetime,
                                  jira_server: str) -> discord.Embed:
    """
    Tworzy embed z raportem ukończonych zadań.

    Args:
        tasks (List[Issue]): Lista ukończonych zadań
        start_time (datetime.datetime): Czas początkowy raportu
        end_time (datetime.datetime): Czas końcowy raportu
        jira_server (str): URL serwera Jira

    Returns:
        discord.Embed: Embed z raportem
    """
    try:
        # Tworzenie embeda z raportem
        embed = discord.Embed(
            title="📊 Raport ukończonych zadań",
            description=f"Okres: {start_time.strftime('%d.%m.%Y %H:%M')} - {end_time.strftime('%d.%m.%Y %H:%M')}",
            color=0x0052CC  # Kolor Jira Blue
        )

        if not tasks:
            embed.add_field(
                name="Brak zadań",
                value="Nie znaleziono żadnych ukończonych zadań w tym okresie.",
                inline=False
            )
            return embed

        # Przetwarzanie zadań według użytkowników
        tasks_by_user = {}
        for task in tasks:
            try:
                assignee = task.fields.assignee
                if assignee:
                    full_name = assignee.displayName
                    display_name = _get_display_name(full_name)

                    if display_name not in tasks_by_user:
                        tasks_by_user[display_name] = {"count": 0, "tasks": []}

                    tasks_by_user[display_name]["count"] += 1
                    task_link = f"[{task.key}]({jira_server}/browse/{task.key})"
                    tasks_by_user[display_name]["tasks"].append(task_link)
            except Exception as task_error:
                logger.error(
                    f"Błąd podczas przetwarzania zadania {task.key if hasattr(task, 'key') else 'unknown'}: {task_error}")
                continue

        # Dodawanie pól dla każdego użytkownika
        for user, data in tasks_by_user.items():
            # Limit długości pola Discord to 1024 znaki
            task_data = ", ".join(data["tasks"])
            # Jeśli lista zadań jest zbyt długa, dzielimy ją na części
            if len(task_data) > 1000:
                # Podziel listę zadań na części, które zmieszczą się w polu
                user_field_count = 1
                for i in range(0, len(data["tasks"]), 10):  # Po 10 zadań na pole
                    chunk = ", ".join(data["tasks"][i:i + 10])
                    field_name = f"{user} (część {user_field_count})" if len(data["tasks"]) > 10 else user
                    embed.add_field(
                        name=field_name,
                        value=f"{len(data['tasks'][i:i + 10])} zadań: {chunk}",
                        inline=False
                    )
                    user_field_count += 1
            else:
                # Jeśli lista zadań zmieści się w jednym polu
                embed.add_field(
                    name=user,
                    value=f"{data['count']} zadań: {task_data}",
                    inline=False
                )

        # Dodawanie informacji o łącznej liczbie zadań
        embed.add_field(
            name=f"Łączna liczba ukończonych zadań: {len(tasks)}",
            value="\u200b",  # Niewidoczny znak, by pole miało treść
            inline=False
        )

        return embed
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia raportu z zadaniami: {e}")
        logger.error(traceback.format_exc())
        # Utworzenie embeda z informacją o błędzie
        error_embed = discord.Embed(
            title="⚠️ Błąd raportu",
            description=f"Wystąpił błąd podczas generowania raportu: {str(e)}",
            color=discord.Color.orange()
        )
        return error_embed


def create_help_embed() -> discord.Embed:
    """
    Tworzy embed z informacją pomocy.

    Returns:
        discord.Embed: Embed z listą dostępnych komend
    """
    try:
        embed = discord.Embed(
            title="📋 Pomoc - Bot Jira",
            description="Lista dostępnych komend:",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="/refresh",
            value="Ręcznie odświeża listę bugów z Jiry",
            inline=False
        )

        embed.add_field(
            name="/setbugschannel [kanał]",
            value="Ustawia kanał do wyświetlania bugów (tylko dla administratorów)",
            inline=False
        )

        embed.add_field(
            name="/setreportschannel [kanał]",
            value="Ustawia kanał do wysyłania raportów (tylko dla administratorów)",
            inline=False
        )

        embed.add_field(
            name="/setinterval [minuty]",
            value="Ustawia interwał aktualizacji bugów w minutach (tylko dla administratorów)",
            inline=False
        )

        embed.add_field(
            name="/generate_report",
            value="Generuje raport ukończonych zadań na żądanie",
            inline=False
        )

        embed.add_field(
            name="/help",
            value="Wyświetla tę pomoc",
            inline=False
        )

        return embed
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia embeda pomocy: {e}")
        logger.error(traceback.format_exc())
        # Utworzenie prostego embeda w przypadku błędu
        error_embed = discord.Embed(
            title="⚠️ Błąd",
            description=f"Wystąpił błąd podczas generowania pomocy: {str(e)}",
            color=discord.Color.orange()
        )
        return error_embed


def create_error_embed(title: str, description: str) -> discord.Embed:
    """
    Tworzy embed z informacją o błędzie.

    Args:
        title (str): Tytuł embeda
        description (str): Opis błędu

    Returns:
        discord.Embed: Embed z informacją o błędzie
    """
    try:
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=discord.Color.orange()
        )
        return embed
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia embeda błędu: {e}")
        # Utworzenie podstawowego embeda błędu w przypadku, gdy nie uda się utworzyć bardziej szczegółowego
        return discord.Embed(
            title="⚠️ Błąd",
            description="Wystąpił nieoczekiwany błąd",
            color=discord.Color.red()
        )