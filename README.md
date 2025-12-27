# Discord Bot

#### Bot discordowy zbudowany w oparciu o architekturę modułową (Cogs)

## Funkcje
- **League of Legends**: Sprawdzanie rangi (`!rank`) oraz TOP 3 maestrii (`!mastery`) bezpośrednio z OP.GG. <br>
    Komendy działają jako tradycyjne prefix-commands (`!`) oraz nowoczesne Slash Commands (`/`).
- **Przypomnienia**: System osobistych powiadomień z interfejsem Modal (okno wprowadzania danych).
- **Narzędzia**: Rzut kostką, sprawdzanie awatara, powiązania nicków LoL z użytkownikami Discorda.

## Struktura
- `cogs/`: Logika komend podzielona na kategorie (General, League, Reminders).
- `database/`: Zarządzanie bazą danych SQLite.
- `utils/`: Silnik scrapujący dane z serwisów zewnętrznych.
- `data/`: Folder na bazę danych `reminder.db` oraz plik `gracze.json`.

## Instalacja na Linuxie 

1. **Klonowanie/pobranie repozytorium:**
   ```bash
   cd ~/
   # Skopiuj pliki bota do folderu discord_bot
   cd discord_bot
2. **Tworzenie środowiska wirtualnego**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
3. **Instalacja zależności**
    ```bash
    pip install -r requirements.txt
4. **Konfiguracja**
    ```bash
    Dodaj .env
    Dodaj token -> DISCORD_TOKEN=abcd_1234_def
5. **Uruchom**
    ```bash
    python3 main.py
6. **Logi**
    ```bash
    Bot loguje swoje działania w data/bot.log
    Mozna je podejrzeć przez:
        tail -f data/bot.log


### Jak utrzymać bota przy życiu?

Największym wyzwaniem jest to, żeby działał po zamknięciu sesji SSH. Najprostsze rozwiązanie: użycie narzędzia `screen`.
1. `screen -S bot`.
2. `python3 main.py`.
3. `Ctrl + A`, a pozniej `D`.

Bot będzie teraz działał w tle, nawet po wyjsciu z SSH.