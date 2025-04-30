# Specyfikacja modułu „Rozgrywka”

## 1. Klasa `GameEngine`

```python
class GameEngine:
    def __init__(self, players: List[Player], deck: Deck,
                 small_blind: int = 25, big_blind: int = 50):
        """Inicjalizuje graczy, talię, blindy i pulę."""
    
    def play_round(self) -> None:
        """Przeprowadza jedną rundę:
           1. Pobiera blindy
           2. Rozdaje karty
           3. Rundę zakładów
           4. Wymianę kart
           5. Showdown i przyznanie puli
        """
    
    def prompt_bet(self, player: Player, current_bet: int) -> str:
        """Pobiera akcję od gracza (human lub bot) — check/call/raise/fold."""
    
    def exchange_cards(self, hand: List[Card], indices: List[int]) -> List[Card]:
        """Wymienia wskazane karty z ręki gracza, wkłada stare na spód talii."""
    
    def showdown(self) -> Player:
        """Porównuje układy pozostałych graczy i zwraca zwycięzcę."""
```

## 2. Przebieg rundy (`play_round`)

1. **Blindy**  
   - Każdy gracz płaci small blind lub big blind; żetony trafiają do `pot`.

2. **Rozdanie kart**  
   - `deck.shuffle()`  
   - `deck.deal(players, 5)`  
   - Gracz widzi tylko swoją rękę:
     ```python
     print("Twoje karty:", player.cards_to_str())
     ```

3. **Runda zakładów**  
   - Dla każdego aktywnego gracza w kolejności:
     ```python
     action = prompt_bet(player, current_bet)
     ```
   - Aktualizuj `player.stack`, `pot`, `current_bet`.  
   - Kończy się, gdy wszyscy wyrównają stawki lub spasują.

4. **Wymiana kart**  
   - Dla każdego gracza:
     - **Human**: wpisuje indeksy do wymiany; weryfikacja `ValueError`/`IndexError`  
     - **Bot**: wybiera według prostej reguły lub losowo  
     - Wywołanie:
       ```python
       player.hand = exchange_cards(player.hand, indices)
       ```

5. **Showdown**  
   - `winner = showdown()`  
   - `winner.stack += pot`  
   - Wyświetl wynik:
     ```text
     Zwycięzca: Gracz X, otrzymuje Y żetonów.
     ```

## 3. Obsługa wejścia i wyjątków

- **Wejście z klawiatury**: zawsze w `try/except ValueError`  
- **Nieprawidłowa akcja**: `raise InvalidActionError`  
- **Brak środków** przy `raise`: `raise InsufficientFundsError`  
- **IndexError** w `exchange_cards`, gdy `idx not in [0–4]`

## 4. Funkcja pomocnicza `exchange_cards`

```python
def exchange_cards(self,
                   hand: List[Card],
                   indices: List[int]
                  ) -> List[Card]:
    """
    hand     – 5 kart gracza
    indices  – lista indeksów (0–4) do wymiany
    Zwraca: nową listę 5 kart.
    Stare karty odkłada na spód talii.
    """
```

- **Błędy**:  
  - `IndexError` jeśli któryś `idx ∉ [0,4]`  

- **Działanie**:  
  1. `new_cards = [deck.draw() for _ in indices]`  
  2. Zamiana i `deck.discard_to_bottom(old_card)`  
  3. Zwrócenie zaktualizowanej ręki
