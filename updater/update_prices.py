import json
import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime

print(f"[{datetime.now()}] Avvio Motore Completo: Scraping Lidl CH + AI...")

# ==========================================
# FASE 1: WEB SCRAPING SUL SITO LIDL CH (Ricerca Ampia)
# ==========================================
def scarica_offerte_lidl():
    print("Tentativo di connessione al sito Lidl CH (Offerte)...")
    url = "https://www.lidl.ch/c/it-CH/azioni-della-settimana/a10103198"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    offerte_estratte = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # RICERCA AGGRESSIVA: Cerchiamo tutti i titoli nella pagina
        for tag in soup.find_all(['h3', 'h2']):
            testo = tag.text.strip()
            # Escludiamo titoli generici del sito o testi troppo corti
            parole_ignorate = ["Offerte", "Azioni", "Newsletter", "Servizio", "Lidl", "Menu", "Filtra", "Categorie"]
            
            if len(testo) > 4 and not any(parola.lower() in testo.lower() for parola in parole_ignorate):
                offerte_estratte.append(testo)
                
        # Rimuoviamo i doppioni e prendiamo solo i primi 10 prodotti veri
        offerte_uniche = list(dict.fromkeys(offerte_estratte))
        return offerte_uniche[:10]
        
    except Exception as e:
        print(f"Scraping fallito: {e}")
        return None

vere_offerte = scarica_offerte_lidl()

        # Costruiamo il link completo
        if not link_offerte.startswith('http'):
            link_offerte = base_url + link_offerte
            
        print(f"Trovato il link aggiornato della settimana: {link_offerte}")
        
        # SECONDO SALTO: Visitiamo la pagina vera e propria delle offerte
        response_offerte = requests.get(link_offerte, headers=headers, timeout=15)
        soup_offerte = BeautifulSoup(response_offerte.text, 'html.parser')
        
        # Estraiamo i prodotti
        prodotti_html = soup_offerte.find_all('article')
        for prodotto in prodotti_html[:10]:
            titolo_tag = prodotto.find(['h2', 'h3'])
            if titolo_tag:
                nome_pulito = titolo_tag.text.strip().split('\n')[0]
                offerte_estratte.append(nome_pulito)
                
        return offerte_estratte
        
    except Exception as e:
        print(f"Scraping fallito durante la navigazione autonoma: {e}")
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
