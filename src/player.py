class Player:

    def __init__(self, money, name="", is_bot: bool = False):
        self.__stack = money
        self.__name = name
        self.__hand = []
        self.is_bot = is_bot

    def take_card(self, card):
        self.__hand.append(card)

    def get_stack_amount(self):
        return self.__stack

    def add_to_stack(self, amount):
        self.__stack += amount

    def remove_from_stack(self, amount):
        if amount > self.__stack:
            raise ValueError(f"Gracz {self.__name} nie ma wystarczającej ilości żetonów ({self.__stack})")
        self.__stack -= amount
        return amount

    def change_card(self, card, idx):
        old_card = self.__hand[idx]
        self.__hand[idx] = card
        return old_card

    def get_player_hand(self):
        return tuple(self.__hand)

    def get_name(self):
        return self.__name

    def clear_hand(self):
        self.__hand = []

    def cards_to_str(self):
        return ''.join(str(card) for card in self.__hand)