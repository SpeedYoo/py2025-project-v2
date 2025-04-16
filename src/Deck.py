import random

from src.Card import Card


class Deck():
    def __init__(self, *args):
        # TODO: definicja metody, ma tworzyć niepotasowaną talię (jak na poprzednich lab)
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['s', 'h', 'd', 'c']
        self.cards = [Card(rank, suit) for suit in suits for rank in ranks]

    def __str__(self):
        # TODO: definicja metody, przydatne do wypisywania karty
        return ', '.join(str(card) for card in self.cards)

    def shuffle(self):
        # TODO: definicja metody, tasowanie
        random.shuffle(self.cards)

    def deal(self, players):
        # TODO: definicja metody, otrzymuje listę graczy i rozdaje im karty wywołując na nich metodę take_card z Player
        for i in range(5):
            for p in players:
                if len(self.cards) > 0:
                    p.take_card(self.cards.pop())
