# === Partie 1 : IMPORTS et CONFIGURATIONS ===
import os
import random
import re
import time
import unicodedata
import pyttsx3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import gc

from pathlib import Path
from io import BytesIO
from moviepy.editor import TextClip, ImageClip, ColorClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, ImageSequenceClip
from moviepy.audio.AudioClip import AudioClip
from moviepy.config import change_settings
import drawbot_skia.drawbot as drawBot

from sklearn import decomposition, cluster, manifold, preprocessing
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, accuracy_score, classification_report, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

# Config ImageMagick
change_settings({
    "IMAGEMAGICK_BINARY": r"H:\\ImageMagick-7.1.1-Q16\\magick.exe"
})

# Chemins
INPUT_MD = Path(r"H:\\formation-main\\eca1.md")  # <- adapte ton chemin ici
LOGO_PATH = Path(r"H:\\ZKoou2hVcY4v.webp")
BASE_DIR = INPUT_MD.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
ANIMATION_DIR = OUTPUT_DIR / "animations"
ANIMATION_DIR.mkdir(exist_ok=True)

# Nettoyage fichiers audio corrompus
for f in OUTPUT_DIR.glob("*.wav"):
    try:
        f.unlink()
    except Exception as e:
        print(f"❌ Impossible de supprimer {f.name} : {e}")

# Paramètres Généraux
FONT_SIZE_TITLE = 50
FONT_SIZE_TEXT = 36
FONT_SIZE_TABLE = 28
WIDTH, HEIGHT = 960, 540  # 🧹 Correction RAM
BG_COLOR = (255, 255, 255)
TEXT_COLOR = "black"
TABLE_HEADER_BG = (200, 220, 240)
TABLE_ROW_BG_1 = (248, 248, 248)
TABLE_ROW_BG_2 = (255, 255, 255)
TABLE_BORDER = (180, 180, 180)
TEXT_MARGIN = 40
INTRO_DUR = 3
OUTRO_DUR = 3
SLIDE_DUR = 8
TRANSITION_DUR = 1
ANIMATION_FRAMES = 15  # 🧹 Moins d'images pour animation DrawBot
ANIMATION_DURATION = 2

# Synthèse Vocale
engine = pyttsx3.init()
engine.setProperty('rate', 150)
# === Partie 2 : FONCTIONS UTILITAIRES ===

def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")



def format_numbered_sections(text):
    """Formate les sections numérotées comme "2 • Les Différents types" en les mettant chacune sur une ligne"""
    # Cherche les motifs comme "2 • Texte" ou "2.3 • Texte"
    pattern = r'(\d+(?:\.\d+)?)\s*([•\-\*])\s*([^\d•\-\*][^\n•\-\*]*)'
    
    # On utilise une fonction de remplacement pour préserver les groupes capturés
    def replacement(match):
        num, symbol, content = match.groups()
        # On vérifie si le numéro est précédé par un retour à la ligne
        if match.start() > 0 and text[match.start()-1] != '\n':
            return f"\n{num} {symbol} {content}"
        return f"{num} {symbol} {content}"
    
    return re.sub(pattern, replacement, text)

def clean_text_for_display(text):
    if not text or not text.strip():
        return ""
    text = text.replace("\n\n", "§§§")
    
    # Format les sections numérotées
    text = format_numbered_sections(text)
    
    # Détection améliorée des symboles et numéros en début de texte
    # Cette regex cherche les chiffres suivis d'un point, tiret ou autre symbole
    text = re.sub(r'([^\n])(\d+[\s\.\-\•\➤\►\→\✓\✔\*]+)', r'\1\n\2', text)
    
    # Détection améliorée pour tous les symboles courants
    for symbol in ['❑', '•', '-', '*', '➤', '►', '→', '✓', '✔', '▪', '▫', '◦']:
        text = re.sub(r'([^\n])(' + re.escape(symbol) + r')', r'\1\n\2', text)
    
    # Détection spécifique pour les numéros suivis d'un point (comme "1.")
    text = re.sub(r'([^\n])(\d+\.\s)', r'\1\n\2', text)
    
    # Détection pour les formats comme "1-" ou "2-"
    text = re.sub(r'([^\n])(\d+\-\s*)', r'\1\n\2', text)
    
    lines = text.split('\n')
    formatted_lines = []
    for line in lines:
        indent = len(line) - len(line.lstrip())
        line_content = line.strip()
        
        # Traitement spécial pour les lignes commençant par un numéro
        if re.match(r'^\d+[\.\-]', line_content):
            spaces = ' ' * indent
            line = f"{spaces}{line_content}"
        
        # Traitement pour les lignes commençant par un symbole
        elif line_content.startswith(('-', '*', '•', '❑', '➤', '►', '→', '✓', '✔', '▪', '▫', '◦')):
            spaces = ' ' * indent
            line = f"{spaces}• {line_content[1:].strip()}"
        
        formatted_lines.append(line)
    
    return '\n'.join(formatted_lines).replace("§§§", "\n\n")
def preserve_markdown_formatting(text):
    """Conserve la mise en forme Markdown dans le texte pour l'affichage"""
    if not text or not isinstance(text, str):
        return ""
    
    # CORRECTION: Supprimer les références d'images avant le formatage
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # Préserver les titres H1, H2, H3, etc.
    text = re.sub(r'^# (.+)$', r'\1', text, flags=re.MULTILINE)  # Ne pas ajouter "TITRE1: "
    text = re.sub(r'^## (.+)$', r'\1', text, flags=re.MULTILINE)  # Ne pas ajouter "TITRE2: "
    text = re.sub(r'^### (.+)$', r'\1', text, flags=re.MULTILINE)  # Ne pas ajouter "TITRE3: "
    
    # Préserver l'italique et le gras en supprimant simplement les symboles de formatage
    # au lieu de les remplacer par "GRAS:" ou "ITALIQUE:"
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Gras
    text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italique
    text = re.sub(r'\_(.+?)\_', r'\1', text)  # Italique alternatif
    
    # Préserver les listes à puces et numérotées
    text = re.sub(r'^- (.+)$', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'^\* (.+)$', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'^(\d+)\. (.+)$', r'\1. \2', text, flags=re.MULTILINE)
    
    # Préserver les blocs de code
    code_blocks = re.findall(r'```(.+?)```', text, re.DOTALL)
    for i, block in enumerate(code_blocks):
        text = text.replace(f'```{block}```', f'{block}')  # Supprimer les backticks
    
    return text

