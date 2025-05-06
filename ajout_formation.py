import pandas as pd

# 🔹 1. Charger le fichier existant
df = pd.read_csv("formations_enrichies_mistral.csv")

# 🔹 2. Définir la nouvelle formation
nouvelle_formation = {
    "title": "Formation Métiers du Financement",
    "generated_description": """Cette formation en ligne offre une compréhension complète des métiers du financement. Elle couvre les fondamentaux des crédits (définition, paramètres, amortissements), les différents types de crédits (consommation, leasing, révolving), ainsi que les aspects pratiques tels que le calcul des échéances, la gestion du risque et les produits financiers spécialisés.

Idéale pour les professionnels du secteur bancaire, du crédit ou de la gestion d'actifs, cette formation vous permettra de maîtriser les crédits classiques, le crédit-bail, les crédits aux entreprises, la location longue durée, le crédit immobilier et les spécificités du révolving.

À travers une approche progressive et structurée, vous serez guidé pas à pas dans l’analyse, la simulation et la compréhension des mécanismes financiers modernes. Une excellente base pour ceux qui souhaitent évoluer dans le financement ou approfondir leur expertise en matière de crédit.""",
    "url": "/local/formation-metiers-financement"
}

# 🔹 3. Ajouter la nouvelle ligne
df = pd.concat([df, pd.DataFrame([nouvelle_formation])], ignore_index=True)

# 🔹 4. Sauvegarder dans un nouveau fichier (sécurité si le fichier est ouvert)
nouveau_nom = "formations_enrichies_mistral_avec_financement.csv"
df.to_csv(nouveau_nom, index=False)

print(f"✅ Formation ajoutée avec succès dans le fichier : {nouveau_nom}")
