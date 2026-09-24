import json
from datetime import datetime
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"data/products.json"
url="https://www.lidl.ch/"
r=requests.get(url,headers={"User-Agent":"MealPlanLidlCH/1.0"},timeout=30)
r.raise_for_status()
d=json.loads(p.read_text(encoding="utf-8"))
d["checked_at"]=datetime.now().astimezone().isoformat(timespec="minutes")
d["source_status"]="Sito Lidl raggiunto; prezzi precedenti conservati finché non viene verificato un parser strutturato."
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
