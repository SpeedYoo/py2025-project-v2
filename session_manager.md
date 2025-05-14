## Specyfikacja modułu: Operacje na plikach i serializacja

### 1. Cel modułu
Moduł ma umożliwić:
- Zapis wyników rozgrywki, logów oraz historii gier do plików (CSV, JSON).
- Odczyt i zapis konfiguracji gry (np. ustawienia poziomu trudności, parametrów początkowych rozgrywki).

### 2. Założenia
- Pliki wyników i historii będą przechowywane w katalogu `data/`.
- Konfiguracja gry w pliku `config.json`.
- Użycie standardowych bibliotek Pythona (`json`, `csv`).
- Interfejs modułu musi być prosty do wykorzystania w silniku gry.

### 3. Wymagania funkcjonalne
1. **Zapis i odczyt sesji gry**
   - `save_session(session: dict) -> None`:
     - Zapisuje stan gry wraz z historią zakończonych rozdań do pliku `session_<game_id>.json` lub jako kolejne wpisy JSON-Lines.
     - Możliwość wznowienia wyłącznie po zakończonej rundzie — w sesji zapisujemy tylko pełne rozgrywki rąk.
   - `load_session(game_id: str) -> dict`:
     - Odczytuje plik sesji i zwraca pełny stan gry (stos każdego gracza, aktualne blindy oraz listę zakończonych rozdań), umożliwiając kontynuację rozgrywki.

 **Uwaga**: Aby uniknąć wycieku kart w trakcie rundy, zapisy sesji są możliwe wyłącznie po zakończeniu rundy (rozstrzygnięciu rozdania).

#### Historia rozdań

Należy **przemyśleć**, opracować, zaimplememntować i przetestować sposób zapisywania rozegranego rozdania do pliku (tak aby umożliwić odczytanie i odtworzenie jego przebiegu oraz potencjalną analizę. Szkielet
struktury danych mógłby wyglądać następująco (należy rozważyć dodanie dodatkowych pól lub modyfikację proponowanych):

```json
{
  "game_id": "<unikalny_id>",
  "timestamp": "<ISO-8601>",
  "stage": "<aktualny_etap>",
  "players": [
    {"id": 1, "name": "<nick>", "stack": <liczba>},
    {"id": 2, "name": "<nick>", "stack": <liczba>},
    ...
  ],
  "deck": ["<lista_kart_w_dealującej_kolejności>"],
  "hands": {
    "1": ["<karta>", ...],
    "2": ["<karta>", ...]
  },
  "bets": [
    {"stage": "<etap>", "player_id": <id>, "action": "<akcja>", "amount": <kwota>, "pot": <kwota>},
    ...
  ],
  "current_player": <id>,
  "pot": <kwota>,
  ... // inne pola według potrzeb (np. discards, drawn, itp.)
}

```

### 4. Wymagania niefunkcjonalne
- Jedna klasa `SessionManager` z dwoma metodami: `save_session` i `load_session`.
- Prosty, klarowny format JSON lub JSON-Lines. Można rozważyć wykorzystanie CSV i połączenie go z JSON.
- Obsługa błędów I/O (wyjątki przy zapisie/odczycie).

### 5. Projekt API
```python
class SessionManager:
    def __init__(self, data_dir: str = 'data'):
        """Inicjalizuje katalog, w którym przechowywane będą pliki sesji."""

    def save_session(self, session: dict) -> None:
        """Zapisuje stan gry i historię zakończonych rozdań do pliku."""

    def load_session(self, game_id: str) -> dict:
        """Ładuje sesję gry z pliku i zwraca strukturę pozwalającą na kontynuację rozgrywki."""
```

### 6. Struktura katalogów
```
project-root/
├── data/                   # katalog na pliki sesji: session_<game_id>.json
├── src/
│   └── fileops/
│       └── session_manager.py  # klasa SessionManager
├── config.json
└── tests/
    └── test_session_manager.py # opcjonalne aczkolwiek zalecane testy jednostkowe SessionManager
```
