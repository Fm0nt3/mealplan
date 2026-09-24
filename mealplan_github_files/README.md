# MealPlan Lidl CH
App web per una persona con piano pasti, budget e lista della spesa.

## Pubblicazione
Repository > Settings > Pages > Source: GitHub Actions.

## Aggiornamento
GitHub Actions esegue il controllo ogni lunedì alle 06:00 Europe/Zurich.
L'updater incluso controlla il sito ufficiale Lidl e aggiorna il timestamp, ma non sostituisce
automaticamente i prezzi con dati non verificati. Il parser dei prezzi va adattato alla struttura
corrente del sito Lidl prima di considerarlo un aggiornamento prezzi completo.
