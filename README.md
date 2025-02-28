# Bot Discord/Jira

Bot Discord integrujący informacje o bugach i zadaniach z Jira. Bot wyświetla aktualną listę bugów, a także generuje dzienne raporty z ukończonych zadań.

## Główne funkcje

- **Śledzenie bugów**: Automatyczne pobieranie i wyświetlanie listy aktywnych bugów z Jira
- **Dzienne raporty**: Automatyczne generowanie dziennych raportów z ukończonych zadań
- **Komendy slash**: Łatwe zarządzanie botem poprzez komendy slash w Discord

## Struktura projektu

- `main.py` - Główny plik uruchomieniowy
- `bot_config.py` - Konfiguracja bota
- `jira_client.py` - Klient Jira
- `discord_embeds.py` - Generator embedów Discord
- `message_updater.py` - Aktualizator wiadomości z bugami
- `commands.py` - Komendy slash bota
- `tasks.py` - Zadania okresowe bota
- `reports.py` - Moduł raportów
- `.env` - Plik konfiguracyjny (skopiuj z `.env.example`)

## Wymagania

- Python 3.8 lub nowszy
- Pakiety wymienione w `requirements.txt`
- Token bota Discord
- Dostęp do Jira (URL, nazwa użytkownika, token API)

## Instalacja

1. Sklonuj repozytorium
2. Utwórz wirtualne środowisko Python:
   ```
   python -m venv .venv
   ```
3. Aktywuj wirtualne środowisko:
   - Windows: `.venv\Scripts\activate`
   - Linux/MacOS: `source .venv/bin/activate`
4. Zainstaluj wymagane pakiety:
   ```
   pip install -r requirements.txt
   ```
5. Skopiuj `.env.example` do `.env` i uzupełnij wszystkie wymagane wartości
6. Uruchom bota:
   ```
   python main.py
   ```

## Konfiguracja

Bot konfigurowany jest poprzez plik `.env`. Najważniejsze ustawienia:

### Konfiguracja Discord
- `DISCORD_TOKEN` - Token bota Discord
- `DISCORD_GUILD_ID` - ID serwera Discord (opcjonalne)
- `DISCORD_BUGS_CHANNEL_ID` - ID kanału do wyświetlania bugów
- `DISCORD_REPORTS_CHANNEL_ID` - ID kanału do wysyłania raportów

### Konfiguracja Jira
- `JIRA_SERVER` - URL instancji Jira
- `JIRA_USERNAME` - Nazwa użytkownika/email do Jira
- `JIRA_API_TOKEN` - Token API Jira
- `JIRA_PROJECT` - Klucz projektu w Jira
- `JIRA_BUG_QUERY` - Własne zapytanie JQL (opcjonalne)

### Mapowanie nazw użytkowników
- `NAME_MAPPING` - Mapowanie pełnych nazw użytkowników na skrócone imiona.
  Format: `pełna_nazwa1:skrót1;pełna_nazwa2:skrót2`
  
  Przykład: `NAME_MAPPING=Filip Pocztarski:Filip;Jan Kowalski:Janek`

### Inne ustawienia
- `TIMEZONE` - Strefa czasowa (np. Europe/Warsaw)
- `UPDATE_INTERVAL` - Interwał aktualizacji bugów w sekundach
- `REPORT_HOUR` - Godzina wysyłania dziennego raportu (domyślnie 21)
- `REPORT_MINUTE` - Minuta wysyłania dziennego raportu (domyślnie 37)

## Komendy Discord

Bot obsługuje następujące komendy slash:

- `/refresh` - Ręcznie odświeża listę bugów z Jiry
- `/setbugschannel [kanał]` - Ustawia kanał do wyświetlania bugów
- `/setreportschannel [kanał]` - Ustawia kanał do wysyłania raportów
- `/setreportschannelid [id_kanału]` - Ustawia kanał raportów poprzez ID
- `/setinterval [minuty]` - Ustawia interwał aktualizacji bugów w minutach
- `/generate_report` - Generuje raport ukończonych zadań na żądanie
- `/help` - Wyświetla pomoc z listą dostępnych komend

## Logowanie

Bot loguje informacje o swoim działaniu do pliku `jira_discord_bot.log` oraz na konsolę. Poziom logowania można dostosować w pliku `main.py`.

## Rozwiązywanie problemów

- **Bot nie łączy się z Discord**: Sprawdź czy token Discord jest poprawny
- **Bot nie pobiera danych z Jira**: Sprawdź ustawienia serwera Jira, nazwę użytkownika i token API
- **Bot nie wyświetla bugów**: Sprawdź czy ID kanału jest poprawne i czy bot ma uprawnienia do wysyłania wiadomości
- **Bot pokazuje błąd podczas aktualizacji**: Sprawdź logi w celu zidentyfikowania problemu