import json
import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime

print(f"[{datetime.now()}] Avvio Motore Completo: Scraping Lidl CH + AI...")

# ==========================================
# FASE 1: WEB SCRAPING SUL SITO LIDL CH
# ==========================================
def scarica_offerte_lidl():
    print("Tentativo di connessione al sito Lidl CH (Offerte)...")
    # URL della pagina delle offerte (potrebbe variare nel tempo)
    url = "https://www.lidl.ch/c/it-CH/azioni-della-settimana/a10103198"
    
    # Ci fingiamo un normale browser per non farci bloccare
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    offerte_estratte = []
    
    try:
        # Visitiamo il sito
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Analizziamo il codice HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo i blocchi che contengono i prodotti (Lidl usa spesso tag <article> o div specifici)
        prodotti_html = soup.find_all('article')
        
        for prodotto in prodotti_html[:10]: # Limitiamo alle prime 10 offerte per non confondere l'AI
            titolo_tag = prodotto.find(['h2', 'h3'])
            if titolo_tag:
                nome_prodotto = titolo_tag.text.strip()
                # Pulisce nomi troppo lunghi o con codici a capo
                nome_pulito = nome_prodotto.split('\n')[0]
                offerte_estratte.append(nome_pulito)
                
        return offerte_estratte
        
    except Exception as e:
        print(f"Scraping fallito (il sito potrebbe essere protetto o aver cambiato layout): {e}")
        return None

# Avviamo lo scraper
vere_offerte = scarica_offerte_lidl()

# ==========================================
# FASE 2: PREPARAZIONE DATI PER L'AI
# ==========================================
with open('data/products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

if vere_offerte and len(vere_offerte) > 0:
    print(f"🎉 SUCCESSO! Trovate offerte reali sul sito Lidl: {vere_offerte}")
    offerte_testo = ", ".join(vere_offerte)
    # In futuro qui possiamo aggiungere il codice per inserire automaticamente questi prodotti in products.json con i loro veri prezzi!
else:
    print("⚠️ Uso il piano B: Prendo le offerte salvate nel database locale.")
    prodotti_in_offerta = [p['name'] for p in products if p.get('inPromo', False)]
    offerte_testo = ", ".join(prodotti_in_offerta)

print(f"Ingredienti in offerta che userò per le ricette: {offerte_testo}")


# ==========================================
# FASE 3: INTELLIGENZA ARTIFICIALE (Con Retry)
# ==========================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Errore: GEMINI_API_KEY non trovata!")
    exit(1)

client = genai.Client(api_key=api_key)

prompt = f"""
Sei uno chef svizzero esperto in meal prep e risparmio. 
Crea un piano pasti di 3 giorni (Lunedì, Martedì, Mercoledì) per due piani dietetici: 'economico' e 'bilanciato'.
Regola TASSATIVA: Costruisci le ricette attorno a questi prodotti attualmente in offerta: {offerte_testo}.

Restituisci ESCLUSIVAMENTE un file JSON valido:
{{
  "economico": [
    {{
      "day": "Lunedì",
      "meals": [
        {{ "type": "Colazione", "name": "Nome", "qty": "Dosi", "steps": "Procedimento breve", "link": "" }},
        {{ "type": "Pranzo", "name": "Nome", "qty": "Dosi", "steps": "Procedimento", "link": "" }},
        {{ "type": "Cena", "name": "Nome", "qty": "Dosi", "steps": "Procedimento", "link": "" }}
      ]
    }}
  ],
  "bilanciato": [
    {{
      "day": "Lunedì",
      "meals": [
        {{ "type": "Colazione", "name": "Nome", "qty": "Dosi", "steps": "Procedimento", "link": "" }},
        {{ "type": "Pranzo", "name": "Nome", "qty": "Dosi", "steps": "Procedimento", "link": "" }},
        {{ "type": "Cena", "name": "Nome", "qty": "Dosi", "steps": "Procedimento", "link": "" }}
      ]
    }}
  ]
}}
"""

max_retries = 3

for attempt in range(max_retries):
    try:
        print(f"Contatto Gemini (Tentativo {attempt + 1}/{max_retries})...")
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        
        result_text = response.text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        new_recipes = json.loads(result_text.strip())
        
        with open('data/recipes.json', 'w', encoding='utf-8') as f:
            json.dump(new_recipes, f, indent=2, ensure_ascii=False)
            
        print("✅ Successo! Nuove ricette salvate in recipes.json.")
        break

    except Exception as e:
        print(f"Errore AI: {e}")
        if attempt < max_retries - 1:
            print("Server occupati. Attendo 15 secondi...")
            time.sleep(15)
        else:
            print("❌ Tentativi esauriti. Riproverà al prossimo giro.")
