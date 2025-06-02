"""
Rozszerzony moduł do obsługi grafik kart w GUI pokera.
Obsługuje zarówno obrazki PNG/JPG jak i generowane grafiki.
"""

import tkinter as tk
from tkinter import Canvas, PhotoImage
from PIL import Image, ImageTk
import os
from typing import Optional, Dict
from pathlib import Path


class CardImageManager:
    """Menedżer obrazków kart"""

    def __init__(self, cards_dir: str = "assets/cards"):
        # Sprawdź różne możliwe lokalizacje katalogu
        possible_paths = [
            Path(cards_dir),  # Ścieżka względna
            Path(__file__).parent.parent.parent / cards_dir,  # Względem tego pliku
            Path.cwd() / cards_dir,  # Względem katalogu roboczego
        ]

        self.cards_dir = None
        for path in possible_paths:
            if path.exists():
                self.cards_dir = path
                break

        if not self.cards_dir:
            self.cards_dir = Path(cards_dir)  # Użyj domyślnej

        self.images: Dict[str, PhotoImage] = {}
        self.back_image: Optional[PhotoImage] = None
        self.use_images = False
        self._loaded = False

    def ensure_loaded(self):
        """Upewnia się, że obrazki są załadowane (wywołać po utworzeniu okna Tkinter)"""
        if not self._loaded and self.cards_dir.exists():
            self._load_images()
            self._loaded = True

    def _load_images(self):
        """Ładuje obrazki kart z katalogu"""
        try:
            print(f"Szukam obrazków kart w: {self.cards_dir.absolute()}")

            if not self.cards_dir.exists():
                print(f"Katalog {self.cards_dir} nie istnieje!")
                return

            # Lista plików w katalogu
            files = list(self.cards_dir.glob("*"))
            print(f"Znaleziono {len(files)} plików w katalogu")

            # Mapowanie dla różnych konwencji nazewnictwa
            rank_map = {
                '2': ['2', 'two'], '3': ['3', 'three'], '4': ['4', 'four'],
                '5': ['5', 'five'], '6': ['6', 'six'], '7': ['7', 'seven'],
                '8': ['8', 'eight'], '9': ['9', 'nine'], '10': ['10', 'ten'],
                'J': ['J', 'jack', 'j'], 'Q': ['Q', 'queen', 'q'],
                'K': ['K', 'king', 'k'], 'A': ['A', 'ace', 'a']
            }

            suit_map = {
                's': ['s', 'S', 'spades', 'spade'],
                'h': ['h', 'H', 'hearts', 'heart'],
                'd': ['d', 'D', 'diamonds', 'diamond'],
                'c': ['c', 'C', 'clubs', 'club']
            }

            # Próbuj załadować obrazki
            cards_loaded = 0

            for rank, rank_variants in rank_map.items():
                for suit, suit_variants in suit_map.items():
                    key = f"{rank}{suit}"

                    # Próbuj różne kombinacje nazw
                    for r in rank_variants:
                        for s in suit_variants:
                            # Różne formaty nazw
                            filenames = [
                                f"{r}{s}.png",
                                f"{r}_{s}.png",
                                f"{r}_of_{s}.png",
                                f"{r}-{s}.png",
                                f"{r}{s}.jpg",
                                f"{r}_{s}.jpg"
                            ]

                            for filename in filenames:
                                filepath = self.cards_dir / filename
                                if filepath.exists():
                                    try:
                                        # Załaduj i przeskaluj obrazek
                                        img = Image.open(filepath)
                                        img = img.resize((80, 120), Image.Resampling.LANCZOS)
                                        self.images[key] = ImageTk.PhotoImage(img)
                                        cards_loaded += 1
                                        print(f"Załadowano: {filename} jako {key}")
                                        break
                                    except Exception as e:
                                        print(f"Błąd ładowania {filepath}: {e}")

                            if key in self.images:
                                break
                        if key in self.images:
                            break

            # Załaduj rewers karty
            back_names = ['back.png', 'card_back.png', 'back.jpg', 'card_back.jpg', 'red_back.png']
            for name in back_names:
                filepath = self.cards_dir / name
                if filepath.exists():
                    try:
                        img = Image.open(filepath)
                        img = img.resize((80, 120), Image.Resampling.LANCZOS)
                        self.back_image = ImageTk.PhotoImage(img)
                        print(f"Załadowano rewers: {name}")
                        break
                    except Exception as e:
                        print(f"Błąd ładowania rewersu: {e}")

            print(f"Załadowano {cards_loaded} obrazków kart")
            self.use_images = cards_loaded >= 52  # Używaj obrazków tylko jeśli mamy pełną talię

            if self.use_images:
                print("Włączono tryb obrazków kart")
            else:
                print(f"Za mało obrazków ({cards_loaded}/52), używam generowanych grafik")

        except Exception as e:
            print(f"Błąd podczas ładowania obrazków kart: {e}")
            self.use_images = False

    def get_card_image(self, rank: str, suit: str) -> Optional[PhotoImage]:
        """Zwraca obrazek karty"""
        self.ensure_loaded()  # Upewnij się, że obrazki są załadowane

        if not self.use_images:
            return None

        key = f"{rank}{suit}"
        return self.images.get(key)

    def get_back_image(self) -> Optional[PhotoImage]:
        """Zwraca obrazek rewersu karty"""
        self.ensure_loaded()  # Upewnij się, że obrazki są załadowane

        return self.back_image if self.use_images else None


