import json
import os
import google.generativeai as genai
from datetime import datetime

print(f"[{datetime.now()}] Avvio generazione intelligente del Meal Plan...")

# 1. Configura la chiave API (che metteremo nei segreti di GitHub)
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Errore: GEMINI_API_KEY non trovata. Configura i Secrets su GitHub!")
    exit(1)

genai.configure(api_key=api_key)
# Usiamo il modello Flash, velocissimo e gratuito
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Leggi i prodotti dal database per capire cosa è in offerta
with open('data/products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Trova i prodotti attualmente in promo (inPromo == true)
prodotti_in_offerta = [p['name'] for p in products if p.get('inPromo', False)]
offerte_testo = ", ".join(prodotti_in_offerta)
print(f"Prodotti in offerta trovati: {offerte_testo}")

# 3. Il "Prompt": le istruzioni per l'Intelligenza Artificiale
prompt = f"""
Sei un nutrizionista e chef esperto in meal prep. 
Crea un piano pasti di 3 giorni (Lunedì, Martedì, Mercoledì) per due piani dietetici: 'economico' e 'bilanciato'.
Regola fondamentale: DEVI includere il più possibile questi ingredienti in offerta: {offerte_testo}.

Restituisci ESCLUSIVAMENTE un file JSON valido che segua ESATTAMENTE questa struttura. Non usare formattazioni Markdown, solo il JSON puro:
{{
  "economico": [
    {{
      "day": "Lunedì",
      "meals": [
        {{ "type": "Colazione", "name": "Nome Ricetta", "qty": "Dosi per 1 persona", "steps": "Procedimento", "link": "" }},
        {{ "type": "Pranzo", "name": "Nome Ricetta", "qty": "Dosi per 1 persona", "steps": "Procedimento", "link": "" }},
        {{ "type": "Cena", "name": "Nome Ricetta", "qty": "Dosi per 1 persona", "steps": "Procedimento", "link": "" }}
      ]
    }}
  ],
  "bilanciato": [
    // Stessa struttura per il bilanciato
  ]
}}
Assicurati di generare Lunedì, Martedì e Mercoledì per entrambi i piani.
"""

# 4. Chiama l'AI
try:
    response = model.generate_content(prompt)
    
    # Pulisce la risposta da eventuali backtick del markdown ```json ... ```
    result_text = response.text.strip()
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
        
    new_recipes = json.loads(result_text.strip())
    
    # 5. Salva le nuove ricette
    with open('data/recipes.json', 'w', encoding='utf-8') as f:
        json.dump(new_recipes, f, indent=2, ensure_ascii=False)
        
    print("Successo! Nuove ricette generate e salvate in recipes.json.")

except Exception as e:
    print(f"Errore durante la generazione o il salvataggio: {e}")
