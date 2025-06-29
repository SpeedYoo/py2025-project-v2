class Card:
    """Reprezentuje kartę do gry."""

    UNICODE_SUITS = {
        's': '\u2660',  # pik (spade)
        'h': '\u2665',  # kier (heart)
        'd': '\u2666',  # karo (diamond)
        'c': '\u2663'   # trefl (club)
    }
    RANKS_VALUES = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

        if rank not in self.RANKS_VALUES:
            raise ValueError(f"Nieprawidłowa ranga karty: {rank}")
        if suit not in self.UNICODE_SUITS:
            raise ValueError(f"Nieprawidłowy kolor karty: {suit}")

    def get_value(self):
        return self.rank, self.suit

    def get_rank_value(self):
        return self.RANKS_VALUES[self.rank]

    def __str__(self):
        return f" {self.rank}{self.UNICODE_SUITS[self.suit]} "

    def __repr__(self):
        return f"Card('{self.rank}', '{self.suit}')"