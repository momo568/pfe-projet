import os
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image

def extract_pdf_to_markdown_with_images(pdf_file, output_md_file, output_images_dir):
    # Créer un répertoire pour les images
    os.makedirs(output_images_dir, exist_ok=True)

    # Ouvrir le fichier PDF
    with open(pdf_file, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        markdown_content = ""

        # Parcourir chaque page du PDF
        for page_number, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                # Ajouter le texte extrait au contenu Markdown
                markdown_content += text + "\n\n"

            # Convertir la page en image
            images = convert_from_path(pdf_file, first_page=page_number + 1, last_page=page_number + 1)
            for img_index, image in enumerate(images):
                image_filename = f"{output_images_dir}/page_{page_number + 1}_img_{img_index + 1}.png"
                image.save(image_filename, 'PNG')
                # Ajouter la référence de l'image au contenu Markdown
                markdown_content += f"![Image from page {page_number + 1}](./{output_images_dir}/{os.path.basename(image_filename)})\n\n"

    # Sauvegarder le contenu Markdown dans un fichier
    with open(output_md_file, 'w', encoding='utf-8') as file:
        file.write(markdown_content)

# Spécifiez le nom du fichier PDF, le nom du fichier de sortie Markdown et le répertoire pour les images
pdf_file = r"H:\TR__Formations_EKIP_\TW Formation-Prestation_V2 (1).pdf"
output_md_file = 'output_with_images.md'
output_images_dir = 'extracted_images'

# Extraire le contenu et les images
extract_pdf_to_markdown_with_images(pdf_file, output_md_file, output_images_dir)

print(f"Le contenu du PDF a été extrait et sauvegardé dans {output_md_file} avec les images dans le dossier {output_images_dir}.")