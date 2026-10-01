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
# FASE 2: PREPARAZIONE DATI PER L'AI (Catalogo Chiuso)
# ==========================================
with open('data/products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Creiamo le tre liste fondamentali per l'AI
catalogo_nomi = [p['name'] for p in products]
in_dispensa = [p['name'] for p in products if p.get('inCasa', False)]

if vere_offerte and len(vere_offerte) > 0:
    print(f"🎉 SUCCESSO! Offerte lette dal sito Lidl: {vere_offerte}")
    offerte_attive = vere_offerte
else:
    print("⚠️ Uso il piano B: Prendo le offerte salvate nel database locale (products.json).")
    offerte_attive = [p['name'] for p in products if p.get('inPromo', False)]

testo_catalogo = ", ".join(catalogo_nomi)
testo_dispensa = ", ".join(in_dispensa) if in_dispensa else "Nessuno"
testo_offerte = ", ".join(offerte_attive) if offerte_attive else "Nessuna"

# Queste righe ti faranno vedere tutto nel log!
print(f"🛒 Prodotti IN OFFERTA che l'AI dovrà usare: {testo_offerte}")
print(f"📦 Prodotti GIA' IN DISPENSA: {testo_dispensa}")
print(f"📚 Catalogo totale inviato all'AI: {len(catalogo_nomi)} prodotti.")

# ==========================================
# FASE 3: INTELLIGENZA ARTIFICIALE (Con Prompt Restrittivo)
# ==========================================
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

prompt = f"""
Sei un nutrizionista. Crea un piano pasti di 7 giorni per due piani: 'economico' e 'bilanciato'.

CATALOGO (PESCA SOLO DA QUI): [{testo_catalogo}]
OFFERTE: [{testo_offerte}]
DISPENSA (NON COMPRARE, L'UTENTE LI HA GIA'): [{testo_dispensa}]

REGOLE PER LE DUE LISTE DELLA SPESA:
Devi creare DUE liste separate: "shopping_list_economico" e "shopping_list_bilanciato".
Per ogni prodotto che decidi di usare, fai questo calcolo:
1. Somma i grammi totali usati nei 7 giorni per quel piano.
2. Guarda la grandezza della confezione nel nome del prodotto (es. 500g).
3. Dividi i grammi totali per la confezione e ARROTONDA PER ECCESSO (es. se ti servono 1200g di Broccoli (500g), devi calcolare "packages": 3).

Restituisci ESCLUSIVAMENTE un JSON puro con questa esatta struttura (NON DIMENTICARE IL CAMPO "packages"):
{{
  "shopping_list_economico": [
    {{ "item": "Broccoli (500g)", "packages": 3, "calculation": "Totale ricette 1.2kg, confezioni da 500g = 3 pacchi" }}
  ],
  "shopping_list_bilanciato": [
    {{ "item": "Petto di Pollo (500g)", "packages": 2, "calculation": "Totale ricette 800g, confezioni da 500g = 2 pacchi" }}
  ],
  "economico": [
    {{
      "day": "Lunedì",
      "meals": [
        {{ "type": "Colazione", "name": "Nome", "qty": "Ingredienti", "steps": "Procedimento", "link": "link_google" }}
      ]
    }}
  ],
  "bilanciato": [
    // Stessa struttura
  ]
}}
"""

max_retries = 6
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
            
        print("✅ Successo! Menu e lista della spesa intelligente salvati.")
        break

    except Exception as e:
        print(f"Errore AI: {e}")
        if attempt < max_retries - 1:
            print("Server occupati. Attendo 20 secondi prima di riprovare...")
            time.sleep(20)
        else:
            print("❌ Tentativi esauriti.")
