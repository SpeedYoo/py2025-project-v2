import random
from typing import List, Tuple, Dict
from collections import Counter

from src.card import Card
from src.deck import Deck
from src.player import Player


class InvalidActionError(Exception):
    """Wyrzucane przy nieprawidłowej akcji gracza."""
    pass


class InsufficientFundsError(Exception):
    """Wyrzucane, gdy gracz nie ma środków na raise lub blindy."""
    pass


def hand_rank(hand: List[Card]) -> Tuple[int, List[int]]:
    values = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':11,'Q':12,'K':13,'A':14}
    ranks = sorted((values[c.rank] for c in hand), reverse=True)
    is_flush = len({c.suit for c in hand}) == 1
    uniq = sorted(set(ranks))
    if uniq == [2,3,4,5,14]: is_straight, high = True, 5
    elif len(uniq)==5 and uniq[0]+4==uniq[-1]: is_straight, high = True, uniq[-1]
    else: is_straight, high = False, ranks[0]
    cnt = Counter(ranks).most_common()
    counts = sorted([c for _,c in cnt], reverse=True)
    if is_straight and is_flush: return 9, [high]
    if counts[0]==4:
        four = cnt[0][0]
        kicker = [r for r in ranks if r!=four][0]
        return 8, [four,kicker]
    if counts[0]==3 and counts[1]==2:
        return 7, [cnt[0][0], cnt[1][0]]
    if is_flush: return 6, ranks
    if is_straight: return 5, [high]
    if counts[0]==3:
        three = cnt[0][0]
        kicks = sorted([r for r in ranks if r!=three], reverse=True)
        return 4, [three]+kicks
    if counts[0]==2 and counts[1]==2:
        pairs = sorted([r for r,c in cnt if c==2], reverse=True)
        kicker = [r for r in ranks if r not in pairs][0]
        return 3, pairs+[kicker]
    if counts[0]==2:
        pair = cnt[0][0]
        kicks = sorted([r for r in ranks if r!=pair], reverse=True)
        return 2, [pair]+kicks
    return 1, ranks


