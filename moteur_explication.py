import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# 1. Charger les descriptions
df = pd.read_csv("formations_enrichies_mistral_avec_financement.csv")
texts = df["generated_description"].dropna().tolist()

# 2. Vectoriser les descriptions
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(texts, show_progress_bar=True)

# 3. Créer l'index FAISS
dimension = embeddings[0].shape[0]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings).astype("float32"))

# 4. Fonction : donner une explication détaillée
def expliquer_concept(mot_cle):
    query_embedding = model.encode([mot_cle])
    distances, indices = index.search(np.array(query_embedding).astype("float32"), 1)
    idx = indices[0][0]
    description = texts[idx]
    
    print(f"\n🧠 Explication pour : « {mot_cle} »\n")
    print(description.strip())
    print("=" * 100)

# 5. Boucle interactive
if __name__ == "__main__":
    while True:
        mot = input("🔎 Tape un mot ou concept à expliquer (ou 'exit') : ")
        if mot.lower() in ["exit", "quit"]:
            print("👋 À bientôt !")
            break
        expliquer_concept(mot)