def extract_images_from_text(text, base_path=BASE_DIR):
    """Extrait toutes les images depuis le Markdown avec une détection améliorée et un débogage"""
    lines = text.split("\n")
    cleaned_lines = []
    image_references = []
    
    # Motif pour trouver les références d'images dans la syntaxe Markdown
    image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
    
    print(f"🔍 Extraction des images de {len(lines)} lignes de texte...")
    
    for i, line in enumerate(lines):
        image_matches = image_pattern.findall(line)
        
        if image_matches:
            print(f"📷 Images trouvées à la ligne {i}: {len(image_matches)} images")
            for alt_text, img_path in image_matches:
                # Nettoyer le chemin d'image
                img_path = img_path.strip()
                print(f"  👉 Tentative de traitement de l'image: '{img_path}' (alt: '{alt_text}')")
                
                # Vérifier plusieurs possibilités pour le chemin
                valid_path = find_valid_image_path(base_path, img_path)
                
                if valid_path:
                    print(f"  ✅ Image trouvée: {valid_path}")
                    # Stocker la référence avec le chemin valide
                    image_references.append((valid_path, i))
                else:
                    # Essayer des alternatives si le chemin direct ne fonctionne pas
                    print(f"  ⚠️ Chemin image non trouvé directement: {img_path}")
                    alt_paths = [
                        # Essayer avec le nom de fichier seul
                        base_path / Path(img_path).name,
                        # Essayer dans des sous-dossiers courants
                        base_path / "images" / Path(img_path).name,
                        base_path / "img" / Path(img_path).name,
                        base_path / "assets" / Path(img_path).name,
                        base_path / "media" / Path(img_path).name,
                        base_path / "pictures" / Path(img_path).name,
                    ]
                    
                    found = False
                    for alt_path in alt_paths:
                        if alt_path.exists():
                            print(f"  ✅ Image alternative trouvée: {alt_path}")
                            image_references.append((alt_path, i))
                            found = True
                            break
                    
                    if not found:
                        print(f"  ❌ Aucune image trouvée pour: {img_path}")
        
        # CORRECTION: On ne garde que les lignes sans références d'images
        # ou on les nettoie pour supprimer ces références
        cleaned_line = re.sub(r'!\[.*?\]\(.*?\)', '', line)
        if cleaned_line.strip():  # On ne garde pas les lignes vides
            cleaned_lines.append(cleaned_line)
    
    # Vérification supplémentaire pour les images dans le dossier BASE_DIR
    if len(image_references) == 0:
        print("🔍 Aucune image trouvée dans le texte. Recherche d'images alternatives dans le dossier...")
        image_files = []
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp"]:
            image_files.extend(list(base_path.glob(ext)))
            
            # Chercher également dans les sous-dossiers courants
            for subfolder in ["images", "img", "assets", "media", "pictures"]:
                subfolder_path = base_path / subfolder
                if subfolder_path.exists():
                    image_files.extend(list(subfolder_path.glob(ext)))
        
        if image_files:
            print(f"📷 {len(image_files)} images trouvées dans le dossier")
            for img in image_files[:5]:  # Limiter à 5 images pour éviter la surcharge
                print(f"  ➕ Ajout de l'image trouvée: {img}")
                image_references.append((img, 0))
    
    # Résumé de l'extraction
    print(f"📊 Résultat de l'extraction: {len(image_references)} images trouvées")
    
    return image_references, "\n".join(cleaned_lines).strip()


def find_valid_image_path(base_path, raw_path, search_subfolders=True, debug=True):
    """
    Version robuste et exhaustive de la recherche d'images
    """
    if debug:
        print(f"🔍 Recherche de l'image: {raw_path}")
    
    # Nettoyage du chemin
    raw_path = raw_path.strip().replace('\\', '/').replace('%20', ' ')
    
    # Liste complète des chemins possibles à vérifier
    possible_paths = []
    
    # 1. Chemin direct tel quel
    possible_paths.append(base_path / raw_path)
    
    # 2. Juste le nom du fichier dans le dossier de base
    filename = Path(raw_path).name
    possible_paths.append(base_path / filename)
    
    # 3. Essayer avec différentes extensions
    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']
    
    # Pour le chemin complet sans extension
    stem = re.sub(r"\.\w+$", "", raw_path)
    for ext in extensions:
        possible_paths.append(base_path / f"{stem}{ext}")
    
    # Pour juste le nom du fichier sans extension
    filename_stem = Path(stem).name
    for ext in extensions:
        possible_paths.append(base_path / f"{filename_stem}{ext}")
    
    # 4. Recherche dans les sous-dossiers courants
    if search_subfolders:
        common_folders = ["images", "img", "assets", "media", "pictures", "photos", "docs", "content"]
        
        for folder in common_folders:
            subfolder_path = base_path / folder
            
            if subfolder_path.exists():
                # Chemin complet dans le sous-dossier
                possible_paths.append(subfolder_path / raw_path)
                
                # Juste le nom dans le sous-dossier
                possible_paths.append(subfolder_path / filename)
                
                # Variations d'extensions dans le sous-dossier
                for ext in extensions:
                    possible_paths.append(subfolder_path / f"{filename_stem}{ext}")
    
    # Vérifier tous les chemins possibles
    for path in possible_paths:
        try:
            if path.exists():
                if debug:
                    print(f"✅ Image trouvée: {path}")
                return path
        except:
            # Ignorer les erreurs de chemin invalide
            pass
    
    if debug:
        print(f"❌ Aucune image trouvée pour: {raw_path}")
    return None

def extract_images_from_markdown(markdown_text, base_path):
    """
    Extrait toutes les images du Markdown avec leur position exacte
    """
    image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
    images = []
    
    # Trouver toutes les références d'images
    for match in image_pattern.finditer(markdown_text):
        alt_text = match.group(1)
        img_path = match.group(2)
        position = match.start()
        
        # Trouver le chemin valide de l'image
        valid_path = find_valid_image_path(base_path, img_path)
        
        if valid_path:
            # Stocker l'image avec sa position exacte dans le Markdown
            images.append({
                'path': valid_path,
                'alt_text': alt_text,
                'original_path': img_path,
                'position': position,
                'match_length': len(match.group(0))
            })
    
    return images
def extract_images_from_markdown(markdown_text, base_path):
    """
    Extrait toutes les images du Markdown avec leur position exacte
    """
    image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
    images = []
    
    # Trouver toutes les références d'images
    for match in image_pattern.finditer(markdown_text):
        alt_text = match.group(1)
        img_path = match.group(2)
        position = match.start()
        
        # Trouver le chemin valide de l'image
        valid_path = find_valid_image_path(base_path, img_path)
        
        if valid_path:
            # Stocker l'image avec sa position exacte dans le Markdown
            images.append({
                'path': valid_path,
                'alt_text': alt_text,
                'original_path': img_path,
                'position': position,
                'match_length': len(match.group(0))
            })
    
    return images

