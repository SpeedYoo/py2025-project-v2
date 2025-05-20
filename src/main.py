import uuid
import os
import platform
from typing import List

from src.deck import Deck
from src.game_engine import GameEngine
from src.player import Player

def get_player_count():
    while True:
        try:
            count = input("Podaj liczbę graczy (2-6): ")
            count = int(count)
            if 2 <= count <= 6:
                return count
            print("Liczba graczy musi być między 2 a 6.")
        except ValueError:
            print("Podaj poprawną liczbę.")


def setup_players(player_count: int) -> List[Player]:
    players = []

    for i in range(player_count):
        while True:
            name = input(f"Podaj nazwę gracza {i + 1} (lub 'bot' dla komputera): ").strip()
            if not name:
                print("Nazwa nie może być pusta.")
                continue

            # Sprawdzenie czy nazwa jest unikalna
            if any(p.get_name() == name for p in players):
                print("Ta nazwa jest już zajęta.")
                continue

            break

        is_bot = name.lower() == 'bot'
        if is_bot:
            name = f"Bot_{i + 1}"

        while True:
            try:
                money = input(f"Początkowa ilość żetonów dla {name} (50-5000): ")
                money = int(money)
                if 50 <= money <= 5000:
                    break
                print("Ilość żetonów musi być między 50 a 5000.")
            except ValueError:
                print("Podaj poprawną kwotę.")

        players.append(Player(money, name, is_bot))

    return players


def setup_game():
    # Ustawienia początkowe gry
    print("GRA POKER")
    player_count = get_player_count()
    players = setup_players(player_count)

    # Konfiguracja blindów
    while True:
        try:
            small_blind = input("Podaj wartość małej ciemnej (domyślnie 25): ")
            small_blind = int(small_blind) if small_blind.strip() else 25

            big_blind = input(f"Podaj wartość dużej ciemnej (domyślnie {small_blind * 2}): ")
            big_blind = int(big_blind) if big_blind.strip() else small_blind * 2

            if small_blind <= 0 or big_blind <= 0:
                print("Wartości muszą być dodatnie.")
                continue

            if small_blind >= big_blind:
                print("Duża ciemna musi być większa od małej ciemnej.")
                continue

            break
        except ValueError:
            print("Podaj poprawne wartości.")

    deck = Deck()
    engine = GameEngine(players, deck, small_blind, big_blind)

    return engine

def main():
    engine = setup_game()
    players = engine.players

    round_number = 1

    while len(players) >= 2:
        print(f"\nRUNDA {round_number}")

        print("\nGracze:")
        for i, p in enumerate(players):
            dealer_mark = " (D)" if i == engine.dealer_idx else ""
            bot_mark = " [BOT]" if p.is_bot else ""
            print(f"{p.get_name()}{dealer_mark}{bot_mark}: {p.get_stack_amount()} żetonów")

        try:
            engine.play_round() # rozpoczęcie rundy
        except Exception as e:
            print(f"Błąd podczas rozgrywania rundy: {e}")
            input("\nNaciśnij ENTER, aby kontynuować...")
            continue

        # Sprawdzenie czy gracze chcą kontynuować
        next_round = []
        print("\nDecyzje o pozostaniu w grze:")

        for p in players:
            if p.get_stack_amount() <= 0:
                print(f"{p.get_name()} nie ma już żetonów i odpada z gry.")
                continue

            if p.is_bot:
                # Bot zostaje w grze dopóki ma żetony
                print(f"{p.get_name()} (BOT) zostaje w grze.")
                next_round.append(p)
            else:
                while True:
                    cont = input(
                        f"{p.get_name()} ({p.get_stack_amount()} żetonów), czy chcesz grać dalej? (t/n): ").strip().lower()
                    if cont in ['t', 'n']:
                        break
                    print("Podaj t lub n.")

                if cont == 't':
                    next_round.append(p)
                else:
                    print(f"{p.get_name()} odchodzi z gry.")

        players = next_round
        engine.players = players

        if len(players) < 2:
            print("Za mało graczy, koniec gry.")
            break

        round_number += 1
        input("\nNaciśnij ENTER, aby rozpocząć nową rundę...")

    print("\nKONIEC GRY")

    if players:
        print("\nPozostali gracze:")
        for p in players:
            print(f"{p.get_name()}: {p.get_stack_amount()} żetonów")

    print("\nDziękujemy za grę!")


if __name__ == "__main__":
    main()