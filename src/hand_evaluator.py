from typing import List, Tuple
from collections import Counter

from src.card import Card


class HandEvaluator:
    """Klasa odpowiedzialna za ocenę układów pokerowych."""

    HAND_RANKINGS = {
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

    @staticmethod
    def get_hand_strength(hand: List[Card]) -> Tuple[int, List[int]]:
        values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13,
                  'A': 14}
        ranks = sorted((values[c.rank] for c in hand), reverse=True)
        is_flush = len({c.suit for c in hand}) == 1
        uniq = sorted(set(ranks))

        # Sprawdzenie specjalnego przypadku dla strita A-5
        if uniq == [2, 3, 4, 5, 14]:
            is_straight, high = True, 5
        # Sprawdzenie normalnego strita
        elif len(uniq) == 5 and uniq[0] - 4 == uniq[-1]:
            is_straight, high = True, uniq[0]
        else:
            is_straight, high = False, ranks[0]

        cnt = Counter(ranks).most_common()
        counts = sorted([c for _, c in cnt], reverse=True)

        # Sprawdzenie wszystkich możliwych układów od najsilniejszego
        # Poker
        if is_straight and is_flush:
            return 9, [high]

        # Kareta
        if counts[0] == 4:
            four = cnt[0][0]
            kicker = [r for r in ranks if r != four][0]
            return 8, [four, kicker]

        # Full House
        if counts[0] == 3 and counts[1] == 2:
            return 7, [cnt[0][0], cnt[1][0]]

        # Kolor
        if is_flush:
            return 6, ranks

        # Strit
        if is_straight:
            return 5, [high]

        # Trójka
        if counts[0] == 3:
            three = cnt[0][0]
            kicks = sorted([r for r in ranks if r != three], reverse=True)
            return 4, [three] + kicks

        # Dwie pary
        if counts[0] == 2 and counts[1] == 2:
            pairs = sorted([r for r, c in cnt if c == 2], reverse=True)
            kicker = [r for r in ranks if r not in pairs][0]
            return 3, pairs + [kicker]

        # Para
        if counts[0] == 2:
            pair = cnt[0][0]
            kicks = sorted([r for r in ranks if r != pair], reverse=True)
            return 2, [pair] + kicks

        # Wysoka karta
        return 1, ranks