def slide_clip_with_exact_markdown(title, content, images, duration=SLIDE_DUR):
    """
    Crée un slide qui préserve exactement la structure Markdown originale
    avec une mise en page adaptative selon la quantité de texte
    """
    bg = ColorClip((WIDTH, HEIGHT), color=BG_COLOR).set_duration(duration)
    layers = [bg]
    
    # Zone de contenu
    content_top =20 #Position plus haut si pas de titre
    
    # Vérifier si le titre est un marqueur de page pour le masquer
    display_title = title
    if title and re.match(r'(---\s*)?[Pp]age\s+\d+(\s*---)?', title):
        display_title = None  # Ne pas afficher les titres de type "Page X"
    
    # Réduire la position de départ du contenu
    content_top = 20  # Au lieu de 40 ou 100
    
    # Ajuster le positionnement du titre
    if display_title:
        title_clip = create_text_clip(display_title, FONT_SIZE_TITLE, WIDTH-120, 
                                    position=("center", 10), # Au lieu de 30
                                    align="center", duration=duration)
        layers.append(title_clip)
        content_top = 60 
    
    # Supprimer les références aux marqueurs de page du contenu
    content_without_markers = re.sub(r'^##\s+(---\s*)?[Pp]age\s+\d+(\s*---)?.*?$', '', content, flags=re.MULTILINE)
    
    # Extraire le contenu principal sans le titre pour l'affichage
    content_without_title = content_without_markers
    if title:
        # Tenter de retirer le premier titre s'il correspond au titre actuel
        first_line_match = re.match(r'^#+\s+(.*?)$', content.split('\n')[0] if '\n' in content else '')
        if first_line_match and title in first_line_match.group(1):
            content_without_title = '\n'.join(content.split('\n')[1:])
    
    # CORRECTION: Supprimer les références d'images du contenu texte affiché
    processed_content = re.sub(r'!\[.*?\]\(.*?\)', '', content_without_title)
    
    # Traiter le Markdown pour préserver la mise en forme
    processed_content = preserve_markdown_formatting(processed_content)
    
    # Déterminer si le texte est court ou vide
    is_text_short = len(processed_content.strip()) < 100
    
    # Vérifier si nous avons des images valides
    has_valid_images = False
    valid_image_path = None
    
    for img in images:
        if isinstance(img, tuple):  # Support de l'ancien format
            img_path = img[0]
        else:  # Nouveau format
            img_path = img['path']
        
        try:
            # Tester si l'image est accessible
            ImageClip(str(img_path))
            has_valid_images = True
            valid_image_path = img_path
            break
        except Exception as e:
            print(f"⚠️ Erreur test image {img_path}: {e}")
    
    # Paramètres pour le positionnement du texte et des images
    text_width = WIDTH - 2*TEXT_MARGIN
    text_x = TEXT_MARGIN
    img_width = WIDTH * 0.4  # Image plus petite par défaut
    img_x = WIDTH - img_width - TEXT_MARGIN  # Image à droite
    
    # Disposition adaptative selon la présence d'images et la quantité de texte
    if has_valid_images and processed_content.strip():
        # Si texte + image: texte à gauche, image à droite (pas de chevauchement)
        text_width = WIDTH * 0.5 - TEXT_MARGIN
        text_x = TEXT_MARGIN  # Texte à gauche
    elif not has_valid_images:
        # Si aucune image valide: texte en pleine largeur
        text_width = WIDTH - 2*TEXT_MARGIN
        text_x = TEXT_MARGIN
    
    # Ajouter le texte principal si présent
    if processed_content.strip():
        text_clip = create_text_clip(processed_content, FONT_SIZE_TEXT, text_width, 
                                    position=(text_x, content_top), 
                                    duration=duration)
        layers.append(text_clip)
    
    # Ajouter les images seulement si on a une image valide
    if has_valid_images:
        try:
            # Charger l'image
            img_clip = ImageClip(str(valid_image_path))
            
            # Calculer les dimensions
            img_ratio = img_clip.h / img_clip.w
            img_height = int(img_width * img_ratio)
            
            # Limiter la hauteur
            if img_height > HEIGHT * 0.7:
                img_height = HEIGHT * 0.7
                img_width = int(img_height / img_ratio)
            
            # Positionner l'image à droite, pas en chevauchement avec le texte
            img_y = content_top  # Par défaut sous le titre
            
            img_clip = img_clip.resize(width=img_width)
            img_clip = img_clip.set_position((img_x, img_y)).set_duration(duration)
            layers.append(img_clip)
            
        except Exception as e:
            print(f"⚠️ Erreur image {valid_image_path}: {e}")
    
    # Ajouter le logo
    if LOGO_PATH.exists():
        logo = ImageClip(str(LOGO_PATH)).resize(width=70).set_position((WIDTH-80, 20)).set_duration(duration)
        layers.append(logo)
    
    return CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
