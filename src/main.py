from src.deck import Deck
from src.game_engine import GameEngine
from src.player import Player


def main():
    player1 = Player(1000, 'player1')
    player2 = Player(1000, 'player2', is_bot=True)

    players = [player1, player2]
    deck = Deck()
    engine = GameEngine(players, deck)

    while len(players) >= 2:
        engine.players = players
        engine.play_round()
        next_round = []
        for p in players:
            if getattr(p, 'is_bot', False):
                # Bot zawsze chce grać dalej
                print(f"{p._Player__name_} (BOT) zostaje w grze.")
                next_round.append(p)
            else:
                cont = input(f"{p._Player__name_}, czy chcesz grać dalej? (t/n): ").strip().lower()
                if cont == 't':
                    next_round.append(p)
                else:
                    print(f"{p._Player__name_} odchodzi z gry.")
        players = next_round
        if len(players) < 2:
            print("Za mało graczy, koniec gry.")
            break
    print("Dziękujemy za grę!")

if __name__ == "__main__":
    main()
