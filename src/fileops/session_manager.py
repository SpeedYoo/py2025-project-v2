import os
import json
import csv
from typing import Dict, Any, List

class SessionManager:
    def __init__(self, data_dir: str = 'data'):
        """
        Inicjalizuje katalog, w którym przechowywane będą pliki sesji.
        Jeśli katalog nie istnieje, zostaje utworzony.
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def save_session(self, session: Dict[str, Any]) -> None:
        """
        Zapisuje stan gry i historię zakończonych rozdań do pliku JSON-Lines.
        Każde wywołanie zapisuje jedną sesję jako osobny rekord.
        Klucz 'game_id' musi być obecny w słowniku session.
        """
        game_id = session.get('game_id')
        if not game_id:
            raise ValueError("Brak klucza 'game_id' w danych sesji")
        path = os.path.join(self.data_dir, f'session_{game_id}.jsonl')
        try:
            with open(path, 'a', encoding='utf-8') as f:
                json_record = json.dumps(session, ensure_ascii=False)
                f.write(json_record + '\n')
        except IOError as e:
            raise IOError(f"Błąd zapisu sesji: {e}")

    def load_session(self, game_id: str) -> Dict[str, Any]:
        """
        Ładuje sesję gry z pliku JSON-Lines i zwraca pełny stan gry.
        Jeżeli plik zawiera wiele wpisów, zwraca listę odsłoniętych sesji.
        """
        path = os.path.join(self.data_dir, f'session_{game_id}.jsonl')
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Brak sesji o id: {game_id}")
        sessions: List[Dict[str, Any]] = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    sessions.append(json.loads(line))
        except IOError as e:
            raise IOError(f"Błąd odczytu sesji: {e}")
        # jeśli pojedynczy wpis, zwracamy słownik, w innym razie listę
        if len(sessions) == 1:
            return sessions[0]
        return sessions

    def save_history_csv(self, history: List[Dict[str, Any]], filename: str) -> None:
        """
        Zapisuje listę rozdań (history) do pliku CSV.
        history: lista słowników z identycznymi kluczami.
        filename: nazwa pliku w katalogu data_dir.
        """
        if not history:
            return
        path = os.path.join(self.data_dir, filename)
        keys = list(history[0].keys())
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(history)
        except IOError as e:
            raise IOError(f"Błąd zapisu historii CSV: {e}")

    def load_config(self, config_path: str = 'config.json') -> Dict[str, Any]:
        """
        Odczytuje konfigurację gry z pliku JSON.
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Nie znaleziono pliku konfiguracyjnego: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Błąd formatu pliku konfiguracyjnego: {e}")

    def save_config(self, config: Dict[str, Any], config_path: str = 'config.json') -> None:
        """
        Zapisuje konfigurację gry do pliku JSON.
        """
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except IOError as e:
            raise IOError(f"Błąd zapisu pliku konfiguracyjnego: {e}")