# === Nouvelle fonction pour créer des transitions ===
def create_transition(first_clip, second_clip, transition_type="fade", duration=TRANSITION_DUR):
    """
    Crée une transition entre deux clips vidéo
    
    Types de transition disponibles:
    - fade: fondu enchaîné entre les deux clips
    - wipe_right: balayage de gauche à droite
    - wipe_left: balayage de droite à gauche
    - wipe_up: balayage de bas en haut
    - wipe_down: balayage de haut en bas
    - zoom_in: zoom avant sur la nouvelle diapo
    - zoom_out: zoom arrière de l'ancienne diapo
    """
    w, h = first_clip.size
    
    # Vérifier que la transition n'est pas trop longue comparée aux clips
    safe_duration = min(duration, first_clip.duration/2, second_clip.duration/2)
    
    if transition_type == "fade":
        # Fondu enchaîné classique
        first_end = first_clip.copy().subclip(first_clip.duration - safe_duration, first_clip.duration)
        first_end = first_end.crossfadeout(safe_duration)
        
        second_start = second_clip.copy().subclip(0, safe_duration)
        second_start = second_start.crossfadein(safe_duration)
        
        return CompositeVideoClip([first_end, second_start])
    
    elif transition_type.startswith("wipe"):
        # Différents types de balayage (wipe)
        first_end = first_clip.copy().subclip(first_clip.duration - safe_duration, first_clip.duration)
        second_start = second_clip.copy().subclip(0, safe_duration)
        
        def make_mask(t):
            progress = t / safe_duration
            mask = np.zeros((h, w), dtype=np.float32)
            
            if transition_type == "wipe_right":
                x_limit = int(w * progress)
                mask[:, :x_limit] = 1.0
            elif transition_type == "wipe_left":
                x_limit = int(w * (1 - progress))
                mask[:, x_limit:] = 1.0
            elif transition_type == "wipe_up":
                y_limit = int(h * (1 - progress))
                mask[y_limit:, :] = 1.0
            elif transition_type == "wipe_down":
                y_limit = int(h * progress)
                mask[:y_limit, :] = 1.0
            
            return mask
        
        mask_clip = VideoClip(make_mask, duration=safe_duration).set_position((0, 0))
        
        return CompositeVideoClip(
            [first_end, second_start.set_mask(mask_clip)]
        )
    
    elif transition_type == "zoom_in":
        # Zoom avant sur la nouvelle diapositive
        first_end = first_clip.copy().subclip(first_clip.duration - safe_duration, first_clip.duration)
        
        def zoom_in(t):
            progress = t / safe_duration
            scale = 1 - progress + 0.5 * progress  # De 0.5 à 1.0
            x_offset = w * (1 - scale) / 2
            y_offset = h * (1 - scale) / 2
            return (second_clip.copy()
                .resize(lambda t: scale)
                .set_position((x_offset, y_offset)))
        
        second_start = VideoClip(zoom_in, duration=safe_duration)
        
        return CompositeVideoClip([first_end, second_start])
    
    elif transition_type == "zoom_out":
        # Zoom arrière de l'ancienne diapositive
        second_start = second_clip.copy().subclip(0, safe_duration)
        
        def zoom_out(t):
            progress = t / safe_duration
            scale = 1.5 - 0.5 * progress  # De 1.5 à 1.0
            x_offset = w * (1 - scale) / 2
            y_offset = h * (1 - scale) / 2
            return (first_clip.copy()
                .resize(lambda t: scale)
                .set_position((x_offset, y_offset)))
        
        first_end = VideoClip(zoom_out, duration=safe_duration)
        
        return CompositeVideoClip([second_start, first_end])
    
    else:
        # Défaut: fondu enchaîné simple
        return create_transition(first_clip, second_clip, "fade", safe_duration)

# === Fonction pour appliquer des transitions à une liste de clips ===
def apply_transitions_to_clips(clips, transition_type="fade", transition_duration=TRANSITION_DUR):
    """
    Applique des transitions entre tous les clips d'une liste
    Retourne une liste de clips avec transitions
    """
    if not clips or len(clips) < 2:
        return clips
    
    result = [clips[0]]
    
    for i in range(1, len(clips)):
        # Obtenir le clip précédent et le clip actuel
        prev_clip = clips[i-1]
        current_clip = clips[i]
        
        # Durée de la transition ne doit pas être plus grande que la moitié du clip le plus court
        safe_duration = min(transition_duration, prev_clip.duration/2, current_clip.duration/2)
        
        # Raccourcir le clip précédent (puisqu'il sera mélangé avec le suivant)
        new_prev_duration = prev_clip.duration - safe_duration
        result[-1] = prev_clip.subclip(0, new_prev_duration)
        
        # Créer la transition entre les deux clips
        transition = create_transition(prev_clip, current_clip, transition_type, safe_duration)
        result.append(transition)
        
        # Ajouter le clip courant (raccourci pour ne pas inclure la partie déjà dans la transition)
        new_current = current_clip.subclip(safe_duration, current_clip.duration)
        result.append(new_current)
    
    return result

# === Fonction pour choisir des transitions variées ===
def get_varied_transitions(number_of_transitions, seed=42):
    """
    Génère une liste de transitions variées pour éviter la monotonie
    """
    random.seed(seed)  # Pour la reproductibilité
    
    transition_types = [
        "fade",
        "wipe_right",
        "wipe_left",
        "wipe_up",
        "wipe_down",
        "zoom_in",
        "zoom_out"
    ]
    
    # Pour éviter de répéter la même transition deux fois de suite
    transitions = []
    last_transition = None
    
    for _ in range(number_of_transitions):
        available = [t for t in transition_types if t != last_transition]
        chosen = random.choice(available)
        transitions.append(chosen)
        last_transition = chosen
    
    return transitions
def extract_tables_from_text(text):
    lines = text.split("\n")
    table_start_indices = []
    table_end_indices = []
    in_table = False
    current_table_start = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:] and not in_table:
            current_table_start = i
            in_table = True
        elif in_table and re.match(r"\|\s*[-:]+\s*\|", stripped):
            pass
        elif in_table and (not stripped or not stripped.startswith("|")):
            if current_table_start >= 0:
                table_start_indices.append(current_table_start)
                table_end_indices.append(i - 1)
                current_table_start = -1
            in_table = False
    if in_table and current_table_start >= 0:
        table_start_indices.append(current_table_start)
        table_end_indices.append(len(lines) - 1)

    tables = []
    for start, end in zip(table_start_indices, table_end_indices):
        table_lines = lines[start:end+1]
        if not any(re.match(r"\|\s*[-:]+\s*\|", line.strip()) for line in table_lines):
            continue
        table_data = []
        for line in table_lines:
            stripped = line.strip()
            if re.match(r"\|\s*[-:]+\s*\|", stripped):
                continue
            cells = [cell.strip() for cell in stripped.strip('|').split('|')]
            table_data.append(cells)
        max_cols = max(len(row) for row in table_data) if table_data else 0
        for row in table_data:
            while len(row) < max_cols:
                row.append("")
        if table_data:
            tables.append(table_data)
    cleaned_lines = []
    i = 0
    while i < len(lines):
        if any(start <= i <= end for start, end in zip(table_start_indices, table_end_indices)):
            i += 1
            continue
        cleaned_lines.append(lines[i])
        i += 1
    return tables, "\n".join(cleaned_lines)
# === Partie 3 : ANIMATIONS + VISUALISATIONS ===
def draw_wrapped_text(txt, x, y, max_width, line_height=FONT_SIZE_TEXT + 5):
    """Affiche du texte avec retour à la ligne automatique dans DrawBot"""
    if not txt or not isinstance(txt, str):
        txt = str(txt) if txt is not None else " "
    
    # Séparer le texte en lignes distinctes
    paragraphs = txt.split('\n')
    current_y = y
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            # Ajouter un espace vertical pour les lignes vides
            current_y -= line_height / 2
            continue
            
        # Traiter chaque paragraphe par mots
        words = paragraph.split()
        line = ""

        for word in words:
            test_line = line + word + " "
            drawBot.font("Helvetica", FONT_SIZE_TEXT)
            w, _ = drawBot.textSize(test_line)
            
            if w <= max_width:
                line = test_line
            else:
                # Dessiner la ligne actuelle et passer à la suivante
                drawBot.text(line.strip(), (x, current_y))
                current_y -= line_height
                line = word + " "
                
        # Dessiner la dernière ligne du paragraphe
        if line:
            drawBot.text(line.strip(), (x, current_y))
            current_y -= line_height
        
        # Ajouter un espace supplémentaire entre les paragraphes
        current_y -= line_height / 3
