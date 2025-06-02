import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import sys
import io
from typing import List, Optional
import os

from src.deck import Deck
from src.game_engine import GameEngine
from src.player import Player
from src.fileops.session_manager import SessionManager, serialize_player, create_round_summary

# Import modułu grafik kart
USE_CARD_GRAPHICS = False
CardButton = None
EnhancedCardButton = None
get_image_manager = None

try:
    from src.gui.card_graphics import CardButton, CardDisplay, CardGraphics

    USE_CARD_GRAPHICS = True

    try:
        from src.gui.card_images import EnhancedCardButton, get_image_manager

        # Nie inicjalizuj jeszcze menedżera - zrobimy to po utworzeniu okna
        print("Moduł obrazków kart dostępny")
    except ImportError:
        print("Używam generowanych grafik kart")
        get_image_manager = None
except ImportError:
    print("Moduł grafik kart niedostępny, używam tekstowej reprezentacji")


class PokerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Pięciokartowy")
        self.root.geometry("1200x800")

        # Zmienne gry
        self.engine = None
        self.game_id = None
        self.session_manager = SessionManager()
        self.round_number = 1
        self.rounds_history = []

        # Kolejka do komunikacji między wątkami
        self.message_queue = queue.Queue()
        self.action_queue = queue.Queue()

        # Flagi kontrolne
        self.waiting_for_action = False
        self.current_player_name = ""
        self.game_thread = None

        # Inicjalizuj menedżer obrazków (jeśli dostępny)
        if USE_CARD_GRAPHICS and get_image_manager:
            try:
                image_manager = get_image_manager()
                image_manager.ensure_loaded()  # Załaduj obrazki po utworzeniu okna
                if image_manager.use_images:
                    print("Używam obrazków kart z plików")
                    global CardButton
                    CardButton = EnhancedCardButton  # Podmień klasę na wersję z obrazkami
                else:
                    print("Używam generowanych grafik kart")
            except Exception as e:
                print(f"Błąd podczas ładowania obrazków: {e}")

        # Tworzenie GUI
        self._create_menu()
        self._create_main_layout()

        # Uruchomienie przetwarzania kolejki
        self.root.after(100, self._process_message_queue)

    def _create_menu(self):
        """Tworzy pasek menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Gra", menu=game_menu)
        game_menu.add_command(label="Nowa gra", command=self._new_game_dialog)
        game_menu.add_separator()
        game_menu.add_command(label="Zapisz grę", command=self._save_game)
        game_menu.add_command(label="Wczytaj grę", command=self._load_game_dialog)
        game_menu.add_separator()
        game_menu.add_command(label="Wyjście", command=self.root.quit)

    def _create_main_layout(self):
        """Tworzy główny układ interfejsu"""
        # Panel górny - informacje o grze
        self.info_frame = ttk.Frame(self.root)
        self.info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.pot_label = ttk.Label(self.info_frame, text="Pula: 0", font=("Arial", 14, "bold"))
        self.pot_label.pack(side=tk.LEFT, padx=20)

        self.phase_label = ttk.Label(self.info_frame, text="Faza: Oczekiwanie", font=("Arial", 12))
        self.phase_label.pack(side=tk.LEFT, padx=20)

        self.round_label = ttk.Label(self.info_frame, text="Runda: 0", font=("Arial", 12))
        self.round_label.pack(side=tk.LEFT, padx=20)

        # Panel graczy
        self.players_frame = ttk.LabelFrame(self.root, text="Gracze", padding=10)
        self.players_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Panel kart gracza
        self.cards_frame = ttk.LabelFrame(self.root, text="Twoje karty", padding=10)
        self.cards_frame.pack(fill=tk.X, padx=10, pady=5)

        # Ramka na przyciski kart
        self.cards_buttons_frame = ttk.Frame(self.cards_frame)
        self.cards_buttons_frame.pack()

        self.card_buttons = []
        self.selected_cards = set()

        if USE_CARD_GRAPHICS:
            # Używamy graficznych kart
            for i in range(5):
                card_btn = CardButton(self.cards_buttons_frame, None,
                                      command=lambda idx=i: self._toggle_card_selection(idx))
                card_btn.pack(side=tk.LEFT, padx=5)
                self.card_buttons.append(card_btn)
        else:
            # Używamy tekstowych przycisków
            for i in range(5):
                btn = tk.Button(self.cards_buttons_frame, text="", width=10, height=5,
                                font=("Courier", 16), state=tk.DISABLED,
                                command=lambda idx=i: self._toggle_card_selection(idx))
                btn.pack(side=tk.LEFT, padx=5)
                self.card_buttons.append(btn)

        # Panel akcji
        self.action_frame = ttk.LabelFrame(self.root, text="Akcje", padding=10)
        self.action_frame.pack(fill=tk.X, padx=10, pady=5)

        # Przyciski akcji licytacji
        self.bet_buttons_frame = ttk.Frame(self.action_frame)
        self.bet_buttons_frame.pack(fill=tk.X)

        self.check_btn = ttk.Button(self.bet_buttons_frame, text="Check",
                                    command=lambda: self._send_action("check"), state=tk.DISABLED)
        self.check_btn.pack(side=tk.LEFT, padx=5)

        self.call_btn = ttk.Button(self.bet_buttons_frame, text="Call",
                                   command=lambda: self._send_action("call"), state=tk.DISABLED)
        self.call_btn.pack(side=tk.LEFT, padx=5)

        self.raise_frame = ttk.Frame(self.bet_buttons_frame)
        self.raise_frame.pack(side=tk.LEFT, padx=5)

        self.raise_btn = ttk.Button(self.raise_frame, text="Raise",
                                    command=self._handle_raise, state=tk.DISABLED)
        self.raise_btn.pack(side=tk.LEFT)

        self.raise_entry = ttk.Entry(self.raise_frame, width=10)
        self.raise_entry.pack(side=tk.LEFT, padx=5)

        self.fold_btn = ttk.Button(self.bet_buttons_frame, text="Fold",
                                   command=lambda: self._send_action("fold"), state=tk.DISABLED)
        self.fold_btn.pack(side=tk.LEFT, padx=5)

        # Przycisk wymiany kart
        self.exchange_btn = ttk.Button(self.action_frame, text="Wymień zaznaczone karty",
                                       command=self._exchange_cards, state=tk.DISABLED)
        self.exchange_btn.pack(pady=10)

        # Panel komunikatów
        self.messages_frame = ttk.LabelFrame(self.root, text="Komunikaty", padding=10)
        self.messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.messages_text = scrolledtext.ScrolledText(self.messages_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.messages_text.pack(fill=tk.BOTH, expand=True)

        # Konfiguracja tagów dla kolorowych komunikatów
        self.messages_text.tag_config("header", font=("Arial", 12, "bold"), foreground="blue")
        self.messages_text.tag_config("win", font=("Arial", 11, "bold"), foreground="green")
        self.messages_text.tag_config("lose", foreground="red")
        self.messages_text.tag_config("action", foreground="purple")
        self.messages_text.tag_config("info", foreground="navy")
        self.messages_text.tag_config("error", font=("Arial", 10, "bold"), foreground="red", background="yellow")

        # Panel kontrolny na dole
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)

        self.continue_btn = ttk.Button(self.control_frame, text="🎮 Kontynuuj grę",
                                       command=self._continue_game, state=tk.DISABLED,
                                       style="Large.TButton")
        self.continue_btn.pack(side=tk.LEFT, padx=5)

        ttk.Style().configure("Large.TButton", font=("Arial", 12, "bold"))

    def _new_game_dialog(self):
        """Dialog nowej gry"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Nowa gra")
        dialog.geometry("400x500")

        # Liczba graczy
        ttk.Label(dialog, text="Liczba graczy (2-6):").pack(pady=5)
        player_count_var = tk.IntVar(value=3)
        ttk.Spinbox(dialog, from_=2, to=6, textvariable=player_count_var, width=10).pack()

        # Ramka na dane graczy
        players_data_frame = ttk.Frame(dialog)
        players_data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        player_entries = []

        def update_player_fields(*args):
            # Usuń stare pola
            for widget in players_data_frame.winfo_children():
                widget.destroy()
            player_entries.clear()

            # Dodaj nowe pola
            for i in range(player_count_var.get()):
                frame = ttk.Frame(players_data_frame)
                frame.pack(fill=tk.X, pady=5)

                ttk.Label(frame, text=f"Gracz {i + 1}:").pack(side=tk.LEFT, padx=5)

                name_var = tk.StringVar(value=f"Gracz_{i + 1}")
                name_entry = ttk.Entry(frame, textvariable=name_var, width=15)
                name_entry.pack(side=tk.LEFT, padx=5)

                is_bot_var = tk.BooleanVar(value=(i > 0))
                bot_check = ttk.Checkbutton(frame, text="Bot", variable=is_bot_var)
                bot_check.pack(side=tk.LEFT, padx=5)

                stack_var = tk.IntVar(value=1000)
                ttk.Label(frame, text="Żetony:").pack(side=tk.LEFT, padx=5)
                stack_entry = ttk.Spinbox(frame, from_=50, to=5000, increment=50,
                                          textvariable=stack_var, width=10)
                stack_entry.pack(side=tk.LEFT, padx=5)

                player_entries.append((name_var, is_bot_var, stack_var))

        player_count_var.trace('w', update_player_fields)
        update_player_fields()

        # Blindy
        blinds_frame = ttk.Frame(dialog)
        blinds_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(blinds_frame, text="Small blind:").pack(side=tk.LEFT, padx=5)
        small_blind_var = tk.IntVar(value=25)
        ttk.Spinbox(blinds_frame, from_=1, to=100, textvariable=small_blind_var, width=10).pack(side=tk.LEFT)

        ttk.Label(blinds_frame, text="Big blind:").pack(side=tk.LEFT, padx=5)
        big_blind_var = tk.IntVar(value=50)
        ttk.Spinbox(blinds_frame, from_=1, to=200, textvariable=big_blind_var, width=10).pack(side=tk.LEFT)

        # Przyciski
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        def start_game():
            # Walidacja
            if big_blind_var.get() <= small_blind_var.get():
                messagebox.showerror("Błąd", "Big blind musi być większy od small blind")
                return

            # Tworzenie graczy
            players = []
            for i, (name_var, is_bot_var, stack_var) in enumerate(player_entries):
                name = name_var.get().strip()
                if not name:
                    messagebox.showerror("Błąd", f"Nazwa gracza {i + 1} nie może być pusta")
                    return

                if is_bot_var.get():
                    name = f"Bot_{i + 1}"

                players.append(Player(stack_var.get(), name, is_bot_var.get()))

            # Inicjalizacja gry
            self._init_new_game(players, small_blind_var.get(), big_blind_var.get())
            dialog.destroy()

        ttk.Button(buttons_frame, text="Rozpocznij", command=start_game).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Anuluj", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _init_new_game(self, players: List[Player], small_blind: int, big_blind: int):
        """Inicjalizuje nową grę"""
        import uuid

        deck = Deck()
        self.engine = GameEngine(players, deck, small_blind, big_blind)
        self.game_id = str(uuid.uuid4())
        self.round_number = 1
        self.rounds_history = []

        # Wyczyść komunikaty
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.delete(1.0, tk.END)
        self.messages_text.config(state=tk.DISABLED)

        self._update_display()
        self._add_message("=== NOWA GRA ===")
        self._add_message(f"Liczba graczy: {len(players)}")
        self._add_message(f"Blindy: {small_blind}/{big_blind}")

        # Uruchom grę w osobnym wątku
        self._start_game_thread()

    def _load_game_dialog(self):
        """Dialog wczytywania gry"""
        sessions = self.session_manager.list_sessions()

        if not sessions:
            messagebox.showinfo("Informacja", "Nie znaleziono zapisanych sesji gry.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Wczytaj grę")
        dialog.geometry("600x400")

        # Lista sesji
        ttk.Label(dialog, text="Dostępne sesje gry:").pack(pady=5)

        sessions_frame = ttk.Frame(dialog)
        sessions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview do wyświetlania sesji
        tree = ttk.Treeview(sessions_frame, columns=('timestamp', 'players', 'rounds'), show='tree headings')
        tree.heading('#0', text='Nr')
        tree.heading('timestamp', text='Data')
        tree.heading('players', text='Gracze')
        tree.heading('rounds', text='Rundy')

        # Scrollbar
        scrollbar = ttk.Scrollbar(sessions_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Wypełnij listę
        for i, session in enumerate(sessions):
            players_str = ", ".join(session['players'])
            tree.insert('', 'end', text=str(i + 1),
                        values=(session['timestamp'][:19], players_str, session['rounds_played']),
                        tags=(session['game_id'],))

        # Przyciski
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        def load_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Uwaga", "Wybierz sesję do wczytania")
                return

            item = tree.item(selection[0])
            game_id = item['tags'][0]

            try:
                self._load_game(game_id)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd podczas wczytywania gry: {e}")

        ttk.Button(buttons_frame, text="Wczytaj", command=load_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Anuluj", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _load_game(self, game_id: str):
        """Wczytuje grę z pliku"""
        session_data = self.session_manager.load_session(game_id)

        # Odtwórz graczy
        players = []
        for p_data in session_data['players']:
            player = Player(p_data['stack'], p_data['name'], p_data.get('is_bot', False))
            players.append(player)

        # Utwórz silnik gry
        deck = Deck()
        self.engine = GameEngine(
            players,
            deck,
            session_data.get('small_blind', 25),
            session_data.get('big_blind', 50)
        )

        self.engine.dealer_idx = session_data.get('dealer_idx', 0)
        self.game_id = game_id
        self.round_number = session_data.get('round_number', 1)
        self.rounds_history = session_data.get('rounds_history', [])

        self._update_display()
        self._add_message(f"=== WCZYTANO GRĘ ===")
        self._add_message(f"Kontynuacja od rundy {self.round_number}")

        # Uruchom grę
        self._start_game_thread()

    def _save_game(self):
        """Zapisuje stan gry"""
        if not self.engine:
            messagebox.showwarning("Uwaga", "Brak aktywnej gry do zapisania")
            return

        try:
            # Serializacja danych graczy
            players_data = [serialize_player(player) for player in self.engine.players]

            # Tworzenie danych sesji
            session_data = {
                'game_id': self.game_id,
                'small_blind': self.engine.small_blind,
                'big_blind': self.engine.big_blind,
                'dealer_idx': self.engine.dealer_idx,
                'round_number': self.round_number,
                'players': players_data,
                'rounds_history': self.rounds_history
            }

            # Zapisanie sesji
            self.session_manager.save_session(session_data)
            self._add_message(f"Stan gry został zapisany. ID sesji: {self.game_id}")
            messagebox.showinfo("Sukces", "Gra została zapisana pomyślnie")

        except Exception as e:
            messagebox.showerror("Błąd", f"Błąd podczas zapisywania gry: {e}")

    def _start_game_thread(self):
        """Uruchamia wątek gry"""
        if self.game_thread and self.game_thread.is_alive():
            return

        self.game_thread = threading.Thread(target=self._game_loop, daemon=True)
        self.game_thread.start()

    def _game_loop(self):
        """Główna pętla gry - uruchamiana w osobnym wątku"""
        while self.engine and len(self.engine.players) >= 2:
            try:
                # Przechwytywanie wyjścia standardowego
                old_stdout = sys.stdout
                sys.stdout = self._create_stdout_redirect()

                # Zapisz oryginalne metody
                original_prompt_bet = self.engine.prompt_bet
                original_exchange = self.engine.exchange_cards

                # Podmień metody na wersje GUI
                self.engine.prompt_bet = self._gui_prompt_bet
                self.engine.exchange_cards = self._gui_exchange_wrapper

                # Podmień też input() dla fazy wymiany kart
                import builtins
                original_input = builtins.input
                builtins.input = self._gui_input_wrapper

                # Aktualizuj informacje o rundzie
                self.message_queue.put(('round', self.round_number))

                # Rozegraj rundę
                self.engine.play_round()

                # Przywróć oryginalne metody
                self.engine.prompt_bet = original_prompt_bet
                self.engine.exchange_cards = original_exchange
                builtins.input = original_input
                sys.stdout = old_stdout

                # Zapisz rundę do historii
                round_summary = create_round_summary(self.engine, self.round_number, [])
                self.rounds_history.append(round_summary)

                # Usunięto automatyczny zapis - teraz tylko ręczny z menu

                # Sprawdź czy kontynuować
                if not self._check_continue():
                    break

                self.round_number += 1

            except Exception as e:
                sys.stdout = old_stdout
                self.message_queue.put(('error', f"Błąd w grze: {e}"))
                import traceback
                traceback.print_exc()
                break

        self.message_queue.put(('game_over', 'Koniec gry'))

    def _continue_game(self):
        """Obsługuje kliknięcie przycisku kontynuacji"""
        if self.waiting_for_action:
            self.action_queue.put('continue')
            self.continue_btn.config(state=tk.DISABLED)

    def _show_showdown_dialog(self, showdown_data):
        """Pokazuje okno z wynikami showdown"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🏆 Showdown - Wyniki rozdania")
        dialog.geometry("600x400")
        dialog.transient(self.root)

        # Nagłówek
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(header_frame, text="⚔️ SHOWDOWN ⚔️",
                  font=("Arial", 18, "bold")).pack()

        # Tabela z graczami
        table_frame = ttk.Frame(dialog)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Nagłówki kolumn
        ttk.Label(table_frame, text="Gracz", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=10, pady=5)
        ttk.Label(table_frame, text="Karty", font=("Arial", 12, "bold")).grid(row=0, column=1, padx=10, pady=5)
        ttk.Label(table_frame, text="Układ", font=("Arial", 12, "bold")).grid(row=0, column=2, padx=10, pady=5)

        # Dane graczy
        for i, player_info in enumerate(showdown_data['players'], 1):
            # Nazwa gracza
            name_label = ttk.Label(table_frame, text=player_info['name'], font=("Arial", 11))
            if player_info.get('is_winner'):
                name_label.config(foreground="green", font=("Arial", 11, "bold"))
            name_label.grid(row=i, column=0, padx=10, pady=5)

            # Karty
            ttk.Label(table_frame, text=player_info['cards'],
                      font=("Courier", 12)).grid(row=i, column=1, padx=10, pady=5)

            # Układ
            rank_label = ttk.Label(table_frame, text=player_info['rank'], font=("Arial", 11))
            if player_info.get('is_winner'):
                rank_label.config(foreground="green", font=("Arial", 11, "bold"))
            rank_label.grid(row=i, column=2, padx=10, pady=5)

        # Informacja o zwycięzcy i puli
        winner_frame = ttk.Frame(dialog)
        winner_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(winner_frame,
                  text=f"🏆 Zwycięzca: {showdown_data['winner']} wygrywa {showdown_data['pot']} żetonów!",
                  font=("Arial", 14, "bold"), foreground="green").pack()

        # Przycisk zamknięcia
        ttk.Button(dialog, text="OK", command=dialog.destroy,
                   style="Large.TButton").pack(pady=10)

        # Ustaw focus na dialog
        dialog.focus_set()

    def _gui_prompt_bet(self, player: Player, current_bet: int, contributed: int) -> str:
        """Zastępuje prompt_bet dla GUI"""
        to_call = current_bet - contributed

        # Dla botów używamy oryginalnej logiki
        if player.is_bot:
            import random
            if to_call > 0:
                if random.random() < 0.7:
                    action = 'call'
                else:
                    action = 'fold'
            else:
                if random.random() < 0.3:
                    raise_amount = random.randint(1, min(50, player.get_stack_amount()))
                    action = f'raise {raise_amount}'
                else:
                    action = 'check'

            self.message_queue.put(('message', f"{player.get_name()} (BOT) wykonuje: {action}"))
            return action

        # Dla gracza człowieka
        self.current_player_name = player.get_name()
        self.message_queue.put(('enable_betting', {
            'player': player.get_name(),
            'stack': player.get_stack_amount(),
            'to_call': to_call,
            'current_bet': current_bet,
            'contributed': contributed
        }))

        # Czekaj na akcję
        self.waiting_for_action = True
        action = self.action_queue.get()
        self.waiting_for_action = False

        self.message_queue.put(('disable_betting', None))
        return action

    def _gui_exchange_wrapper(self, hand, indices):
        """Wrapper dla exchange_cards - używa oryginalnej metody"""
        # Wykonaj wymianę kart używając oryginalnej logiki
        new_hand = list(hand)
        for i in indices:
            if i < 0 or i >= len(hand):
                raise IndexError(f"Nieprawidłowy indeks karty: {i}")

        for i in indices:
            old = new_hand[i]
            new = self.engine.deck.cards.pop()
            new_hand[i] = new
            self.engine.deck.cards.insert(0, old)

        return new_hand

    def _gui_input_wrapper(self, prompt=""):
        """Wrapper dla input() który obsługuje GUI podczas wymiany kart"""
        # Wyświetl prompt w komunikatach
        if prompt:
            self.message_queue.put(('message', f">>> {prompt}"))

        # Sprawdź czy to pytanie o wymianę kart
        if "Które karty wymienić?" in prompt:
            # Znajdź gracza człowieka
            human_player = None
            for p in self.engine.players:
                if not p.is_bot:
                    human_player = p
                    break

            if human_player:
                # Włącz GUI do wyboru kart
                self.message_queue.put(('enable_exchange', list(human_player.get_player_hand())))

                # Czekaj na wybór
                self.waiting_for_action = True
                selected_indices = self.action_queue.get()
                self.waiting_for_action = False

                self.message_queue.put(('disable_exchange', None))

                # Zwróć indeksy jako string
                if selected_indices:
                    return ' '.join(str(i) for i in selected_indices)
                else:
                    return ""

        # Dla pytania o kontynuację gry
        elif "czy chcesz grać dalej?" in prompt.lower():
            # To jest obsługiwane przez _check_continue
            return "t"

        # Dla innych pytań zwróć pusty string
        return ""

    def _gui_showdown_wrapper(self, active_players=None):
        """Wrapper dla showdown który wysyła dane do GUI"""
        # Wywołaj oryginalną metodę
        if active_players is None:
            active_players = self.engine.players

        if not active_players:
            raise ValueError("Brak aktywnych graczy do showdown")

        # Przygotuj dane do wyświetlenia
        showdown_data = {
            'players': [],
            'winner': None,
            'pot': self.engine.pot
        }

        # Zbierz informacje o graczach
        for p in active_players:
            hand = p.get_player_hand()
            rank_id, tiebreak = self.engine.hand_evaluator.get_hand_strength(list(hand))
            hand_name = self.engine.hand_evaluator.HAND_RANKINGS[rank_id]

            showdown_data['players'].append({
                'name': p.get_name(),
                'cards': p.cards_to_str(),
                'rank': hand_name,
                'strength': (rank_id, tiebreak)
            })

        # Znajdź zwycięzcę
        winner = max(active_players,
                     key=lambda p: self.engine.hand_evaluator.get_hand_strength(list(p.get_player_hand())))

        showdown_data['winner'] = winner.get_name()

        # Oznacz zwycięzcę w danych
        for player_info in showdown_data['players']:
            if player_info['name'] == winner.get_name():
                player_info['is_winner'] = True

        # Wyślij dane do GUI
        self.message_queue.put(('showdown', showdown_data))

        return winner

    def _check_continue(self) -> bool:
        """Sprawdza czy kontynuować grę"""
        # Usuń graczy bez żetonów
        next_players = []
        for p in self.engine.players:
            if p.get_stack_amount() > 0:
                next_players.append(p)
            else:
                self.message_queue.put(('message', f"{p.get_name()} nie ma już żetonów i odpada z gry."))

        self.engine.players = next_players

        if len(next_players) < 2:
            return False

        # Włącz przycisk kontynuacji
        self.message_queue.put(('enable_continue', None))

        # Czekaj na decyzję użytkownika
        self.waiting_for_action = True
        response = self.action_queue.get()
        self.waiting_for_action = False

        self.message_queue.put(('disable_continue', None))

        return response == 'continue'

    def _create_stdout_redirect(self):
        """Tworzy obiekt do przechwytywania print()"""

        class StdoutRedirect:
            def __init__(self, queue):
                self.queue = queue

            def write(self, text):
                if text.strip():
                    self.queue.put(('message', text.strip()))

            def flush(self):
                pass

        return StdoutRedirect(self.message_queue)

    def _process_message_queue(self):
        """Przetwarza komunikaty z kolejki"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()

                if msg_type == 'message':
                    self._add_message(data)
                elif msg_type == 'round':
                    self.round_label.config(text=f"Runda: {data}")
                elif msg_type == 'error':
                    self._add_message(f"BŁĄD: {data}", "error")
                    messagebox.showerror("Błąd", data)
                elif msg_type == 'game_over':
                    self._add_message("=== KONIEC GRY ===", "header")
                    self._disable_all_actions()
                elif msg_type == 'enable_betting':
                    self._enable_betting_actions(data)
                elif msg_type == 'disable_betting':
                    self._disable_betting_actions()
                elif msg_type == 'enable_exchange':
                    self._enable_card_exchange(data)
                elif msg_type == 'disable_exchange':
                    self._disable_card_exchange()
                elif msg_type == 'enable_continue':
                    self.continue_btn.config(state=tk.NORMAL)
                    self._add_message("\n👉 Kliknij 'Kontynuuj grę' aby przejść do następnej rundy", "info")
                elif msg_type == 'disable_continue':
                    self.continue_btn.config(state=tk.DISABLED)
                elif msg_type == 'showdown':
                    self._show_showdown_dialog(data)

                # Zawsze aktualizuj wyświetlanie po przetworzeniu komunikatu
                self._update_display()

        except queue.Empty:
            pass

        # Zaplanuj następne sprawdzenie
        self.root.after(100, self._process_message_queue)

    def _update_display(self):
        """Aktualizuje wyświetlane informacje"""
        if not self.engine:
            return

        # Aktualizuj pulę
        self.pot_label.config(text=f"Pula: {self.engine.pot}")

        # Aktualizuj panel graczy
        for widget in self.players_frame.winfo_children():
            widget.destroy()

        # Znajdź gracza człowieka
        human_player = None

        for i, player in enumerate(self.engine.players):
            frame = ttk.Frame(self.players_frame)
            frame.pack(fill=tk.X, pady=2)

            # Nazwa gracza
            name_text = player.get_name()
            if i == self.engine.dealer_idx:
                name_text += " (D)"
            if player.is_bot:
                name_text += " [BOT]"
            else:
                human_player = player  # Zapamiętaj gracza człowieka

            name_label = ttk.Label(frame, text=name_text, font=("Arial", 12, "bold"))
            name_label.pack(side=tk.LEFT, padx=5)

            # Stack
            stack_label = ttk.Label(frame, text=f"{player.get_stack_amount()} żetonów")
            stack_label.pack(side=tk.LEFT, padx=5)

            # Karty (tylko dla gracza człowieka podczas gry)
            if not player.is_bot and player.get_player_hand():
                cards_text = player.cards_to_str()
                cards_label = ttk.Label(frame, text=cards_text, font=("Courier", 14))
                cards_label.pack(side=tk.LEFT, padx=10)

        # Aktualizuj karty na przyciskach dla gracza człowieka
        if human_player and human_player.get_player_hand():
            hand = human_player.get_player_hand()
            for i, card in enumerate(hand):
                if i < len(self.card_buttons):
                    self.card_buttons[i].config(text=str(card), font=("Courier", 16))

    def _add_message(self, message: str, tag=None):
        """Dodaje komunikat do okna komunikatów z opcjonalnym formatowaniem"""
        self.messages_text.config(state=tk.NORMAL)

        # Dodaj emotki i formatowanie
        if "===" in message:
            # Nagłówki
            if "NOWA GRA" in message:
                message = "🎮 " + message
                tag = "header"
            elif "RUNDA LICYTACJI" in message:
                message = "💰 " + message
                tag = "header"
            elif "WYMIANA KART" in message:
                message = "🃏 " + message
                tag = "header"
            elif "SHOWDOWN" in message:
                message = "⚔️ " + message
                tag = "header"
            elif "KONIEC GRY" in message:
                message = "🏁 " + message
                tag = "header"
            else:
                tag = "header"
        elif "zwycięzca" in message.lower() or "wygrywa" in message.lower():
            message = "🏆 " + message
            tag = "win"
        elif "fold" in message.lower() or "pasuje" in message.lower():
            message = "❌ " + message
            tag = "lose"
        elif "call" in message.lower() or "check" in message.lower() or "raise" in message.lower():
            message = "🎯 " + message
            tag = "action"
        elif "bot" in message.lower():
            message = "🤖 " + message
            tag = "info"
        elif "błąd" in message.lower():
            message = "⚠️ " + message
            tag = "error"

        if tag:
            self.messages_text.insert(tk.END, message + "\n", tag)
        else:
            self.messages_text.insert(tk.END, message + "\n")

        self.messages_text.see(tk.END)
        self.messages_text.config(state=tk.DISABLED)

    def _toggle_card_selection(self, idx: int):
        """Przełącza zaznaczenie karty"""
        if USE_CARD_GRAPHICS:
            card_btn = self.card_buttons[idx]
            if not hasattr(card_btn, 'enabled') or not card_btn.enabled:
                return

            if idx in self.selected_cards:
                self.selected_cards.remove(idx)
                card_btn.set_selected(False)
                self._add_message(f"Odznaczyłeś kartę {idx + 1}")
            else:
                self.selected_cards.add(idx)
                card_btn.set_selected(True)
                self._add_message(f"Zaznaczyłeś kartę {idx + 1}")
        else:
            if self.card_buttons[idx]['state'] == tk.DISABLED:
                return

            if idx in self.selected_cards:
                self.selected_cards.remove(idx)
                self.card_buttons[idx].config(relief=tk.RAISED, bg='SystemButtonFace')
                self._add_message(f"Odznaczyłeś kartę {idx + 1}")
            else:
                self.selected_cards.add(idx)
                self.card_buttons[idx].config(relief=tk.SUNKEN, bg='lightblue')
                self._add_message(f"Zaznaczyłeś kartę {idx + 1}")

    def _enable_betting_actions(self, data):
        """Włącza przyciski akcji licytacji"""
        to_call = data['to_call']

        # Wyczyść pole raise
        self.raise_entry.delete(0, tk.END)

        if to_call == 0:
            self.check_btn.config(state=tk.NORMAL, text="Check")
            self.call_btn.config(state=tk.DISABLED)
        else:
            self.check_btn.config(state=tk.DISABLED)
            self.call_btn.config(state=tk.NORMAL, text=f"Call {to_call}")

        self.fold_btn.config(state=tk.NORMAL)

        if data['stack'] > to_call:
            self.raise_btn.config(state=tk.NORMAL)
            self.raise_entry.config(state=tk.NORMAL)
        else:
            self.raise_btn.config(state=tk.DISABLED)
            self.raise_entry.config(state=tk.DISABLED)

        # Aktualizuj etykietę fazy
        self.phase_label.config(text=f"Faza: Licytacja - {data['player']}")

    def _disable_betting_actions(self):
        """Wyłącza przyciski akcji licytacji"""
        self.check_btn.config(state=tk.DISABLED)
        self.call_btn.config(state=tk.DISABLED)
        self.raise_btn.config(state=tk.DISABLED)
        self.fold_btn.config(state=tk.DISABLED)
        self.raise_entry.config(state=tk.DISABLED)

    def _enable_card_exchange(self, hand):
        """Włącza wymianę kart"""
        self.selected_cards.clear()

        # Pokaż karty na przyciskach
        for i, card in enumerate(hand):
            if i < len(self.card_buttons):
                if USE_CARD_GRAPHICS:
                    self.card_buttons[i].set_card(card)
                    self.card_buttons[i].set_enabled(True)
                    self.card_buttons[i].enabled = True
                    self.card_buttons[i].set_selected(False)
                else:
                    self.card_buttons[i].config(
                        text=str(card),
                        state=tk.NORMAL,
                        font=("Courier", 16),
                        relief=tk.RAISED,
                        bg='SystemButtonFace'
                    )

        self.exchange_btn.config(state=tk.NORMAL)
        self.phase_label.config(text="Faza: Wymiana kart")

        # Dodaj informację dla gracza
        self._add_message("\n=== WYMIANA KART ===", "header")
        self._add_message("Kliknij na karty które chcesz wymienić, następnie kliknij 'Wymień zaznaczone karty'", "info")
        self._add_message("Możesz też kliknąć przycisk bez zaznaczania kart, aby nie wymieniać żadnych", "info")

    def _disable_card_exchange(self):
        """Wyłącza wymianę kart"""
        for i, btn in enumerate(self.card_buttons):
            if USE_CARD_GRAPHICS:
                btn.set_enabled(False)
                btn.enabled = False
                btn.set_selected(False)
            else:
                btn.config(state=tk.DISABLED, relief=tk.RAISED, bg='SystemButtonFace')
        self.exchange_btn.config(state=tk.DISABLED)
        self.selected_cards.clear()

    def _exchange_cards(self):
        """Obsługuje wymianę kart"""
        if self.waiting_for_action:
            indices = sorted(list(self.selected_cards), reverse=True)
            if indices:
                self._add_message(f"Wymieniasz karty na pozycjach: {indices}")
            else:
                self._add_message("Nie wymieniasz żadnych kart")

            # Wyślij indeksy do wymiany
            self.action_queue.put(indices)

    def _send_action(self, action: str):
        """Wysyła akcję do silnika gry"""
        if self.waiting_for_action:
            self.action_queue.put(action)
            self._add_message(f"{self.current_player_name} wykonuje: {action}")

    def _handle_raise(self):
        """Obsługuje akcję raise"""
        if not self.waiting_for_action:
            return

        try:
            amount = int(self.raise_entry.get())
            if amount <= 0:
                messagebox.showerror("Błąd", "Kwota raise musi być dodatnia")
                return

            self.action_queue.put(f"raise {amount}")
            self._add_message(f"{self.current_player_name} wykonuje: raise {amount}")

        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowa kwota")

    def _disable_all_actions(self):
        """Wyłącza wszystkie akcje"""
        self._disable_betting_actions()
        self._disable_card_exchange()
        self.continue_btn.config(state=tk.DISABLED)

        messagebox.showerror("Błąd", f"Maksymalny raise: {max_raise}", parent=self)


class PokerGUIApp:
    """Klasa główna aplikacji"""

    def __init__(self):
        self.root = tk.Tk()
        self.gui = PokerGUI(self.root)

    def run(self):
        """Uruchamia aplikację"""
        self.root.mainloop()


if __name__ == "__main__":
    # Upewnij się że katalog data istnieje
    if not os.path.exists('data'):
        os.makedirs('data')

    app = PokerGUIApp()
    app.run()