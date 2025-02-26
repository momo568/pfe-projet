import camelot

# Chemin du fichier PDF (Utilisez '\\' au lieu de '\')
pdf_path = "F:\\app\\Downloads\\TW-Formation Métiers (1) (1).pdf"

# Extraction des tableaux
tables = camelot.read_pdf(pdf_path, pages="1", flavor="stream")

# Affichage des résultats
print(tables)
