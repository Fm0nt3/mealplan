import json
import os
from datetime import datetime

# Percorso del file JSON
file_path = 'data/products.json'

print(f"[{datetime.now()}] Controllo aggiornamenti prezzi in corso...")

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Per ora lo script formatta solo il JSON per assicurarsi che sia leggibile.
    # In futuro qui inseriremo la logica per aggiornare le offerte del Lidl.
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print("File products.json verificato e formattato con successo.")
else:
    print("Errore: file products.json non trovato.")