# Globalny menedżer obrazków
_image_manager = None

def get_image_manager():
    """Zwraca globalną instancję menedżera obrazków"""
    global _image_manager
    if _image_manager is None:
        _image_manager = CardImageManager()
    return _image_manager


class EnhancedCardButton(tk.Frame):
    """Ulepszona wersja przycisku karty z obsługą obrazków"""

    def __init__(self, parent, card=None, width=80, height=120, command=None):
        super().__init__(parent)

        self.card = card
        self.selected = False
        self.enabled = True
        self.command = command
        self.width = width
        self.height = height

        # Pobierz menedżer obrazków
        self.image_manager = get_image_manager()

        # Utwórz widżet
        self._create_widget()

    def _create_widget(self):
        """Tworzy widget karty"""
        # Usuń poprzednie widżety
        for widget in self.winfo_children():
            widget.destroy()

        if self.card and self.image_manager.use_images:
            # Spróbuj użyć obrazka
            img = self.image_manager.get_card_image(self.card.rank, self.card.suit)
            if img:
                self.label = tk.Label(self, image=img,
                                    highlightthickness=2,
                                    highlightbackground='black')
                self.label.image = img  # Zachowaj referencję
                self.label.pack()

                if self.command and self.enabled:
                    self.label.bind("<Button-1>", self._on_click)
                    self.label.config(cursor="hand2")
                return

    def _on_click(self, event):
        """Obsługa kliknięcia"""
        if self.command and self.enabled:
            self.command()

    def set_selected(self, selected: bool):
        """Ustawia stan zaznaczenia"""
        self.selected = selected

        if hasattr(self, 'label'):
            if selected:
                self.label.config(highlightbackground='yellow', highlightthickness=4)
            else:
                self.label.config(highlightbackground='black', highlightthickness=2)
        elif hasattr(self, 'canvas'):
            if selected:
                self.canvas.config(highlightbackground='yellow', highlightthickness=4)
            else:
                self.canvas.config(highlightbackground='black', highlightthickness=2)

    def set_card(self, card):
        """Zmienia wyświetlaną kartę"""
        self.card = card
        self._create_widget()

    def set_enabled(self, enabled: bool):
        """Włącza/wyłącza przycisk"""
        self.enabled = enabled

        if hasattr(self, 'label'):
            if enabled and self.command:
                self.label.config(cursor="hand2")
                self.label.bind("<Button-1>", self._on_click)
            else:
                self.label.config(cursor="")
                self.label.unbind("<Button-1>")
        elif hasattr(self, 'canvas'):
            if enabled and self.command:
                self.canvas.config(cursor="hand2")
                self.canvas.bind("<Button-1>", self._on_click)
            else:
                self.canvas.config(cursor="")
                self.canvas.unbind("<Button-1>")


def download_card_images():
    """
    Przykładowa funkcja do pobrania darmowych obrazków kart.
    Możesz użyć tej funkcji raz, aby pobrać obrazki.
    """
    import urllib.request
    import zipfile

    print("Pobieranie obrazków kart...")

    # Przykład: możesz pobrać darmowe karty stąd:
    # https://github.com/hayeah/playing-cards-assets
    # lub stworzyć własne

    # Utwórz katalog na karty
    cards_dir = Path("assets/cards")
    cards_dir.mkdir(parents=True, exist_ok=True)

    print(f"Obrazki kart powinny być umieszczone w katalogu: {cards_dir.absolute()}")
    print("Nazwy plików powinny być w formacie: 2S.png, KH.png, AS.png itp.")
    print("Oraz plik back.png dla rewersu karty")

    # Tu możesz dodać kod do automatycznego pobierania kart
    # z publicznego repozytorium