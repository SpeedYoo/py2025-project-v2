# Specyfikacja GUI dla gry w pokera pięciokartowego

## 1. Główne okno

Pasek menu z opcjami:

- Nowa gra – uruchamia rozgrywkę z wybraną liczbą botów.
- Zapisz grę – zapisuje bieżący stan do pliku.
- Wczytaj grę – przywraca stan z wcześniej zapisanego pliku.
- Wyjście – zamyka aplikację.

## 2. Panel graczy
- Wyświetla listę uczestników (boty + gracz):
- Nazwa (np. „Bot 1”, „Ty”) i aktualny stan żetonów.
- Ikonki reprezentujące ich karty (odwrócone u botów, odkryte dla gracza).

## 3. Panel kart gracza

Pięć miejsc na karty użytkownika:

- Po rozdaniu pokazują obrazki kart.
- W fazie wymiany każde miejsce można kliknąć, by je zaznaczyć/odznaczyć.

## 4. Panel akcji

Przyciski dostosowane do fazy rozgrywki:

- Zakładów: „Check/Call”, „Raise” (z polem na kwotę), „Fold”.
- Wymiany: „Wymień zaznaczone karty” (widoczny tylko w fazie draw).

## 5. Informacje o stanie gry

Etykieta lub niewielki panel pokazujący:

- Wysokość puli (pot).
- Obecną fazę rundy („Pre-bet”, „Wymiana”, „Showdown”).

## 6. Integracja z modułem sesji

**Zapis:** GUI pobiera z silnika stan gry i przekazuje go SessionManagerowi, który zapisuje do pliku.

**Odczyt:** GUI wywołuje SessionManager, odtwarza stan w silniku, a następnie odświeża wszystkie elementy widoku.

## 7. Przepływ interakcji

- Użytkownik wybiera „Nowa gra” lub „Wczytaj grę” z menu.
- W fazie zakładów podejmuje decyzje przyciskami „Call/Check”, „Raise” lub „Fold”.
- Po rundzie zakładów przełącza się automatycznie do fazy wymiany – gracz zaznacza karty i klika „Wymień”.
- Następuje showdown – system porównuje układy, ogłasza zwycięzcę, aktualizuje stan żetonów.
- Po każdym rozdaniu grę można zapisać lub wczytać, by wznowić rozgrywkę później.
