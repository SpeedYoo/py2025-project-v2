import os
import json
import uuid
import datetime
from typing import Dict, Optional


class SessionManager:

    def __init__(self, data_dir: str = '../../data'):
        self.data_dir = data_dir

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def save_session(self, session: dict) -> str:
        if 'game_id' not in session:
            session['game_id'] = str(uuid.uuid4())

        session['timestamp'] = datetime.datetime.now().isoformat()

        file_path = os.path.join(self.data_dir, f"session_{session['game_id']}.json")

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(session, file, ensure_ascii=False, indent=2)
            return session['game_id']
        except IOError as e:
            raise IOError(f"Błąd podczas zapisywania sesji: {e}")

    def load_session(self, game_id: str) -> dict:
        file_path = os.path.join(self.data_dir, f"session_{game_id}.json")

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                session = json.load(file)
            return session
        except FileNotFoundError:
            raise FileNotFoundError(f"Nie znaleziono pliku sesji dla ID: {game_id}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Błąd dekodowania pliku JSON: {e.msg}", e.doc, e.pos)
        except IOError as e:
            raise IOError(f"Błąd podczas wczytywania sesji: {e}")

    def list_sessions(self) -> list:
        sessions = []
        try:
            for filename in os.listdir(self.data_dir):
                if filename.startswith("session_") and filename.endswith(".json"):
                    file_path = os.path.join(self.data_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            session_data = json.load(file)
                            # Dodajemy tylko podstawowe dane o sesji
                            sessions.append({
                                'game_id': session_data.get('game_id', ''),
                                'timestamp': session_data.get('timestamp', ''),
                                'players': [p.get('name', '') for p in session_data.get('players', [])],
                                'rounds_played': len(session_data.get('rounds_history', []))
                            })
                    except (json.JSONDecodeError, IOError):
                        continue
        except IOError:
            pass

        return sorted(sessions, key=lambda x: x.get('timestamp', ''), reverse=True)

    def delete_session(self, game_id: str) -> bool:
        file_path = os.path.join(self.data_dir, f"session_{game_id}.json")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except IOError:
            return False


def serialize_player(player):

    return {
        'name': player.get_name(),
        'stack': player.get_stack_amount(),
        'is_bot': player.is_bot
    }


def serialize_card(card):

    return f"{card.rank}{card.suit}"


def serialize_hand(hand):

    return [serialize_card(card) for card in hand]


def create_round_summary(engine, round_number, actions=None):

    if actions is None:
        actions = []

    players_data = []
    for player in engine.players:
        player_data = serialize_player(player)
        hand = player.get_player_hand()
        if hand:
            player_data['hand'] = serialize_hand(hand)
        players_data.append(player_data)

    round_summary = {
        'round_number': round_number,
        'timestamp': datetime.datetime.now().isoformat(),
        'pot': engine.pot,
        'small_blind': engine.small_blind,
        'big_blind': engine.big_blind,
        'dealer_idx': engine.dealer_idx,
        'players': players_data,
        'actions': actions
    }

    return round_summary