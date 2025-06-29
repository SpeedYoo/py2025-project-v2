import uuid
import os
import platform
from typing import List, Dict, Optional

from src.deck import Deck
from src.game_engine import GameEngine
from src.player import Player
from src.fileops.session_manager import SessionManager, serialize_player, create_round_summary


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


def setup_blinds() -> tuple:
    """Konfiguracja wartości blindów"""
    while True:
        try:
            small_blind = input("Podaj wartość small blind (domyślnie 25): ")
            small_blind = int(small_blind) if small_blind.strip() else 25

            big_blind = input(f"Podaj wartość big blind (domyślnie {small_blind * 2}): ")
            big_blind = int(big_blind) if big_blind.strip() else small_blind * 2

            if small_blind <= 0 or big_blind <= 0:
                print("Wartości muszą być dodatnie.")
                continue

            if small_blind >= big_blind:
                print("Duża ciemna musi być większa od małej ciemnej.")
                continue

            return small_blind, big_blind
        except ValueError:
            print("Podaj poprawne wartości.")


def setup_new_game():
    """Ustawienia początkowe nowej gry"""
    print("GRA POKER - NOWA GRA")
    player_count = get_player_count()
    players = setup_players(player_count)
    small_blind, big_blind = setup_blinds()

    deck = Deck()
    engine = GameEngine(players, deck, small_blind, big_blind)

    game_id = str(uuid.uuid4())

    return engine, game_id


def load_existing_game(session_manager: SessionManager):
    """Wczytanie istniejącej sesji gry"""
    print("GRA POKER - WCZYTAJ GRĘ")

    sessions = session_manager.list_sessions()

    if not sessions:
        print("Nie znaleziono zapisanych sesji gry.")
        return None, None

    print("\nDostępne sesje gry:")
    for i, session in enumerate(sessions):
        players_str = ", ".join(session['players'])
        print(f"{i + 1}. {session['timestamp']} - Gracze: {players_str} - Rund: {session['rounds_played']}")

    while True:
        try:
            choice = input("\nWybierz numer sesji do wczytania (lub 0, aby anulować): ")
            choice = int(choice)

            if choice == 0:
                return None, None

            if 1 <= choice <= len(sessions):
                selected_session = sessions[choice - 1]
                game_id = selected_session['game_id']

                try:
                    session_data = session_manager.load_session(game_id)

                    players = []
                    for p_data in session_data['players']:
                        player = Player(p_data['stack'], p_data['name'], p_data.get('is_bot', False))
                        players.append(player)

                    deck = Deck()
                    engine = GameEngine(
                        players,
                        deck,
                        session_data.get('small_blind', 25),
                        session_data.get('big_blind', 50)
                    )

                    engine.dealer_idx = session_data.get('dealer_idx', 0)

                    print(f"Wczytano sesję gry z {session_data['timestamp']}")
                    return engine, game_id

                except Exception as e:
                    print(f"Błąd podczas wczytywania sesji: {e}")
                    continue

            print("Nieprawidłowy wybór.")
        except ValueError:
            print("Podaj poprawny numer.")


def save_game_state(engine: GameEngine, game_id: str, round_number: int, session_manager: SessionManager,
                    rounds_history: list):
    """Zapisuje stan gry do pliku sesji"""

    players_data = [serialize_player(player) for player in engine.players]

    session_data = {
        'game_id': game_id,
        'small_blind': engine.small_blind,
        'big_blind': engine.big_blind,
        'dealer_idx': engine.dealer_idx,
        'round_number': round_number,
        'players': players_data,
        'rounds_history': rounds_history
    }

    try:
        session_manager.save_session(session_data)
        print(f"Stan gry został zapisany. ID sesji: {game_id}")
        return True
    except Exception as e:
        print(f"Błąd podczas zapisywania stanu gry: {e}")
        return False


def main():
    session_manager = SessionManager("../data")

    # Menu główne
    print("=" * 50)
    print("POKER - MENU GŁÓWNE")
    print("=" * 50)
    print("1. Nowa gra")
    print("2. Wczytaj grę")
    print("0. Wyjście")

    choice = input("Wybierz opcję: ")

    engine = None
    game_id = None

    if choice == "1":
        engine, game_id = setup_new_game()
    elif choice == "2":
        engine, game_id = load_existing_game(session_manager)
        if engine is None:
            print("Anulowano wczytywanie gry.")
            return
    elif choice == "0":
        print("Dziękujemy za grę!")
        return
    else:
        print("Nieprawidłowy wybór.")
        return

    players = engine.players
    round_number = 1
    rounds_history = []

    if choice == "2":
        session_data = session_manager.load_session(game_id)
        rounds_history = session_data.get('rounds_history', [])
        round_number = session_data.get('round_number', 1)

    while len(players) >= 2:
        print(f"\nRUNDA {round_number}")

        print("\nGracze:")
        for i, p in enumerate(players):
            dealer_mark = " (D)" if i == engine.dealer_idx else ""
            bot_mark = " [BOT]" if p.is_bot else ""
            print(f"{p.get_name()}{dealer_mark}{bot_mark}: {p.get_stack_amount()} żetonów")

        try:
            round_actions = []

            original_prompt_bet = engine.prompt_bet

            def prompt_bet_with_logging(player, current_bet, contributed):
                action = original_prompt_bet(player, current_bet, contributed)
                # Zapisz akcję
                round_actions.append({
                    'player': player.get_name(),
                    'action': action,
                    'current_bet': current_bet,
                    'contributed': contributed,
                    'stack_before': player.get_stack_amount() + (current_bet - contributed if 'call' in action else 0)
                })
                return action

            engine.prompt_bet = prompt_bet_with_logging

            engine.play_round()

            engine.prompt_bet = original_prompt_bet

            round_summary = create_round_summary(engine, round_number, round_actions)
            rounds_history.append(round_summary)

            is_save = input("Czy chcesz zapisać stan gry ?  (t/n): ")
            if is_save == "t" : save_game_state(engine, game_id, round_number + 1, session_manager, rounds_history)


        except Exception as e:
            print(f"Błąd podczas rozgrywania rundy: {e}")
            input("\nNaciśnij ENTER, aby kontynuować...")
            continue

        next_round = []
        print("\nDecyzje o pozostaniu w grze:")

        for p in players:
            if p.get_stack_amount() <= 0:
                print(f"{p.get_name()} nie ma już żetonów i odpada z gry.")
                continue

            if p.is_bot:
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

        # Menu po rundzie
        print("\nOpcje:")
        print("1. Kontynuuj grę")
        print("2. Zapisz i wyjdź")
        menu_choice = input("Wybierz opcję: ").strip()

        if menu_choice == "2":
            # Zapisz grę i zakończ
            save_game_state(engine, game_id, round_number + 1, session_manager, rounds_history)
            print("Gra została zapisana. Dziękujemy za grę!")
            return

        round_number += 1

    print("\nKONIEC GRY")

    if players:
        print("\nPozostali gracze:")
        for p in players:
            print(f"{p.get_name()}: {p.get_stack_amount()} żetonów")

    print("\nDziękujemy za grę!")


if __name__ == "__main__":
    main()