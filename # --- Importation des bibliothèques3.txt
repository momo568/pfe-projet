# --- Importation des bibliothèques nécessaires ---
import os
import re
import pdfplumber
import tkinter as tk
from tkinter import filedialog
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageOps
import base64
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from IPython.display import display, HTML
import ollama
import matplotlib.pyplot as plt

# Import explicite de read_pdf depuis Camelot
from camelot import read_pdf

# Assurez-vous que les ressources NLTK sont téléchargées
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')


# --- Fonction de sélection de fichier PDF ---
def upload_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Sélectionnez un fichier PDF",
        filetypes=[("Fichiers PDF", "*.pdf")]
    )
    return file_path


# --- Fonctions utilitaires de base ---
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name.lower().replace(" ", "_"))

def clean_text(text):
    text = re.sub(r'\b\d+\b', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_chapter_name_from_page(pdf, page_num):
    try:
        page = pdf.pages[page_num - 1]
        text = page.extract_text()
        if not text:
            return None
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            chapter_heading_pattern = re.compile(r'^(CHAPTER|CHAPITRE)\s+(\d+)\s*[\-–—−:]\s*(.+)$', re.IGNORECASE)
            chapter_multiline_pattern = re.compile(r'^(CHAPTER|CHAPITRE)\s+(\d+)\s*$', re.IGNORECASE)
            match = chapter_heading_pattern.match(line)
            if match:
                chapter_num = int(match.group(2))
                chapter_title = match.group(3).strip()
                sanitized_title = sanitize_filename(chapter_title)
                return f"chapitre_{chapter_num}_{sanitized_title}".lower()
            else:
                match = chapter_multiline_pattern.match(line)
                if match:
                    chapter_num = int(match.group(2))
                    current_index = lines.index(line)
                    if current_index + 1 < len(lines):
                        next_line = lines[current_index + 1].strip()
                        if next_line:
                            chapter_title = next_line
                            sanitized_title = sanitize_filename(chapter_title)
                            return f"chapitre_{chapter_num}_{sanitized_title}".lower()
        return None
    except Exception as e:
        print(f"Error extracting chapter name from page {page_num}: {e}")
        return None

def preprocess_text(text):
    irrelevant_keywords = ["cover", "table of contents", "thank you", "agenda", "plan", "merci"]
    for keyword in irrelevant_keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            return None
    lemmatizer = WordNetLemmatizer()
    tokens = word_tokenize(text)
    lemmatized_text = ' '.join([lemmatizer.lemmatize(token) for token in tokens])
    return lemmatized_text.strip()

def group_similar_sections(sections):
    cleaned_sections = {name: preprocess_text(content) for name, content in sections.items()}
    cleaned_sections = {name: content for name, content in cleaned_sections.items() if content}
    section_names = list(cleaned_sections.keys())
    section_contents = list(cleaned_sections.values())
    if not section_contents:
        return {}
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(section_contents)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    grouped_sections = defaultdict(str)
    threshold = 0.5
    for i in range(len(section_names)):
        for j in range(i + 1, len(section_names)):
            if similarity_matrix[i][j] > threshold:
                grouped_sections[section_names[i]] += cleaned_sections[section_names[j]] + "\n"
    final_grouped = {key: cleaned_sections[key] + "\n" + content for key, content in grouped_sections.items()}
    return final_grouped

def save_grouped_sections(grouped_sections, output_dir="output/grouped_sections"):
    os.makedirs(output_dir, exist_ok=True)
    for group_name, content in grouped_sections.items():
        filename = f"group_{group_name.replace(' ', '_')}.txt"
        file_path = os.path.join(output_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    if grouped_sections:
        print(f"Sections groupées sauvegardées dans le répertoire '{output_dir}'.")
    else:
        print("Aucune section groupée à sauvegarder.")


# --- Extraction du contenu du PDF (sections) ---
def extract_sections(pdf_path, start_page=1, end_page=None):
    sections = defaultdict(str)
    current_section = None
    with pdfplumber.open(pdf_path) as pdf:
        if end_page is None:
            end_page = len(pdf.pages)
        for page_num in range(start_page - 1, end_page):
            page = pdf.pages[page_num]
            text = page.extract_text() or ""
            tables = page.extract_tables()
            page_content = ""
            if text:
                page_content += text + "\n"
            if tables:
                for table in tables:
                    for row in table:
                        if row:
                            filtered_row = [str(cell) for cell in row if cell is not None]
                            page_content += "\t".join(filtered_row) + "\n"
            if not page_content.strip():
                continue
            lines = page_content.split('\n')
            if lines:
                first_line = lines[0].strip()
                words = first_line.split()
                if len(words) >= 2:
                    section_name = ' '.join(words[:2])
                else:
                    section_name = first_line
                if current_section and current_section != section_name:
                    sections[current_section] += "\n"
                current_section = section_name
                sections[current_section] += page_content + "\n"
    return sections

def save_sections(sections, output_dir="output/chapters"):
    os.makedirs(output_dir, exist_ok=True)
    for section_name, content in sections.items():
        filename = f"{section_name.replace(' ', '_')}.txt"
        file_path = os.path.join(output_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"Sections sauvegardées dans le répertoire '{output_dir}'.")

def read_sections_from_files(directory):
    sections = {}
    if not os.path.isdir(directory):
        return sections
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r', encoding="utf-8") as f:
                sections[filename] = f.read()
    return sections


# --- Extraction des images des tableaux via Camelot ---
def extract_table_images_camelot(pdf_path, output_dir="output/table_images_camelot", dpi=300):
    os.makedirs(output_dir, exist_ok=True)
    tables = read_pdf(pdf_path, pages="all", flavor="stream")
    if not tables or len(tables) == 0:
        print("Aucun tableau détecté par Camelot.")
        return
    for i, table in enumerate(tables):
        df = table.df
        fig, ax = plt.subplots(figsize=(df.shape[1]*1.5, df.shape[0]*0.5))
        ax.axis('tight')
        ax.axis('off')
        ax.table(cellText=df.values, colLabels=df.columns, loc='center')
        output_file = os.path.join(output_dir, f"table_camelot_{i+1}.png")
        plt.savefig(output_file, bbox_inches='tight', dpi=dpi)
        plt.close(fig)
        print(f"Table image extracted (Camelot): {output_file}")

def display_camelot_table_images(output_dir="output/table_images_camelot"):
    html_content = "<html><body><h1>Images des tableaux extraits par Camelot</h1><div style='display:flex; flex-wrap: wrap;'>"
    for filename in os.listdir(output_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")):
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            ext = filename.split('.')[-1].lower()
            mime_type = "image/png"
            if ext in ["jpg", "jpeg"]:
                mime_type = "image/jpeg"
            elif ext == "gif":
                mime_type = "image/gif"
            html_content += f"<div style='margin:10px;'><img src='data:{mime_type};base64,{encoded}' style='max-width:400px;'/><p>{filename}</p></div>"
    html_content += "</div></body></html>"
    display(HTML(html_content))


# --- Extraction des autres images (figures non-tableaux) ---
def extract_images(pdf_path, figure_pages, output_dir="output/figures"):
    os.makedirs(output_dir, exist_ok=True)
    extracted_images = []
    import fitz
    with fitz.open(pdf_path) as pdf:
        for page_num in figure_pages:
            if page_num < 1 or page_num > pdf.page_count:
                print(f"Page {page_num} hors limite. Passage.")
                continue
            page = pdf.load_page(page_num - 1)
            image_list = page.get_images(full=True)
            if not image_list:
                print(f"Aucune image trouvée sur la page {page_num}.")
                continue
            for img_index, img in enumerate(image_list, start=1):
                xref = img[0]
                pix = fitz.Pixmap(pdf, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                image_filename = f"page_{page_num}_img_{img_index}.png"
                image_path = os.path.join(output_dir, image_filename)
                pix.save(image_path)
                extracted_images.append(image_path)
                print(f"Image extraite : {image_filename}")
    return extracted_images

def display_images_and_descriptions(sample_data):
    html_content = """
    <html>
    <head>
        <style>
            .container { display: flex; flex-wrap: wrap; }
            .figure { display: flex; margin-bottom: 20px; width: 100%; }
            .figure img { max-width: 300px; margin-right: 20px; }
            .description { max-width: 600px; }
        </style>
    </head>
    <body>
        <h1>Rapport de descriptions des figures</h1>
        <div class="container">
    """
    for image_path, description in sample_data:
        try:
            with open(image_path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                extension = os.path.splitext(image_path)[1].lower()
                mime_types = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.tiff': 'image/tiff'
                }
                mime_type = mime_types.get(extension, 'image/png')
                img_src = f"data:{mime_type};base64,{encoded_string}"
        except Exception as e:
            print(f"Erreur lors de l'encodage de l'image {image_path}: {e}")
            img_src = ""
        html_content += f"""
            <div class="figure">
                <img src="{img_src}" alt="Image de figure">
                <div class="description">
                    <p>{description}</p>
                </div>
            </div>
        """
    html_content += """
        </div>
    </body>
    </html>
    """
    display(HTML(html_content))


# --- OCR et génération de descriptions pour les figures de tableaux ---
def extract_text_from_image(image_path, tesseract_cmd=None):
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    try:
        image = Image.open(image_path)
        image = image.convert('L')
        image = ImageOps.autocontrast(image)
        text = pytesseract.image_to_string(image, config="--psm 3")
        return text.strip()
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte de {image_path}: {e}")
        return ""

def generate_description_with_llama(text, model_name="llama3:8b"):
    try:
        prompt = (
            "This text is extracted from a table figure in a risk management document:\n"
            f"{text}\n\n"
            "Please generate a detailed explanation of this table based on the extracted text."
        )
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}]
        )
        description = response['message']['content'].strip()
        return description
    except Exception as e:
        print(f"Erreur lors de la génération de la description avec LLaMA: {e}")
        return "La génération de la description a échoué."

def process_images_with_llama(images, tesseract_cmd, texts_dir="output/texts", descriptions_dir="output/descriptions", model_name="llama3:8b"):
    os.makedirs(texts_dir, exist_ok=True)
    os.makedirs(descriptions_dir, exist_ok=True)
    descriptions = {}
    for image_path in images:
        image_filename = os.path.basename(image_path)
        base_name, _ = os.path.splitext(image_filename)
        text_file = os.path.join(texts_dir, f"{base_name}.txt")
        description_file = os.path.join(descriptions_dir, f"{base_name}_description.txt")
        if os.path.isfile(description_file):
            with open(description_file, "r", encoding="utf-8") as f:
                description = f.read().strip()
            print(f"Description existante chargée pour {image_filename}")
        else:
            if os.path.isfile(text_file):
                with open(text_file, "r", encoding="utf-8") as f:
                    extracted_text = f.read().strip()
                print(f"Texte extrait existant chargé pour {image_filename}")
            else:
                print(f"Extraction du texte depuis {image_filename}...")
                extracted_text = extract_text_from_image(image_path, tesseract_cmd)
                if not extracted_text:
                    print(f"Aucun texte extrait de {image_path}. Génération de description ignorée.")
                    extracted_text = "Aucun texte extrait de l'image."
                else:
                    print(f"Texte extrait depuis {image_filename}.")
                with open(text_file, "w", encoding="utf-8") as f:
                    f.write(extracted_text)
                print(f"Texte sauvegardé pour {image_filename}")
            print(f"Génération de la description pour {image_filename}...")
            description = generate_description_with_llama(extracted_text, model_name)
            with open(description_file, "w", encoding="utf-8") as f:
                f.write(description)
            print(f"Description sauvegardée pour {image_filename}\n")
        descriptions[image_path] = description
    return descriptions

def display_images_and_descriptions(sample_data):
    html_content = """
    <html>
    <head>
        <style>
            .container { display: flex; flex-wrap: wrap; }
            .figure { display: flex; margin-bottom: 20px; width: 100%; }
            .figure img { max-width: 300px; margin-right: 20px; }
            .description { max-width: 600px; }
        </style>
    </head>
    <body>
        <h1>Rapport de descriptions des figures de tableaux</h1>
        <div class="container">
    """
    for image_path, description in sample_data:
        try:
            with open(image_path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                extension = os.path.splitext(image_path)[1].lower()
                mime_types = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.tiff': 'image/tiff'
                }
                mime_type = mime_types.get(extension, 'image/png')
                img_src = f"data:{mime_type};base64,{encoded_string}"
        except Exception as e:
            print(f"Erreur lors de l'encodage de l'image {image_path}: {e}")
            img_src = ""
        html_content += f"""
            <div class="figure">
                <img src="{img_src}" alt="Image de figure">
                <div class="description">
                    <p>{description}</p>
                </div>
            </div>
        """
    html_content += """
        </div>
    </body>
    </html>
    """
    display(HTML(html_content))


# --- Mapping des descriptions aux chapitres ---
def mapping_descriptions_to_chapters(pdf_path):
    chapters_dir = "output/chapters"
    cleaned_chapters_dir = "output/cleaned_chapters"
    descriptions_dir = "output/descriptions"
    final_chapters_dir = "output/final_chapters"
    os.makedirs(cleaned_chapters_dir, exist_ok=True)
    os.makedirs(final_chapters_dir, exist_ok=True)

    print("Cleaning chapters...")
    chapters = {}
    for filename in os.listdir(chapters_dir):
        if filename.endswith(".txt"):
            chapter_path = os.path.join(chapters_dir, filename)
            with open(chapter_path, "r", encoding="utf-8") as f:
                text = f.read()
            cleaned = clean_text(text)
            cleaned_filename = filename.replace("chapitre_", "cleaned_chapitre_")
            cleaned_path = os.path.join(cleaned_chapters_dir, cleaned_filename)
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(cleaned)
            chapter_key = filename.replace(".txt", "").lower()
            chapters[chapter_key] = cleaned
            print(f"Cleaned and saved {filename} to {cleaned_chapters_dir}")
    print("All chapters cleaned.\n")

    print("Mapping figure descriptions to chapters...")
    with pdfplumber.open(pdf_path) as pdf:
        final_chapters = {chapter: text for chapter, text in chapters.items()}
        mapping_info = []
        pattern = re.compile(r'page_(\d+)_table_\d+_description\.txt', re.IGNORECASE)
        for desc_filename in os.listdir(descriptions_dir):
            if desc_filename.endswith("_description.txt"):
                desc_path = os.path.join(descriptions_dir, desc_filename)
                match = pattern.match(desc_filename)
                if not match:
                    print(f"Filename {desc_filename} does not match expected pattern. Skipping.")
                    continue
                page_num = int(match.group(1))
                search_page = page_num
                chapter_name = None
                while search_page >= 1:
                    chapter_name = get_chapter_name_from_page(pdf, search_page)
                    if chapter_name:
                        break
                    search_page -= 1
                if not chapter_name:
                    print(f"Could not determine chapter for page {page_num} after backtracking. Skipping.")
                    continue
                if chapter_name not in final_chapters:
                    print(f"Chapter {chapter_name} not found in cleaned chapters. Skipping.")
                    continue
                with open(desc_path, "r", encoding="utf-8") as f:
                    description_text = f.read().strip()
                final_chapters[chapter_name] += f"\n\nTable Description from page {page_num}:\n{description_text}"
                mapping_info.append((desc_filename, chapter_name, page_num))
                print(f"Added {desc_filename} to {chapter_name}")
    print("\nAll descriptions mapped to chapters.\n")

    print("Saving final chapters with appended descriptions...")
    for chapter, text in final_chapters.items():
        final_path = os.path.join(final_chapters_dir, f"{chapter}.txt")
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved final chapter to {final_path}")
    print("All final chapters saved.\n")

    print("Mapping of descriptions to chapters:")
    for desc, chap, page in mapping_info:
        chap_readable = chap.replace("_", " ").title()
        print(f" - {desc} (page {page}) was added to {chap_readable}")
    print("\nProcessing completed successfully.")


# --- Fonction principale ---
def main():
    # Étape 1 : Sélection et extraction du PDF (sections, OCR, tableaux, descriptions)
    pdf_path = upload_file()
    if not pdf_path:
        print("Aucun fichier sélectionné.")
        return

    print("Extracting sections from the PDF...")
    sections = extract_sections(pdf_path, start_page=1)
    if not sections:
        print("Aucune section trouvée.")
    else:
        print("Sections found:")
        for name, content in sections.items():
            print(f"{name}: {len(content.splitlines())} lines")
    save_sections(sections, output_dir="output/chapters")

    # Regroupement des sections (optionnel)
    sections = read_sections_from_files("output/chapters")
    grouped_sections = group_similar_sections(sections)
    save_grouped_sections(grouped_sections)

    # Étape 2 : Extraction des figures de tableaux via Camelot
    print("Extracting table images from the PDF using Camelot...")
    camelot_output_dir = "output/table_images_camelot"
    os.makedirs(camelot_output_dir, exist_ok=True)
    tables = read_pdf(pdf_path, pages="all", flavor="stream")
    if not tables or len(tables) == 0:
        print("Aucun tableau détecté par Camelot.")
    else:
        for i, table in enumerate(tables):
            df = table.df
            fig, ax = plt.subplots(figsize=(df.shape[1]*1.5, df.shape[0]*0.5))
            ax.axis('tight')
            ax.axis('off')
            ax.table(cellText=df.values, colLabels=df.columns, loc='center')
            output_file = os.path.join(camelot_output_dir, f"table_camelot_{i+1}.png")
            plt.savefig(output_file, bbox_inches='tight', dpi=300)
            plt.close(fig)
            print(f"Table image extracted (Camelot): {output_file}")
    print("Displaying table images extracted by Camelot...")
    display_camelot_table_images(output_dir=camelot_output_dir)

    # Étape 3 : OCR et génération de descriptions pour les figures de tableaux (Camelot)
    table_images = []
    for filename in os.listdir(camelot_output_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")):
            table_images.append(os.path.join(camelot_output_dir, filename))
    if table_images:
        tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if not os.path.isfile(tesseract_cmd):
            print(f"Erreur : Tesseract introuvable à '{tesseract_cmd}'. Vérifiez le chemin.")
        else:
            descriptions = process_images_with_llama(table_images, tesseract_cmd,
                                                     texts_dir="output/texts",
                                                     descriptions_dir="output/descriptions")
            print("Descriptions generated for table images.\n")
            if descriptions:
                sample_size = 3
                sample_data = list(descriptions.items())[:sample_size]
                display_images_and_descriptions(sample_data)
            else:
                print("Aucune description à afficher.")
    else:
        print("Aucune image de tableau (Camelot) trouvée.")

    # Étape 4 : Mapping des descriptions aux chapitres
    print("Starting mapping of descriptions to chapters...")
    mapping_descriptions_to_chapters(pdf_path)
    print("Processing complete.")


if __name__ == "__main__":
    main()
