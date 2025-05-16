class Card:
    # słownik symboli unicode
    unicode_dict = {'s': '\u2660', 'h': '\u2665', 'd': '\u2666', 'c': '\u2663'}

    def __init__(self, rank, suit):
        # definicja konstruktora, ma ustawiać pola rangi i koloru.
        self.rank = rank
        self.suit = suit

    def get_value(self):
        # definicja metody (ma zwracać kartę w takiej reprezentacji, jak dotychczas, tzn. krotka)
        return self.rank, self.suit

    def __str__(self):
        # definicja metody, przydatne do wypisywania karty
        return f" {self.rank}{Card.unicode_dict[self.suit]} "