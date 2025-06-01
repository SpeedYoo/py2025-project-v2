import random
from typing import List, Dict, Tuple, Optional

from src.card import Card
from src.player import Player
from src.deck import Deck
from src.hand_rank import handRank


class InvalidActionError(Exception):
    """Wyrzucane przy nieprawidłowej akcji gracza."""
    pass


class InsufficientFundsError(Exception):
    """Wyrzucane, gdy gracz nie ma środków na raise lub blindy."""
    pass


class GameEngine:
    """Silnik gry pokerowej, zarządza przebiegiem rozgrywki."""

    def __init__(self, players: List[Player], deck: Deck,
                 small_blind: int = 25, big_blind: int = 50):
        self.players = players
        self.deck = deck
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.pot = 0
        self.dealer_idx = 0
        self.hand_evaluator = handRank()

    def play_round(self) -> None:
        """Rozgrywa jedną rundę pokera."""
        n = len(self.players)
        if n < 2:
            print("Za mało graczy do rozpoczęcia rundy")
            return

        sb_idx = (self.dealer_idx + 1) % n
        bb_idx = (self.dealer_idx + 2) % n

        # Przygotowanie rundy
        self.deck.shuffle()
        self.pot = 0
        for p in self.players:
            p.clear_hand()

        # Blindy
        sb = self.players[sb_idx]
        bb = self.players[bb_idx]

        try:
            sb_amt = min(self.small_blind, sb.get_stack_amount())
            bb_amt = min(self.big_blind, bb.get_stack_amount())

            if sb.get_stack_amount() < sb_amt or bb.get_stack_amount() < bb_amt:
                raise InsufficientFundsError("Brak środków na opłacenie blindów")

            self.pot += sb.remove_from_stack(sb_amt)
            self.pot += bb.remove_from_stack(bb_amt)

            print(f"Small blind: {sb.get_name()} płaci {sb_amt}")
            print(f"Big blind: {bb.get_name()} płaci {bb_amt}")
        except InsufficientFundsError as e:
            print(f"Błąd: {e}")
            return

        # Rozdanie kart
        self.deck.deal(self.players)
        for p in self.players:
            if not p.is_bot:
                print(f"{p.get_name()}, Twoje karty: {p.cards_to_str()}")

        # Runda zakładów
        contributions = {p: 0 for p in self.players}
        contributions[sb] = sb_amt
        contributions[bb] = bb_amt
        current_bet = bb_amt
        active = self._betting_round((bb_idx + 1) % n, contributions, current_bet)

        # Fold do jednego
        if len(active) == 1:
            winner = active[0]
            print(f"Zwycięzca (wszyscy spasowali): {winner.get_name()}, otrzymuje {self.pot} żetonów.")
            winner.add_to_stack(self.pot)
            self.dealer_idx = (self.dealer_idx + 1) % n
            self.pot = 0
            return

        # Wymiana kart
        for p in active:
            indices = []
            if p.is_bot:
                # bot losowo wymienia 0-3 kart
                num = random.randint(0, 3)
                indices = random.sample(range(5), num)
                print(f"{p.get_name()} (BOT) wymienia karty: {indices}")
            else:
                print(f"{p.get_name()}, Twoje karty: {p.cards_to_str()}")
                try:
                    idxs = input("Które karty wymienić? (0-4 sep. spacją, ENTER = brak): ")
                    indices = sorted({int(i) for i in idxs.split()}, reverse=True) if idxs.strip() else []
                    # Walidacja indeksów
                    for idx in indices:
                        if idx < 0 or idx > 4:
                            raise ValueError(f"Nieprawidłowy indeks karty: {idx}")
                except ValueError as e:
                    print(f"Błąd: {e}")
                    print("Pomijam wymianę kart")
                    indices = []

            try:
                new_hand = self.exchange_cards(p.get_player_hand(), indices)
                for i, card in enumerate(new_hand):
                    p.change_card(card, i)
                if not p.is_bot:
                    print(f"Nowe karty: {p.cards_to_str()}")
            except (ValueError, IndexError) as e:
                print(f"Błąd przy wymianie kart: {e}, pomijam.")

        # Druga runda zakładów
        # current_bet = 0
        # contributions = {p: 0 for p in active}
        # active = self._betting_round(self.dealer_idx % len(active), contributions, current_bet)

        # Fold do jednego
        if len(active) == 1:
            winner = active[0]
            print(f"Zwycięzca (wszyscy spasowali): {winner.get_name()}, otrzymuje {self.pot} żetonów.")
            winner.add_to_stack(self.pot)
            self.dealer_idx = (self.dealer_idx + 1) % n
            self.pot = 0
            return

        # Showdown
        winner = self.showdown(active)
        print(f"\nZwycięzca: {winner.get_name()}, otrzymuje {self.pot} żetonów.")
        winner.add_to_stack(self.pot)
        self.pot = 0
        self.dealer_idx = (self.dealer_idx + 1) % n

    def prompt_bet(self, player: Player, current_bet: int, contributed: int) -> str:
        to_call = current_bet - contributed

        # Dla botów generujemy losową akcję
        if player.is_bot:
            if to_call > 0:
                if random.random() < 0.7:  # 70% szansa na call
                    action = 'call'
                else:
                    action = 'fold'
            else:
                if random.random() < 0.3:  # 30% szansa na raise
                    raise_amount = random.randint(1, min(50, player.get_stack_amount()))
                    action = f'raise {raise_amount}'
                else:
                    action = 'check'
            print(f"{player.get_name()} (BOT) wykonuje: {action}")
            return action

        # Dla graczy człowieków wyświetlamy menu
        valid_actions = []
        action_menu = []

        if to_call == 0:
            valid_actions.append('check')
            action_menu.append("[c]heck")
        else:
            valid_actions.append('call')
            action_menu.append(f"[c]all {to_call}")

        valid_actions.append('fold')
        action_menu.append("[f]old")

        if player.get_stack_amount() > to_call:
            valid_actions.append('raise')
            action_menu.append("[r]aise <amount>")

        # Monitorowanie błędnych inputów
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            try:
                action = input(
                    f"\n{player.get_name()} (Stack: {player.get_stack_amount()}, Pot: {self.pot}, "
                    f"postawił: {contributed}, do wyrównania: {to_call})\n"
                    f"Dostępne akcje: {' / '.join(action_menu)}: "
                ).strip().lower()

                # Obsługa skrótów
                if action == 'c' and 'call' in valid_actions:
                    return 'call'
                elif action == 'c' and 'check' in valid_actions:
                    return 'check'
                elif action == 'f':
                    return 'fold'
                elif action.startswith('r ') or action.startswith('raise '):
                    parts = action.split()
                    if len(parts) == 2 and parts[1].isdigit():
                        raise_amount = int(parts[1])
                        if raise_amount <= 0:
                            print("Kwota raise musi być dodatnia")
                        elif raise_amount > player.get_stack_amount() - to_call:
                            print(f"Nie masz tyle żetonów (max {player.get_stack_amount() - to_call})")
                        else:
                            return f"raise {raise_amount}"
                    else:
                        print("Niepoprawny format dla raise. Użyj 'raise <amount>'")
                else:
                    cmd = action.split()
                    if len(cmd) > 0 and cmd[0] in valid_actions:
                        if cmd[0] == 'raise' and len(cmd) == 2 and cmd[1].isdigit():
                            raise_amount = int(cmd[1])
                            if raise_amount <= 0:
                                print("Kwota raise musi być dodatnia")
                            elif raise_amount > player.get_stack_amount() - to_call:
                                print(f"Nie masz tyle żetonów (max {player.get_stack_amount() - to_call})")
                            else:
                                return action
                        elif cmd[0] != 'raise':
                            return cmd[0]

                print("Nieprawidłowa akcja, spróbuj ponownie")
                attempts += 1
            except Exception as e:
                print(f"Błąd: {e}")
                attempts += 1

        # Po wyczerpaniu prób, domyślnie fold
        print("Zbyt wiele błędnych prób, wykonuję fold")
        return 'fold'

    def _betting_round(self, start: int, contributions: dict, current_bet: int) -> List[Player]:
        active = list(self.players)
        idx = start
        seen = set()

        print(f"\n=== RUNDA LICYTACJI (stawka: {current_bet}) ===")

        while True:
            player = self.players[idx]
            if player in active:
                contributed = contributions.get(player, 0)

                try:
                    action = self.prompt_bet(player, current_bet, contributed)
                    cmd = action.split()

                    if cmd[0] == 'fold':
                        active.remove(player)
                        print(f"{player.get_name()} pasuje")
                    elif cmd[0] == 'check' and current_bet == contributed:
                        print(f"{player.get_name()} czeka")
                    elif cmd[0] == 'call':
                        to_call = current_bet - contributed
                        amt = min(to_call, player.get_stack_amount())
                        player.remove_from_stack(amt)
                        contributions[player] = contributed + amt
                        self.pot += amt
                        print(f"{player.get_name()} wyrównuje do {current_bet} ({amt})")
                    elif cmd[0] == 'raise' and len(cmd) == 2 and cmd[1].isdigit():
                        raise_amount = int(cmd[1])
                        to_call = current_bet - contributed
                        total_pay = to_call + raise_amount
                        player.remove_from_stack(total_pay)
                        contributions[player] = contributed + total_pay
                        self.pot += total_pay
                        current_bet += raise_amount
                        seen = {player}  # Reset seen po raise
                        print(f"{player.get_name()} podbija o {raise_amount} do {current_bet}")
                    else:
                        raise InvalidActionError(f"Nieprawidłowa akcja: {action}")

                    seen.add(player)

                    # Warunki zakończenia rundy licytacji
                    if len(active) <= 1:
                        return active

                    all_called = all(player not in active or contributions.get(player, 0) == current_bet
                                     for player in self.players)
                    all_had_chance = seen.issuperset(active)

                    if all_called and all_had_chance:
                        return active
                except (InvalidActionError, ValueError) as e:
                    print(f"Błąd: {e}")
                    # W przypadku błędu, domyślnie fold
                    if player in active:
                        active.remove(player)
                        print(f"{player.get_name()} pasuje (domyślnie)")

            idx = (idx + 1) % len(self.players)

    def showdown(self, active_players: List[Player] = None) -> Player:
        if active_players is None:
            active_players = self.players

        if not active_players:
            raise ValueError("Brak aktywnych graczy do showdown")

        # Przygotowanie informacji o układach graczy
        showdown_info = []
        for p in active_players:
            hand = p.get_player_hand()
            rank_id, tiebreak = self.hand_evaluator.get_hand_strength(list(hand))
            strength = (rank_id, tiebreak)
            hand_name = self.hand_evaluator.HAND_RANKINGS[rank_id]
            showdown_info.append((p, p.get_name(), hand_name, strength, p.cards_to_str()))

        # Wyświetlenie tabeli z układami
        print("\n=== SHOWDOWN ===")
        print(f"{'Gracz':<15} | {'Układ':<17} | {'Siła':<20} | Karty")
        print('-' * 70)
        for _, name, rank, strength, cards in showdown_info:
            print(f"{name:<15} | {rank:<17} | {str(strength):<20} | {cards}")

        # Wyłonienie zwycięzcy na podstawie siły układu
        winner = max(active_players,
                     key=lambda p: self.hand_evaluator.get_hand_strength(list(p.get_player_hand())))
        win_rank_id = self.hand_evaluator.get_hand_strength(list(winner.get_player_hand()))[0]
        win_rank_name = self.hand_evaluator.HAND_RANKINGS[win_rank_id]

        return winner

    def exchange_cards(self, hand: Tuple[Card], indices: List[int]) -> List[Card]:
        # Konwersja krotki na listę do modyfikacji
        new_hand = list(hand)

        # Walidacja indeksów
        for i in indices:
            if i < 0 or i >= len(hand):
                raise IndexError(f"Nieprawidłowy indeks karty: {i}")

        # Wymiana kart
        for i in indices:
            old = new_hand[i]
            try:
                new = self.deck.cards.pop()
                new_hand[i] = new
                # Odłożenie starej karty do spodu talii
                self.deck.cards.insert(0, old)
            except IndexError:
                raise IndexError("Brak kart w talii do wymiany")

        return new_hand