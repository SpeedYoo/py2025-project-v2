class Player:

    def __init__(self, money, name="", is_bot: bool = False):
        self.__stack_ = money
        self.__name_ = name
        self.__hand_ = []
        self.is_bot = is_bot

    def take_card(self, card):
        self.__hand_.append(card)

    def get_stack_amount(self):
        return self.__stack_

    def change_card(self, card, idx):
        #TODO: przyjmuje nową kartę, wstawia ją za kartę o indeksie idx, zwraca kartę wymienioną
        temp_card = card
        card = self.__hand_[idx]
        self.__hand_[idx] = temp_card
        return card

    def get_player_hand(self):
        return tuple(self.__hand_)

    def cards_to_str(self):
        # TODO: definicja metody, zwraca stringa z kartami gracza
        return ''.join(str(card) for card in self.__hand_)
