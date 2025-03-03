# jira_client.py
import logging
import os
import traceback
from typing import List

from jira import JIRA
from jira.resources import Issue

logger = logging.getLogger('WielkiInkwizytorFilipa')


def get_jira_client() -> JIRA:
    """
    Inicjalizuje i zwraca klienta JIRA.

    Returns:
        JIRA: Klient Jira API

    Raises:
        Exception: W przypadku problemów z połączeniem
    """
    try:
        # Bezpośredni dostęp do zmiennych środowiskowych przez os.environ
        jira_server = os.environ.get('JIRA_SERVER')
        jira_username = os.environ.get('JIRA_USERNAME')
        jira_api_token = os.environ.get('JIRA_API_TOKEN')

        # Wypisz zmienne dla diagnostyki
        logger.info(f"Zmienne w get_jira_client: SERVER={jira_server}, USERNAME={jira_username}")

        missing_vars = []
        if not jira_server:
            missing_vars.append("JIRA_SERVER")
        if not jira_username:
            missing_vars.append("JIRA_USERNAME")
        if not jira_api_token:
            missing_vars.append("JIRA_API_TOKEN")

        if missing_vars:
            error_msg = f"Brak wymaganych zmiennych środowiskowych Jira: {', '.join(missing_vars)}. Sprawdź plik .env."
            logger.error(error_msg)
            raise ValueError(error_msg)

        client = JIRA(jira_server, basic_auth=(jira_username, jira_api_token))
        return client
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji klienta Jira: {e}")
        logger.error(traceback.format_exc())
        raise


async def fetch_jira_bugs() -> List[Issue]:
    """
    Pobiera listę bugów z Jiry.

    Returns:
        List[Issue]: Lista obiektów Issue z Jiry
    """
    try:
        # Wartości bezpośrednio z os.environ
        jira_project = os.environ.get('JIRA_PROJECT')
        jira_bug_query = os.environ.get('JIRA_BUG_QUERY')

        jira = get_jira_client()

        # Jeśli zdefiniowano własne zapytanie JQL w .env, użyj go
        if jira_bug_query:
            logger.info(f"Używanie niestandardowego zapytania JQL z pliku .env: {jira_bug_query}")
            issues = jira.search_issues(jira_bug_query, maxResults=100)
            logger.info(f"Pobrano {len(issues)} bugów używając niestandardowego zapytania")
            return issues

        # Sprawdź czy zdefiniowano JIRA_PROJECT
        if not jira_project:
            logger.error("Brak zdefiniowanej zmiennej JIRA_PROJECT w pliku .env")
            return []

        # W przeciwnym razie pobierz tylko aktywne bugi (niezakończone)
        active_bugs_jql = f'project = "{jira_project}" AND issuetype = Bug AND status NOT IN ("Done", "Resolved", "Closed") ORDER BY status ASC, priority DESC'

        logger.info(f"Pobieranie aktywnych bugów dla projektu {jira_project}")
        try:
            active_bugs = jira.search_issues(active_bugs_jql, maxResults=100)
            logger.info(f"Pobrano {len(active_bugs)} aktywnych bugów")
            return active_bugs
        except Exception as search_error:
            logger.error(f"Błąd podczas wyszukiwania bugów: {search_error}")
            logger.error(traceback.format_exc())
            # Próba wykonania prostszego zapytania w przypadku błędu
            fallback_jql = f'project = "{jira_project}" AND issuetype = Bug'
            logger.info(f"Próba wykonania zapytania awaryjnego: {fallback_jql}")
            return jira.search_issues(fallback_jql, maxResults=50)

    except Exception as e:
        logger.error(f"Błąd podczas pobierania bugów z Jiry: {e}")
        logger.error(traceback.format_exc())
        return []


async def get_active_sprints() -> List[dict]:
    """
    Pobiera listę aktywnych sprintów dla projektu.

    Returns:
        List[dict]: Lista aktywnych sprintów
    """
    try:
        jira_project = os.environ.get('JIRA_PROJECT')
        jira = get_jira_client()
        boards = jira.boards(projectKeyOrID=jira_project)

        active_sprints = []
        for board in boards:
            try:
                sprints = jira.sprints(board.id, state='active')
                for sprint in sprints:
                    active_sprints.append({
                        'id': sprint.id,
                        'name': sprint.name,
                        'board_id': board.id,
                        'board_name': board.name
                    })
            except Exception as sprint_error:
                logger.warning(f"Nie można pobrać sprintów dla tablicy {board.name} (ID: {board.id}): {sprint_error}")
                continue

        return active_sprints
    except Exception as e:
        logger.error(f"Błąd podczas pobierania aktywnych sprintów: {e}")
        logger.error(traceback.format_exc())
        return []


async def get_completed_tasks_for_report(start_date: str, end_date: str) -> List[Issue]:
    """
    Pobiera zadania zakończone w określonym przedziale czasowym.

    Args:
        start_date (str): Data początkowa w formacie "YYYY-MM-DD HH:MM"
        end_date (str): Data końcowa w formacie "YYYY-MM-DD HH:MM"

    Returns:
        List[Issue]: Lista zakończonych zadań
    """
    try:
        jira_project = os.environ.get('JIRA_PROJECT')
        jira = get_jira_client()

        # Formatowanie dat dla zapytania JQL
        jql_query = (
            f'project = "{jira_project}" '
            f'AND status changed to Done '
            f'AFTER "{start_date}" '
            f'AND status changed to Done BEFORE "{end_date}"'
        )

        logger.info(f"Pobieranie zadań zakończonych w okresie: {start_date} - {end_date}")
        tasks = jira.search_issues(jql_query, maxResults=1000)
        logger.info(f"Pobrano {len(tasks)} zakończonych zadań")

        return tasks
    except Exception as e:
        logger.error(f"Błąd podczas pobierania zakończonych zadań: {e}")
        logger.error(traceback.format_exc())
        return []
