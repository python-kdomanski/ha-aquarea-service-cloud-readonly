# Historia zmian

## 0.2.0 — 2026-11-01

- Pierwsze wydanie przygotowane do instalacji przez HACS jako repozytorium niestandardowe.
- 30 sensorów statusu pompy, odczytywanych bezpośrednio z Service Cloud przez HTTPS.
- Trzy dodatkowe sensory historii: prąd zewnętrzny, pobór mocy podczas grzania i pobór mocy CWU.
- Odczyt historii co 5 minut, czas próbki w atrybutach oraz niedostępność próbek starszych niż 20 minut.
- Odseparowanie błędów historii od odczytów statusu.
- Polska i angielska wersja formularza konfiguracji, ikona i dokumentacja instalacji.
- Testy protokołu, tworzenia encji i obsługi historii oraz walidacja HACS/hassfest w GitHub Actions.

Status podstawowych sensorów potwierdzono w Home Assistant. Rozszerzenie historii
sprawdzono lokalnie i na dostarczonych próbkach odpowiedzi; wymaga potwierdzenia
odczytów trzech nowych encji po restarcie HA.
