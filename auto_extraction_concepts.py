import pandas as pd
import requests
import re
from collections import defaultdict

# 1. Charger le fichier des formations
df = pd.read_csv("formations_enrichies_mistral.csv")
descriptions = df["generated_description"].dropna().tolist()

# 2. Extraire les mots-clés par regex intelligente
def extraire_mots_cles(text):
    mots = re.findall(r'\b[a-zA-Zéèàêâîôûçëïü-]{5,}\b', text.lower())
    stopwords = {"cours", "formation", "apprendre", "professeur", "module", "connaissances", "vidéo", "entreprise", "compétences"}
    return [m for m in set(mots) if m not in stopwords]

# 3. Appel à Ollama pour générer la définition
def generer_definition(concept):
    prompt = f"Explique clairement et professionnellement ce qu'est : {concept}"
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    if response.status_code == 200:
        return response.json()["response"].strip()
    else:
        return "Erreur lors de la génération"

# 4. Extraire tous les mots uniques
concepts_uniques = set()
for description in descriptions:
    concepts_uniques.update(extraire_mots_cles(description))

# 5. Générer et stocker les définitions
definitions = []
déjà_vu = set()
for mot in sorted(concepts_uniques):
    if mot not in déjà_vu:
        print(f"🧠 Génération de la définition pour : {mot}")
        définition = generer_definition(mot)
        definitions.append({"concept": mot, "definition": définition})
        déjà_vu.add(mot)

# 6. Sauvegarder dans un CSV
df_result = pd.DataFrame(definitions)
df_result.to_csv("concepts.csv", index=False, encoding="utf-8")
print("\n✅ Fichier 'concepts.csv' généré avec succès.")
