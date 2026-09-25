import json
import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime

print(f"[{datetime.now()}] Avvio Motore Completo: Scraping Lidl CH + AI...")

# ==========================================
# FASE 1: WEB SCRAPING SUL SITO LIDL CH (Aggiramento Firewall)
# ==========================================
import cloudscraper
from bs4 import BeautifulSoup
import requests # Teniamo questo per sicurezza

def scarica_offerte_lidl():
    print("Tentativo di connessione al sito Lidl CH (Offerte)...")
    url = "https://www.lidl.ch/c/it-CH/azioni-della-settimana/a10103198"
    
    offerte_estratte = []
    
    try:
        # Usiamo cloudscraper al posto di requests per aggirare i blocchi anti-bot
        scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        })
        
        response = scraper.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"Errore dal server: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # RICERCA MIRATA SUI PRODOTTI
        for tag in soup.find_all(['h3', 'h4', 'strong', 'div']):
            classe_tag = tag.get('class', [])
            classe_testo = " ".join(classe_tag).lower()
            
            if tag.name in ['h4', 'strong'] or 'title' in classe_testo or 'headline' in classe_testo:
                testo = tag.text.strip()
                
                parole_ignorate = [
                    "Offerte", "Azioni", "Newsletter", "Servizio", "Lidl", "Menu", 
                    "Filtra", "Categorie", "Frutta", "verdura", "forno", "Pesce", 
                    "carne", "Lista filiali", "Visualizza", "Scopri", 
                    "browser", "supported", "caution", "attention", "javascript"
                ]
                
                if len(testo) > 3 and not any(parola.lower() in testo.lower() for parola in parole_ignorate):
                    nome_pulito = testo.split('\n')[0].strip()
                    offerte_estratte.append(nome_pulito)
                
        offerte_uniche = list(dict.fromkeys(offerte_estratte))
        return offerte_uniche[:15]
        
    except Exception as e:
        print(f"Scraping fallito (il firewall potrebbe aver bloccato l'IP di GitHub): {e}")
        return None

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
Sei un nutrizionista e Masterchef svizzero. 
Devi creare un piano pasti di 7 giorni per due piani dietetici: 'economico' e 'bilanciato'.
Regola TASSATIVA: Costruisci le ricette attorno a questi prodotti: {offerte_testo}.

REGOLE PER COMPILARE IL MENU:
1. "qty": Elenco ESATTO di tutti gli ingredienti necessari con grammi/quantità (es. "150g pollo, 60g riso, 10g burro, sale, pepe").
2. "steps": Procedimento DETTAGLIATO, passo dopo passo, su come tagliare, cuocere e impiattare.
3. "link": Usa questo formato "https://www.google.com/search?q=ricetta+" seguito dalle parole principali del piatto separate dal segno +.

REGOLE PER LA LISTA DELLA SPESA ("shopping_list"):
Crea una singola lista della spesa che includa TUTTI gli ingredienti necessari per realizzare i menu (compresi pane, marmellata, spezie, ecc.). Unisci le quantità se un ingrediente serve in più ricette.

Restituisci ESCLUSIVAMENTE un file JSON valido che segua ESATTAMENTE questa struttura. Non usare formattazioni Markdown, solo il JSON puro:
{{
  "shopping_list": [
    {{ "item": "Petto di Pollo", "amount": "500g" }},
    {{ "item": "Marmellata di fragole", "amount": "1 vasetto" }},
    {{ "item": "Pane integrale", "amount": "1 filone" }}
  ],
  "economico": [
    {{
      "day": "Lunedì",
      "meals": [
        {{ "type": "Colazione", "name": "Nome", "qty": "Ingredienti", "steps": "Procedimento", "link": "https://www.google.com/search?q=..." }},
        {{ "type": "Pranzo", "name": "Nome", "qty": "Ingredienti", "steps": "Procedimento", "link": "https://www.google.com/search?q=..." }},
        {{ "type": "Cena", "name": "Nome", "qty": "Ingredienti", "steps": "Procedimento", "link": "https://www.google.com/search?q=..." }}
      ]
    }}
  ],
  "bilanciato": [
    // Stessa struttura per i 7 giorni
  ]
}}
"""max_retries = 3

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