def create_text_animation(text, title=None, width=WIDTH, height=HEIGHT, output_dir=ANIMATION_DIR):
    """Crée une animation de texte ligne par ligne"""
    if not text or not text.strip():
        text = " "
    
    # Supprimer les références d'images du texte
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # Diviser le texte en lignes
    lines = text.split('\n')
    lines = [line for line in lines if line.strip()]  # Enlever les lignes vides
    
    total_frames = int(ANIMATION_FRAMES * ANIMATION_DURATION)
    text_id = slugify(text[:20])
    output_pattern = os.path.join(output_dir, f"anim_{text_id}_frame_%04d.png")
    frames = []

    try:
        total_lines = len(lines)
        
        for frame in range(total_frames):
            progress = min(1.0, frame / (total_frames * 0.8))
            lines_to_show = max(1, int(progress * total_lines))  # Au moins une ligne

            drawBot.newDrawing()
            drawBot.size(width, height)
            drawBot.fill(1, 1, 1)
            drawBot.rect(0, 0, width, height)

            y_pos = height - 60
            if title:
                drawBot.font("Helvetica-Bold", FONT_SIZE_TITLE)
                drawBot.fill(0, 0, 0)
                # Centrer le titre horizontalement
                title_width, _ = drawBot.textSize(title)
                drawBot.text(title, (width/2 - title_width/2, height - 100))
                y_pos = height - 120

            drawBot.font("Helvetica", FONT_SIZE_TEXT)
            drawBot.fill(0, 0, 0)

            # Afficher uniquement les lignes qui doivent être visibles selon la progression
            display_text = '\n'.join(lines[:lines_to_show])
            
            # Utiliser la fonction existante pour gérer les retours à la ligne
            draw_wrapped_text(display_text, TEXT_MARGIN, y_pos, width - 2 * TEXT_MARGIN)

            frame_path = output_pattern % frame
            drawBot.saveImage(frame_path)
            frames.append(frame_path)
            drawBot.endDrawing()

        return frames

    except Exception as e:
        print(f"❌ Erreur création animation: {e}")
        return None
def create_animated_text_clip(text_content, title=None, duration=SLIDE_DUR):
    """Crée un clip animé avec MoviePy à partir de DrawBot avec animation ligne par ligne"""
    try:
        # Supprimer les références d'images du texte
        input_text = re.sub(r'!\[.*?\]\(.*?\)', '', text_content)
        
        # Prétraiter le texte pour une meilleure lisibilité
        clean_text = clean_text_for_display(input_text)
        
        # Créer les frames d'animation
        animation_frames = create_text_animation(clean_text, title)

        if not animation_frames or len(animation_frames) == 0:
            # Fallback si l'animation échoue
            return create_text_clip(input_text, FONT_SIZE_TEXT, WIDTH-2*TEXT_MARGIN, (TEXT_MARGIN, 100), duration=duration)

        # Calculer la durée appropriée
        clip_duration = min(ANIMATION_DURATION, duration)
        
        # Créer le clip d'animation à partir des frames
        animation_clip = ImageSequenceClip(animation_frames, fps=ANIMATION_FRAMES/ANIMATION_DURATION)
        
        # Ajuster la durée
        if duration > ANIMATION_DURATION:
            # Garder la dernière frame affichée pour le reste de la durée
            last_frame = animation_frames[-1]
            static_clip = ImageClip(last_frame).set_duration(duration - ANIMATION_DURATION)
            final_clip = concatenate_videoclips([animation_clip, static_clip])
            return final_clip
        else:
            return animation_clip.set_duration(duration)

    except Exception as e:
        print(f"❌ Erreur création clip animé: {e}")
        # Fallback en cas d'erreur
        return create_text_clip(text_content, FONT_SIZE_TEXT, WIDTH-2*TEXT_MARGIN, (TEXT_MARGIN, 100), duration=duration)

def create_text_clip(text, fontsize, width, position, align="West", duration=SLIDE_DUR):
    """Crée un TextClip MoviePy propre avec fallback"""
    if not text or not text.strip():
        text = " "

    try:
        clip = TextClip(
            text,
            fontsize=fontsize,
            color=TEXT_COLOR,
            method="caption",
            align=align,
            size=(width, None),
            interline=1.2
        )
        return clip.set_position(position).set_duration(duration)
    except Exception as e:
        print(f"⚠️ Erreur création TextClip: {e}")
        return TextClip(
            " ", fontsize=fontsize, color=TEXT_COLOR,
            method="caption", size=(width, None)
        ).set_position(position).set_duration(duration)

