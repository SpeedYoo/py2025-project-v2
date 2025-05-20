import random
from typing import List

from src.card import Card
from src.player import Player


class Deck:

    def __init__(self):
        self._initialize_deck()

    def _initialize_deck(self):
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['s', 'h', 'd', 'c']
        self.cards = [Card(rank, suit) for suit in suits for rank in ranks]

    def __str__(self):
        return ', '.join(str(card) for card in self.cards)

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, players: List[Player], cards_per_player: int = 5):
        if len(self.cards) < len(players) * cards_per_player:
            raise ValueError("Za mało kart w talii do rozdania")

        for _ in range(cards_per_player):
            for player in players:
                if self.cards:
                    player.take_card(self.cards.pop())
                else:
                    raise ValueError("Zabrakło kart w talii podczas rozdawania")