class GameEngine:
    HAND_RANKINGS: Dict[int, str] = {
        9: 'Straight Flush',
        8: 'Four of a Kind',
        7: 'Full House',
        6: 'Flush',
        5: 'Straight',
        4: 'Three of a Kind',
        3: 'Two Pair',
        2: 'One Pair',
        1: 'High Card'
    }

    def __init__(self, players: List[Player], deck: Deck,
                 small_blind: int = 25, big_blind: int = 50):
        self.players = players
        self.deck = deck
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.pot = 0
        self.dealer_idx = 0

    def play_round(self) -> None:
        n = len(self.players)
        sb_idx = (self.dealer_idx + 1) % n
        bb_idx = (self.dealer_idx + 2) % n

        # Przygotowanie rundy
        self.deck.shuffle()
        self.pot = 0
        for p in self.players:
            p._Player__hand_ = []

        # Blindy
        sb = self.players[sb_idx]
        bb = self.players[bb_idx]
        sb_amt = min(self.small_blind, sb.get_stack_amount())
        bb_amt = min(self.big_blind, bb.get_stack_amount())
        if sb.get_stack_amount() < sb_amt or bb.get_stack_amount() < bb_amt:
            raise InsufficientFundsError("Brak środków na opłacenie blindów")
        sb._Player__stack_ -= sb_amt
        bb._Player__stack_ -= bb_amt
        self.pot += sb_amt + bb_amt

        # Rozdanie kart
        self.deck.deal(self.players)
        for p in self.players:
            if not p.is_bot:
                print(f"{p._Player__name_}, Twoje karty: {p.cards_to_str()}")

        # Runda zakładów
        contributions = {p: 0 for p in self.players}
        contributions[sb] = sb_amt
        contributions[bb] = bb_amt
        current_bet = bb_amt
        active = self._betting_round((bb_idx + 1) % n, contributions, current_bet)

        # Fold do jednego
        if len(active) == 1:
            winner = active[0]
            print(f"Zwycięzca (wszyscy spasowali): {winner._Player__name_}, otrzymuje {self.pot} żetonów.")
            winner._Player__stack_ += self.pot
            self.dealer_idx = (self.dealer_idx + 1) % n
            self.pot = 0
            return

        # Wymiana kart
        for p in active:
            if p.is_bot:
                # bot losowo wymienia 0-3 kart
                num = random.randint(0, 3)
                indices = random.sample(range(5), num)
                print(f"{p._Player__name_} (BOT) wymienia karty: {indices}")
            else:
                print(f"{p._Player__name_}, Twoje karty: {p.cards_to_str()}")
                idxs = input("Które karty wymienić? (0-4 sep. spacją, ENTER = brak): ")
                indices = sorted({int(i) for i in idxs.split()}, reverse=True) if idxs else []
            try:
                new_hand = self.exchange_cards(p._Player__hand_, indices)
                p._Player__hand_ = new_hand
                print(f"Nowe karty: {p.cards_to_str()}")
            except (ValueError, IndexError):
                print("Błąd przy wymianie kart, pomijam.")

        # Showdown ze szczegółami i siłą układu
        showdown_info = []
        for p in active:
            hand = p._Player__hand_
            rank_id, tiebreak = hand_rank(hand)
            strength = (rank_id, tiebreak)
            showdown_info.append((p._Player__name_, self.HAND_RANKINGS[rank_id], strength, p.cards_to_str()))

        print(f"{'Gracz':<15} | {'Układ':<17} | {'Siła':<20} | Karty")
        print('-' * 70)
        for name, rank, strength, cards in showdown_info:
            print(f"{name:<15} | {rank:<17} | {str(strength):<20} | {cards}")

        winner = max(active, key=lambda p: hand_rank(p._Player__hand_))
        win_rank = self.HAND_RANKINGS[hand_rank(winner._Player__hand_)[0]]
        print(f"\nZwycięzca: {winner._Player__name_} ({win_rank}), otrzymuje {self.pot} żetonów.")
        winner._Player__stack_ += self.pot
        self.pot = 0
        self.dealer_idx = (self.dealer_idx + 1) % n

    def _betting_round(self, start: int, contributions: dict, current_bet: int) -> List[Player]:
        active = list(self.players)
        idx = start
        seen = set()
        while True:
            player = self.players[idx]
            if player in active:
                to_call = current_bet - contributions[player]
                contributed = contributions[player]
                # bot wybiera akcję losowo i informuje
                if player.is_bot:
                    if to_call > 0:
                        action = random.choice(['call', 'fold'])
                    else:
                        action = random.choice(['check', f'raise {random.randint(1, 20)}'])
                    print(f"{player._Player__name_} (BOT) wykonuje: {action}")
                else:
                    action = input(
                        f"{player._Player__name_} (Stack: {player.get_stack_amount()}, Pot: {self.pot}, "
                        f"postawił: {contributed}, do wyrównania: {to_call}) -> [check/call/raise X/fold]: "
                    ).strip().lower()
                cmd = action.split()
                if cmd[0] == 'fold':
                    active.remove(player)
                elif cmd[0] == 'check' and to_call == 0:
                    pass
                elif cmd[0] == 'call' and to_call > 0:
                    amt = min(to_call, player.get_stack_amount())
                    player._Player__stack_ -= amt
                    contributions[player] += amt
                    self.pot += amt
                elif cmd[0] == 'raise' and len(cmd) == 2 and cmd[1].isdigit():
                    X = int(cmd[1])
                    pay = to_call + X
                    player._Player__stack_ -= pay
                    contributions[player] += pay
                    self.pot += pay
                    current_bet += X
                    seen = {player}
                else:
                    raise InvalidActionError("Nieprawidłowa akcja")
                seen.add(player)
                if len(active) <= 1 or (all(contributions[p] == current_bet for p in active) and seen.issuperset(active)):
                    return active
            idx = (idx + 1) % len(self.players)

    def exchange_cards(self, hand: List[Card], indices: List[int]) -> List[Card]:
        for i in indices:
            if i < 0 or i >= len(hand):
                raise IndexError
            old = hand[i]
            new = self.deck.cards.pop()
            hand[i] = new
            self.deck.cards.insert(0, old)
        return hand

