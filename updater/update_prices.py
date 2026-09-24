import json
import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime

print(f"[{datetime.now()}] Avvio Motore Completo: Scraping Lidl CH + AI...")

# ==========================================
# FASE 1: WEB SCRAPING SUL SITO LIDL CH (Mirato sui Prodotti)
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
        
        # RICERCA MIRATA SUI PRODOTTI
        # Cerchiamo h3, h4, strong, e div che potrebbero essere i nomi dei prodotti (come "Spinacini bio")
        for tag in soup.find_all(['h3', 'h4', 'strong', 'div']):
            # Controlliamo se la classe dell'elemento assomiglia a un titolo (Lidl usa spesso 'title' o 'headline')
            classe_tag = tag.get('class', [])
            classe_testo = " ".join(classe_tag).lower()
            
            # Prendiamo il tag se è un h4/strong, OPPURE se ha una classe che indica che è un titolo
            if tag.name in ['h4', 'strong'] or 'title' in classe_testo or 'headline' in classe_testo:
                testo = tag.text.strip()
                
                # Lista nera: escludiamo i titoli grandi dei reparti e parole di menu
                parole_ignorate = [
                "Offerte", "Azioni", "Newsletter", "Servizio", "Lidl", "Menu", 
                "Filtra", "Categorie", "Frutta", "verdura", "forno", "Pesce", 
                "carne", "Lista filiali", "Visualizza", "Scopri", 
                "browser", "supported", "caution", "attention"
                ]        
                
                # Il testo deve essere lungo almeno 4 lettere e non essere nella lista nera
                if len(testo) > 3 and not any(parola.lower() in testo.lower() for parola in parole_ignorate):
                    # Togliamo roba inutile come spazi multipli o ritorni a capo
                    nome_pulito = testo.split('\n')[0].strip()
                    offerte_estratte.append(nome_pulito)
                
        # Come vedi dall'immagine, "Uva nera" è doppio. Questo comando rimuove i doppioni!
        offerte_uniche = list(dict.fromkeys(offerte_estratte))
        
        # Restituiamo i primi 15 prodotti trovati
        return offerte_uniche[:15]
        
    except Exception as e:
        print(f"Scraping fallito: {e}")
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
Devi creare un piano pasti di 7 giorni (Lunedì, Martedì, Mercoledì, Giovedì, Venerdì, Sabato, Domenica) per due piani dietetici: 'economico' e 'bilanciato'.
Regola TASSATIVA: Costruisci le ricette attorno a questi prodotti: {offerte_testo}.

REGOLE PER COMPILARE IL MENU:
1. "qty": Non scrivere solo "Dosi per 1". Devi fare un elenco ESATTO di tutti gli ingredienti necessari con grammi e millilitri (es. "150g pollo, 60g riso, 10g burro, sale, pepe").
2. "steps": Non essere riassuntivo. Scrivi un procedimento DETTAGLIATO, passo dopo passo, su come tagliare, cuocere e impiattare (es. "1. Taglia a cubetti. 2. Scalda la padella...").
3. "link": Crea un link di ricerca su Google per trovare ricette simili. Il link deve avere ESATTAMENTE questo formato: "https://www.google.com/search?q=ricetta+" seguito dalle parole principali del piatto separate dal segno +. (Esempio: per il "Pollo al forno", il link sarà "https://www.google.com/search?q=ricetta+pollo+al+forno").

Restituisci ESCLUSIVAMENTE un file JSON valido che segua ESATTAMENTE questa struttura. Non usare formattazioni Markdown, solo il JSON puro:
{{
  "economico": [
    {{
      "day": "Lunedì",
      "meals": [
        {{ "type": "Colazione", "name": "Nome", "qty": "Ingredienti esatti", "steps": "Procedimento lungo", "link": "https://www.google.com/search?q=..." }},
        {{ "type": "Pranzo", "name": "Nome", "qty": "Ingredienti esatti", "steps": "Procedimento lungo", "link": "https://www.google.com/search?q=..." }},
        {{ "type": "Cena", "name": "Nome", "qty": "Ingredienti esatti", "steps": "Procedimento lungo", "link": "https://www.google.com/search?q=..." }}
      ]
    }}
  ],
  "bilanciato": [
    {{
      "day": "Lunedì",
      "meals": [
        {{ "type": "Colazione", "name": "Nome", "qty": "Ingredienti esatti", "steps": "Procedimento lungo", "link": "https://www.google.com/search?q=..." }},
        {{ "type": "Pranzo", "name": "Nome", "qty": "Ingredienti esatti", "steps": "Procedimento lungo", "link": "https://www.google.com/search?q=..." }},
        {{ "type": "Cena", "name": "Nome", "qty": "Ingredienti esatti", "steps": "Procedimento lungo", "link": "https://www.google.com/search?q=..." }}
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