def create_data_visualization(df, viz_type='pca', width=WIDTH//2, height=HEIGHT//2):
    """Crée une visualisation automatique à partir d'un DataFrame pandas"""
    viz_id = f"viz_{viz_type}_{hash(str(df))}"
    output_file = ANIMATION_DIR / f"{viz_id}.png"

    if output_file.exists():
        return str(output_file)

    plt.figure(figsize=(width/100, height/100), dpi=100)

    try:
        numeric_df = df.select_dtypes(include=[np.number])

        if numeric_df.empty:
            df.iloc[:min(10, len(df))].plot(kind='bar')
            plt.title("Aperçu des données")
        elif viz_type == 'pca':
            if numeric_df.shape[1] >= 2:
                scaler = preprocessing.StandardScaler()
                scaled_data = scaler.fit_transform(numeric_df)
                pca = decomposition.PCA(n_components=2)
                components = pca.fit_transform(scaled_data)
                plt.scatter(components[:, 0], components[:, 1], alpha=0.7)
                plt.title("Analyse PCA")
            else:
                numeric_df.plot(kind='bar')
        elif viz_type == 'cluster':
            if numeric_df.shape[1] >= 2 and numeric_df.shape[0] >= 3:
                scaler = preprocessing.StandardScaler()
                scaled_data = scaler.fit_transform(numeric_df)
                n_clusters = min(5, numeric_df.shape[0] // 2)
                kmeans = cluster.KMeans(n_clusters=n_clusters)
                clusters = kmeans.fit_predict(scaled_data)
                pca = decomposition.PCA(n_components=2)
                components = pca.fit_transform(scaled_data)
                plt.scatter(components[:, 0], components[:, 1], c=clusters, cmap='viridis', alpha=0.7)
                plt.title("Clustering K-means")
            else:
                numeric_df.plot(kind='bar')
        elif viz_type == 'tsne':
            if numeric_df.shape[1] >= 2 and numeric_df.shape[0] >= 3:
                scaler = preprocessing.StandardScaler()
                scaled_data = scaler.fit_transform(numeric_df)
                tsne = manifold.TSNE(n_components=2, perplexity=min(30, max(5, numeric_df.shape[0]//10)))
                components = tsne.fit_transform(scaled_data)
                plt.scatter(components[:, 0], components[:, 1], alpha=0.7)
                plt.title("t-SNE")
            else:
                numeric_df.plot(kind='bar')
        else:
            numeric_df.plot()
            plt.title("Aperçu des données")

        plt.tight_layout()
        plt.savefig(str(output_file), dpi=100)
        plt.close()
        return str(output_file)

    except Exception as e:
        print(f"❌ Erreur création visualisation: {e}")
        plt.close()
        return None
# === Partie 4 : MAIN FINAL ===

def split_markdown_into_segments(content):
    """Découpe le Markdown en segments logiques par pages avec préservation des images"""
    pages = re.split(r"## --- Page \d+ ---", content)
    segments = []
    
    for i, page in enumerate(pages[1:], start=1):
        page = page.strip()
        if not page:
            continue
        
        lines = page.split('\n')
        title = lines[0].strip() if lines else f"Page {i}"
        
        # Extraire le corps en préservant les références d'images
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        
        # Vérifier si des images sont présentes dans ce segment
        images_in_segment = re.findall(r'!\[(.*?)\]\((.*?)\)', body)
        if images_in_segment:
            print(f"📄 Page {i}: {len(images_in_segment)} images détectées")
        
        segments.append((title, body))
    
    return segments
def split_markdown_into_hierarchical_segments(content):
    """Découpe le Markdown en segments hiérarchiques en préservant la structure"""
    # Découper par pages comme avant
    pages = re.split(r"## --- Page \d+ ---", content)
    hierarchical_segments = []
    
    for i, page in enumerate(pages[1:], start=1):
        page = page.strip()
        if not page:
            continue
        
        # Extraire le titre principal de la page
        lines = page.split('\n')
        main_title = lines[0].strip() if lines else f"Page {i}"
        
        # Trouver les sous-sections (## Titre)
        sections = re.split(r'^## ', page, flags=re.MULTILINE)[1:]
        
        if not sections:  # S'il n'y a pas de sous-sections
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            hierarchical_segments.append({
                'main_title': main_title,
                'sections': [{'title': None, 'content': body}]
            })
        else:
            page_sections = []
            for section in sections:
                section_lines = section.split('\n')
                section_title = section_lines[0].strip() if section_lines else ""
                section_body = "\n".join(section_lines[1:]).strip() if len(section_lines) > 1 else ""
                page_sections.append({'title': section_title, 'content': section_body})
            
            hierarchical_segments.append({
                'main_title': main_title,
                'sections': page_sections
            })
    
    return hierarchical_segments

def slide_clip(title, text_content, images=None, tables=None, duration=SLIDE_DUR, animate_text=True):
    """Crée un slide avec texte, image, tableau, logo sans chevauchement"""
    bg = ColorClip((WIDTH, HEIGHT), color=BG_COLOR).set_duration(duration)
    layers = [bg]

    # Réserver plus d'espace pour le titre
    title_height = 60
    content_top = title_height + 10# Augmenté pour laisser plus d'espace au titre
    available_height = HEIGHT - content_top - 40  # Marge du bas
    
    # Ajuster la position du titre
    if title:
        title_clip = create_text_clip(title, FONT_SIZE_TITLE, WIDTH-120, 
                                     position=("center", 10), # Au lieu de 30
                                     align="center", duration=duration)
        layers.append(title_clip)
    
    # Ajuster la mise en page selon la présence d'images
    has_content_image = images and len(images) > 0
    
    if has_content_image:
        # Diviser l'écran: texte à gauche, image à droite, mais sous le titre
        text_width = int(WIDTH * 0.55) - TEXT_MARGIN
        img_width = int(WIDTH * 0.40)
        text_x_pos = TEXT_MARGIN
        img_x_pos = WIDTH - img_width - TEXT_MARGIN
        
        # Charger et positionner l'image - IMPORTANT: sous le titre
        try:
            img_path = images[0]
            img_temp = ImageClip(str(img_path))
            img_ratio = img_temp.h / img_temp.w
            img_height = int(img_width * img_ratio)
            
            # Limiter la hauteur de l'image
            if img_height > available_height:
                img_height = available_height
                img_width = int(img_height / img_ratio)
            
            # Positionner l'image SOUS le titre (content_top)
            img_clip = ImageClip(str(img_path)).resize(width=img_width).set_position((img_x_pos, content_top)).set_duration(duration)
            layers.append(img_clip)
        except Exception as e:
            print(f"⚠️ Erreur chargement image {img_path}: {e}")
            has_content_image = False
            text_width = WIDTH - 2*TEXT_MARGIN
    else:
        text_width = WIDTH - 2*TEXT_MARGIN
    
    # CORRECTION: Supprimer les références d'images du texte affiché 
    # pour éviter que les chemins d'images ne s'affichent dans la vidéo
    if text_content:
        # Suppression des références d'images en Markdown
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', text_content)
        # Puis nettoyer pour l'affichage
        clean_text = clean_text_for_display(clean_text)
        
        if animate_text:
            text_clip = create_animated_text_clip(clean_text, duration=duration)
            # Positionner le texte sous le titre
            text_clip = text_clip.resize(width=text_width).set_position((text_x_pos if has_content_image else TEXT_MARGIN, content_top))
        else:
            text_clip = create_text_clip(clean_text, FONT_SIZE_TEXT, text_width, 
                                       position=(text_x_pos if has_content_image else TEXT_MARGIN, content_top), 
                                       duration=duration)
        
        layers.append(text_clip)

    # Ajout des visualisations de table en bas
    if tables:
        try:
            df = pd.DataFrame(tables[0][1:], columns=tables[0][0])
            viz_path = create_data_visualization(df)
            if viz_path:
                # Positionner la visualisation tout en bas
                viz_width = WIDTH // 2
                viz_clip = ImageClip(str(viz_path)).resize(width=viz_width).set_position(("center", HEIGHT-120)).set_duration(duration)
                layers.append(viz_clip)
        except Exception as e:
            print(f"⚠️ Erreur création visualisation table : {e}")

    # Logo en haut à droite, mais s'assurer qu'il ne cache pas le titre
    if LOGO_PATH.exists():
        logo = ImageClip(str(LOGO_PATH)).resize(width=70).set_position((WIDTH-80, 20)).set_duration(duration)
        layers.append(logo)

    return CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
def extract_markdown_structure(markdown_text):
    """
    Analyse la structure du Markdown et préserve l'emplacement exact des images
    et la hiérarchie du contenu, avec meilleure détection des marqueurs de page
    """
    # Structure à retourner (reproduisant exactement le Markdown original)
    structure = []
    current_position = 0
    
    # Motifs pour les éléments à identifier
    heading_pattern = re.compile(r'^(#+)\s+(.*?)$', re.MULTILINE)
    image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
    
    # Motif spécifique pour les marqueurs de page (plus précis)
    page_marker_pattern = re.compile(r'^##\s+(---\s*)?[Pp]age\s+\d+(\s*---)?', re.MULTILINE)
    page_markers = [match.start() for match in page_marker_pattern.finditer(markdown_text)]
    
    # Identifier tous les titres et leur position
    all_headings = [(match.group(1), match.group(2), match.start()) 
                for match in heading_pattern.finditer(markdown_text)]
    
    # Traiter tous les titres, mais marquer ceux qui sont des séparateurs de page
    headings = []
    for level, title, start in all_headings:
        # Vérifier si ce titre correspond à un marqueur de page identifié
        is_page_marker = any(abs(start - marker) < 5 for marker in page_markers)
        
        # Double vérification avec regex pour les formes variées
        if not is_page_marker:
            is_page_marker = bool(re.match(r'(---\s*)?[Pp]age\s+\d+(\s*---)?', title))
        
        headings.append((level, title, start, is_page_marker))
    
    # Identifier toutes les images et leur position exacte
    images = [(match.group(1), match.group(2), match.start()) 
              for match in image_pattern.finditer(markdown_text)]
    
    # Si pas de titres, traiter le document entier
    if not headings:
        content = markdown_text
        images_in_section = [img for img in images]
        structure.append({
            'level': 0,
            'title': None,  # Pas de titre pour ne pas afficher "Document"
            'content': content,
            'images': images_in_section,
            'is_page_marker': False
        })
    else:
        # Traiter chaque section délimitée par les titres
        for i, (level, title, start, is_page_marker) in enumerate(headings):
            if i < len(headings) - 1:
                end = headings[i+1][2]  # Fin = début du titre suivant
            else:
                end = len(markdown_text)  # Fin du document
            
            content = markdown_text[start:end]
            
            # Identifier les images dans cette section spécifique
            images_in_section = [img for img in images if start <= img[2] < end]
            
            structure.append({
                'level': len(level),  # Niveau de titre (# = 1, ## = 2, etc.)
                'title': title,
                'content': content,
                'images': images_in_section,
                'position': start,  # Position absolue dans le document original
                'is_page_marker': is_page_marker  # Indique si c'est un marqueur de page
            })
    
    return structure
def slide_clip_with_markdown(title, markdown_content, images=None, tables=None, duration=SLIDE_DUR):
    """Crée un slide qui respecte la mise en forme Markdown originale"""
    bg = ColorClip((WIDTH, HEIGHT), color=BG_COLOR).set_duration(duration)
    layers = [bg]

    # Titre en haut
    if title:
        title_clip = create_text_clip(title, FONT_SIZE_TITLE, WIDTH-120, position=("center", 30), align="center", duration=duration)
        layers.append(title_clip)
    
    # CORRECTION: Supprimer les références d'images du contenu texte
    # pour éviter que les chemins d'images ne s'affichent dans la vidéo
    cleaned_markdown = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_content)
    
    # Prétraitement du contenu pour préserver la mise en forme
    preserved_content = preserve_markdown_formatting(cleaned_markdown)
    
    # Détection du contenu spécial (images, tableaux, code)
    image_references, cleaned_text = extract_images_from_text(markdown_content)
    tables, cleaned_text = extract_tables_from_text(cleaned_text)
    
    # Organisation du contenu
    content_y = 100  # Position de départ sous le titre
    content_height = HEIGHT - content_y - 40
    
    # Disposition pour privilégier la structure originale
    if images and len(images) > 0:
        # Mise en page avec images intégrées dans le flux du texte
        text_width = WIDTH - 2*TEXT_MARGIN
        text_position = (TEXT_MARGIN, content_y)
        
        # Texte principal avec formatage préservé
        text_clip = create_text_clip(preserved_content, FONT_SIZE_TEXT, text_width, 
                                   position=text_position, duration=duration)
        layers.append(text_clip)
        
        # Ajouter les images où elles apparaissent dans le texte
        for img_path, img_position in image_references:
            try:
                # Calculer la position verticale proportionnelle au texte
                img_y_ratio = img_position / len(markdown_content.split('\n'))
                img_y = content_y + int(img_y_ratio * content_height)
                
                img_clip = ImageClip(str(img_path)).resize(width=WIDTH//3)
                img_clip = img_clip.set_position((WIDTH - WIDTH//3 - TEXT_MARGIN, img_y)).set_duration(duration)
                layers.append(img_clip)
            except Exception as e:
                print(f"⚠️ Erreur chargement image {img_path}: {e}")
    else:
        # Sans image, afficher le texte en pleine largeur avec formatage préservé
        text_clip = create_text_clip(preserved_content, FONT_SIZE_TEXT, WIDTH - 2*TEXT_MARGIN, 
                                   position=(TEXT_MARGIN, content_y), duration=duration)
        layers.append(text_clip)
    
    # Logo
    if LOGO_PATH.exists():
        logo = ImageClip(str(LOGO_PATH)).resize(width=70).set_position((WIDTH-80, 20)).set_duration(duration)
        layers.append(logo)

    return CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
def slide_clip_title_image(title, image_path, duration=SLIDE_DUR):
    """
    Crée une diapositive avec un titre en haut et une image en dessous qui occupe
    tout l'espace disponible.
    """
    bg = ColorClip((WIDTH, HEIGHT), color=BG_COLOR).set_duration(duration)
    layers = [bg]
    
    # Ajouter le titre en haut
    if title:
        title_clip = create_text_clip(title, FONT_SIZE_TITLE, WIDTH-120, 
                                    position=("center", 30), 
                                    align="center", duration=duration)
        layers.append(title_clip)
    
    # Zone réservée pour l'image (sous le titre)
    title_space = 100  # Espace pour le titre et marge
    image_area_width = WIDTH - 2 * TEXT_MARGIN
    image_area_height = HEIGHT - title_space - TEXT_MARGIN
    
    # Charger et positionner l'image
    try:
        if image_path and Path(image_path).exists():
            img_clip = ImageClip(str(image_path))
            
            # Calculer les dimensions pour ajuster l'image proportionnellement
            img_ratio = img_clip.h / img_clip.w
            
            # Calculer les dimensions optimales pour l'image
            if (image_area_width * img_ratio) <= image_area_height:
                # L'image est plus large que haute par rapport à l'espace disponible
                img_width = image_area_width
                img_height = img_width * img_ratio
            else:
                # L'image est plus haute que large par rapport à l'espace disponible
                img_height = image_area_height
                img_width = img_height / img_ratio
            
            # Centrer l'image dans la zone disponible
            img_x = (WIDTH - img_width) / 2
            img_y = title_space + (image_area_height - img_height) / 2
            
            # Ajouter l'image redimensionnée et positionnée
            img_clip = img_clip.resize(width=img_width)
            img_clip = img_clip.set_position((img_x, img_y)).set_duration(duration)
            layers.append(img_clip)
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement de l'image {image_path}: {e}")
    
    # Ajouter le logo
    if LOGO_PATH.exists():
        logo = ImageClip(str(LOGO_PATH)).resize(width=70).set_position((WIDTH-80, 20)).set_duration(duration)
        layers.append(logo)
    
    return CompositeVideoClip(layers, size=(WIDTH, HEIGHT))

def create_enhanced_presentation(content):
    """
    Crée une présentation qui préserve fidèlement la structure Markdown
    et affiche correctement toutes les images, en masquant les marqueurs de page,
    avec des transitions fluides entre les diapositives
    """
    output_path = OUTPUT_DIR / "presentation_fidele.mp4"
    audio_path = OUTPUT_DIR / "presentation_fidele.wav"
    
    # Extraire la structure exacte du Markdown
    structure = extract_markdown_structure(content)
    all_slides = []
    full_narration = ""
    
    # Diapositives d'introduction
    intro = slide_clip("🎓 Présentation", "Introduction", duration=INTRO_DUR)
    all_slides.append(intro)
    full_narration += "Bienvenue dans cette présentation. "
 # Obtenir toutes les images disponibles pour le secours
    fallback_images = []
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        fallback_images.extend(list(BASE_DIR.glob(f"*{ext}")))
        for subfolder in ["images", "img", "assets", "media"]:
            subfolder_path = BASE_DIR / subfolder
            if subfolder_path.exists():
                fallback_images.extend(list(subfolder_path.glob(f"*{ext}")))
    
    # Traiter chaque section de la structure
    for section in structure:
        level = section['level']
        title = section['title']
        content = section['content']
        is_page_marker = section.get('is_page_marker', False)
        
        # Extraire les images de cette section
        section_images = extract_images_from_markdown(content, BASE_DIR)
        
        # Si pas d'images et qu'on a des images de secours, en utiliser une
        if not section_images and fallback_images:
            random_img = random.choice(fallback_images)
            section_images = [{'path': random_img, 'position': 0}]
        
        # Pour le niveau 1, on peut créer une diapo de titre uniquement sauf pour les marqueurs de page
        if level == 1 and title and not is_page_marker:
            title_slide = slide_clip(title, "", duration=2)
            all_slides.append(title_slide)
            full_narration += f"{title}. "
        
        # Ne pas afficher le titre des marqueurs de page
        display_title = None
        if title and not is_page_marker:
            display_title = title if level > 1 else f"Section: {title}"
        
        # Ne pas créer de slide pour les sections qui sont juste des marqueurs de page sans contenu
        content_without_title = re.sub(r'^#+\s+.*?\n', '', content, 1).strip()
        if content_without_title or not is_page_marker:
            # Créer la diapositive avec la structure exacte
            slide = slide_clip_with_exact_markdown(
                display_title,
                content,
                section_images,
                duration=SLIDE_DUR
            )
            all_slides.append(slide)
            
            # Préparer la narration
            narration_text = re.sub(r'!\[.*?\]\(.*?\)', '', content)
            narration_text = re.sub(r'#{1,6}\s+', '', narration_text)
            narration_text = re.sub(r'\n+', ' ', narration_text)
            full_narration += narration_text + ". "
        
        # Libérer la mémoire
        gc.collect()
    
    # Diapositive de conclusion
    outro = slide_clip("📘 Merci pour votre attention", "Conclusion", duration=OUTRO_DUR)
    all_slides.append(outro)
    full_narration += "Merci pour votre attention."
    
    # Générer l'audio
    print("🔊 Génération de la narration...")
    engine.save_to_file(full_narration, str(audio_path))
    engine.runAndWait()
    time.sleep(1)
    
    if not audio_path.exists():
        print("❌ Échec de la génération audio")
        return False
    
    # MÉTHODE ALTERNATIVE: Transitions avec crossfadein/crossfadeout
    print("✨ Application des transitions simples entre diapositives...")
    
    # Calculer la durée totale et la durée de chaque clip
    durations = [clip.duration for clip in all_slides]
    total_duration = sum(durations) - TRANSITION_DUR * (len(all_slides) - 1)
    
    clips_with_transitions = []
    for i, clip in enumerate(all_slides):
        if i > 0:  # Tous les clips sauf le premier ont un fade in
            clip = clip.crossfadein(TRANSITION_DUR)
        
        if i < len(all_slides) - 1:  # Tous les clips sauf le dernier ont un fade out
            clip = clip.crossfadeout(TRANSITION_DUR)
        
        # Calculer la position de départ
        start_time = sum(durations[:i]) - (i * TRANSITION_DUR)
        
        # Ajouter à la liste finale avec sa position temporelle
        clips_with_transitions.append(clip.set_start(start_time))
    
    # Créer le clip final avec tous les clips superposés
    final_clip = CompositeVideoClip(clips_with_transitions)
    
    # Ajuster la durée de l'audio
    audio = AudioFileClip(str(audio_path))
    if audio.duration > final_clip.duration:
        audio = audio.subclip(0, final_clip.duration)
    elif audio.duration < final_clip.duration:
        silence = AudioClip(lambda t: 0, duration=(final_clip.duration - audio.duration))
        audio = concatenate_videoclips([audio, silence])
    
    final_clip = final_clip.set_audio(audio)
    
    # Enregistrer la vidéo
    print(f"💾 Sauvegarde de la vidéo alternative : {output_path}")
    final_clip.write_videofile(
        str(output_path),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="faster",
        threads=4
    )
    
    print("✅ Vidéo alternative générée avec succès avec transitions fluides !")
    return True
def main():
    """Fonction principale améliorée"""
    try:
        print("📖 Lecture du fichier Markdown...")
        with INPUT_MD.open(encoding="utf-8") as f:
            content = f.read()
        
        print("🎬 Création de la présentation fidèle...")
        result = create_enhanced_presentation(content)
        
        return result
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()