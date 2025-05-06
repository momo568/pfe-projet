import os
import re
import time
import unicodedata
import pyttsx3
from pathlib import Path
from moviepy.editor import *
from moviepy.config import change_settings
# Ajoutez cette section en haut du fichier
import drawbot_skia.drawbot as drawBot
from drawbot_skia.drawbot import *
# Évitez d'utiliser "from drawbot_skia.drawbot import *" car cela peut créer des conflits de noms
# À la place, utilisez toujours le préfixe drawBot pour les fonctions DrawBot

# Par exemple, utilisez:
# drawBot.text(), drawBot.textBox(), etc.

# CONFIG ImageMagick
change_settings({
    "IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16\\magick.exe"
})

# CHEMINS
INPUT_MD = Path(r"C:\\Users\\OUMAIMA\\Desktop\\pfe\\eca1.md")
LOGO_PATH = Path(r"C:\\Users\\OUMAIMA\\Desktop\\pfe\\teamwill_logo.png")
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

# PARAMÈTRES
FONT_SIZE_TITLE = 50  # Reduced to leave more space
FONT_SIZE_TEXT = 36   # Reduced for better fit
FONT_SIZE_TABLE = 28  # Smaller font for tables
WIDTH, HEIGHT = 1280, 720
BG_COLOR = (255, 255, 255)
TEXT_COLOR = "black"
TABLE_HEADER_BG = (200, 220, 240)  # Plus foncé pour meilleur contraste
TABLE_ROW_BG_1 = (248, 248, 248)  # Plus subtil
TABLE_ROW_BG_2 = (255, 255, 255)
TABLE_BORDER = (180, 180, 180)  # Plus foncé pour meilleure visibilité
TEXT_MARGIN = 40  # Margin for text to prevent cutting off
INTRO_DUR = 3
OUTRO_DUR = 3
SLIDE_DUR = 8
TRANSITION_DUR = 1
ANIMATION_FRAMES = 24  # Nombre d'images par seconde pour les animations
ANIMATION_DURATION = 2 
def draw_wrapped_text(txt, x, y, max_width, line_height=FONT_SIZE_TEXT + 10):
    """Affiche du texte avec retour à la ligne automatique (word wrap)"""
    if not txt or not isinstance(txt, str):
        txt = str(txt) if txt is not None else " "
        
    words = txt.split()
    line = ""
    current_y = y  # Utiliser une variable différente pour suivre la position Y
    
    for word in words:
        test_line = line + word + " "
        drawBot.font("Helvetica", FONT_SIZE_TEXT)
        w, _ = drawBot.textSize(test_line)
        if w <= max_width:
            line = test_line
        else:
            # Utiliser drawBot.text explicitement
            drawBot.text(line.strip(), (x, current_y))
            current_y -= line_height
            line = word + " "
    if line:
        # Utiliser drawBot.text explicitement
        drawBot.text(line.strip(), (x, current_y))

def create_text_animation(text, title=None, width=WIDTH, height=HEIGHT, output_dir=ANIMATION_DIR):
    """Crée une animation de texte caractère par caractère avec DrawBot et renvoie une liste d'images"""
    if not text or not text.strip():
        text = " "

    # Calculer le nombre total d'images pour l'animation
    total_frames = int(ANIMATION_FRAMES * ANIMATION_DURATION)

    # Créer un identifiant unique pour cette animation
    text_id = slugify(text[:20])
    output_pattern = os.path.join(output_dir, f"anim_{text_id}_frame_%04d.png")

    frames = []

    try:
        print(f"  🎬 Génération animation pour: {text[:30]}...")

        # Préparer le texte pour l'animation (diviser en mots et caractères)
        words = text.split()
        total_chars = sum(len(word) for word in words) + len(words) - 1  # Compte les espaces

        for frame in range(total_frames):
            # Calculer combien de caractères doivent être affichés dans cette image
            progress = min(1.0, frame / (total_frames * 0.8))  # Animation terminée à 80% du temps
            chars_to_show = int(progress * total_chars)

            # Créer une nouvelle image DrawBot
            drawBot.newDrawing()
            drawBot.size(width, height)

            # Fond blanc
            drawBot.fill(1, 1, 1)
            drawBot.rect(0, 0, width, height)

            # Afficher le titre s'il est présent
            y_pos = height - 60
            if title:
                drawBot.font("Helvetica-Bold", FONT_SIZE_TITLE)
                drawBot.fill(0, 0, 0)
                # Utiliser drawBot.text au lieu de textBox
                drawBot.text(title, (width/2 - 200, height - 100))
                y_pos = height - 120

            # Afficher le texte caractère par caractère
            drawBot.font("Helvetica", FONT_SIZE_TEXT)
            drawBot.fill(0, 0, 0)

            display_text = ""
            char_count = 0

            for word in words:
                if char_count + len(word) <= chars_to_show:
                    display_text += word + " "
                    char_count += len(word) + 1
                else:
                    # Afficher partiellement ce mot
                    chars_left = chars_to_show - char_count
                    if chars_left > 0:
                        display_text += word[:chars_left]
                    break

            # Utiliser draw_wrapped_text avec drawBot.text au lieu de textBox
            draw_wrapped_text(display_text, TEXT_MARGIN, y_pos, width - 2 * TEXT_MARGIN)

            # Sauvegarder cette image
            frame_path = output_pattern % frame
            drawBot.saveImage(frame_path)
            frames.append(frame_path)

            # Nettoyer pour l'image suivante
            drawBot.endDrawing()

        print(f"  ✅ Animation générée: {len(frames)} images")
        return frames

    except Exception as e:
        print(f"❌ Erreur création animation: {e}")
        return None
def create_animated_text_clip(text_content, title=None, duration=SLIDE_DUR):
    """Crée un clip vidéo avec texte animé à partir d'une séquence d'images DrawBot"""
    try:
        # Renommer la variable pour éviter les conflits avec les fonctions
        input_text = text_content
        
        # Générer les images d'animation
        animation_frames = create_text_animation(input_text, title)
        
        if not animation_frames or len(animation_frames) == 0:
            # Fallback au clip de texte standard en cas d'erreur
            print("  ⚠️ Animation échouée, utilisation du texte statique")
            return create_text_clip(input_text, FONT_SIZE_TEXT, WIDTH - 2*TEXT_MARGIN, (TEXT_MARGIN, 100), duration=duration)
        
        # Créer un clip à partir des images d'animation
        clip_duration = min(ANIMATION_DURATION, duration)
        animation_clip = ImageSequenceClip(animation_frames, fps=ANIMATION_FRAMES)
        
        # Si la durée demandée est plus longue que l'animation
        if duration > ANIMATION_DURATION:
            # Créer un clip statique avec le texte complet pour la durée restante
            last_frame = animation_frames[-1]
            static_clip = ImageClip(last_frame).set_duration(duration - ANIMATION_DURATION)
            
            # Concaténer l'animation et le clip statique
            final_clip = concatenate_videoclips([animation_clip, static_clip])
            return final_clip
        else:
            # Ajuster la durée de l'animation
            return animation_clip.set_duration(duration)
            
    except Exception as e:
        print(f"❌ Erreur création clip animé: {e}")
        # Fallback au clip de texte standard en cas d'erreur
        return create_text_clip(text_content, FONT_SIZE_TEXT, WIDTH - 2*TEXT_MARGIN, (TEXT_MARGIN, 100), duration=duration)
engine = pyttsx3.init()
engine.setProperty('rate', 150)

def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")

def find_valid_image_path(base_path: Path, raw_path: str):
    original = base_path / raw_path
    if original.exists():
        return original
    else:
        alternatives = [".jpeg", ".jpg", ".png", ".gif"]
        for ext in alternatives:
            candidate = re.sub(r"\.\w+$", ext, raw_path)
            candidate_path = base_path / candidate
            if candidate_path.exists():
                return candidate_path
    return None

def clean_text_for_display(text):
    if not text or not text.strip():
        return ""
    
    # Insérer un retour à la ligne avant le symbole ❑ s'il n'est pas déjà au début d'une ligne
    text = re.sub(r'([^\n])❑', r'\1\n❑', text)
    
    # Insérer un retour à la ligne avant les numéros (1., 2., etc.) s'ils ne sont pas déjà au début d'une ligne
    text = re.sub(r'([^\n])(\d+\.)', r'\1\n\2', text)
    
    text = text.replace("\n\n", "§§§")
    lines = text.split('\n')
    formatted_lines = []

    for line in lines:
        indent = len(line) - len(line.lstrip())
        line_content = line.strip()

        if line_content.startswith(('-', '*', '•', '❑')):  # Ajout de ❑ ici
            spaces = ' ' * indent if indent > 0 else ''
            line = f"{spaces}• {line_content[1:].strip()}"
        elif re.match(r'^\d+\.', line_content):
            num_match = re.match(r'^\d+\.', line_content)
            spaces = ' ' * indent if indent > 0 else ''
            line = f"{spaces}{num_match.group()} {line_content[len(num_match.group()):].strip()}"

        formatted_lines.append(line)

    text = '\n'.join(formatted_lines)
    text = text.replace("§§§", "\n\n")

    paragraphs = text.split('\n\n')
    formatted_paragraphs = []

    for p in paragraphs:
        lines = p.split('\n')
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # On laisse intact les listes et titres
            if stripped.startswith(('•', '-', '*', '❑')) or re.match(r'^\d+\.', stripped) or re.match(r'^#+\s+', stripped):
                new_lines.append(line)
            else:
                # 🔥 Si double espace → retour à la ligne
                line = line.replace("  ", "\n")
                new_lines.append(line)

        formatted_paragraphs.append('\n'.join(new_lines))

    return '\n\n'.join(formatted_paragraphs)

def extract_images_from_text(text, base_path=BASE_DIR):
    """Extract all images from text and return a list of image paths and cleaned text"""
    lines = text.split("\n")
    cleaned_lines = []
    image_references = []
    current_image = None
    
    for i, line in enumerate(lines):
        # Check for image markdown syntax
        if "![" in line and "](" in line:
            match = re.search(r'!\[.*?\]\((.*?)\)', line)
            if match:
                img_path = match.group(1).strip()
                valid_path = find_valid_image_path(base_path, img_path)
                if valid_path:
                    current_image = valid_path
                    # Find the next non-empty line as potential image description
                    next_idx = i + 1
                    while next_idx < len(lines) and not lines[next_idx].strip():
                        next_idx += 1
                    image_references.append((valid_path, next_idx if next_idx < len(lines) else -1))
            continue

        # Keep track of other image references
        if re.search(r'\.(jpeg|jpg|png|gif|jpeeg|jpge)', line, re.IGNORECASE) and not current_image:
            # Extract potential image path
            potential_path = re.search(r'[\w/\\-]+\.(jpeg|jpg|png|gif|jpeeg|jpge)', line, re.IGNORECASE)
            if potential_path:
                img_path = potential_path.group(0)
                valid_path = find_valid_image_path(base_path, img_path)
                if valid_path:
                    current_image = valid_path
                    image_references.append((valid_path, i))
            continue

        # Skip lines that are just referencing an image/figure
        if re.search(r"voir image|figure|illustration", line, re.IGNORECASE) and not line.strip().startswith("Figure"):
            continue

        cleaned_lines.append(line)

    return image_references, "\n".join(cleaned_lines).strip()

def extract_tables_from_text(text):
    """Extract Markdown tables from text with improved format preservation"""
    lines = text.split("\n")
    table_start_indices = []
    table_end_indices = []
    in_table = False
    current_table_start = -1
    
    # Trouver le début et la fin des tableaux avec une meilleure détection
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Détecter le début du tableau - vérifier le format typique d'un tableau Markdown
        if stripped.startswith("|") and "|" in stripped[1:] and not in_table:
            current_table_start = i
            in_table = True
            
        # Vérifier la ligne de séparation (---|---) qui confirme qu'on est dans un tableau
        elif in_table and re.match(r"\|\s*[-:]+\s*\|", stripped):
            # Ceci confirme que nous sommes dans un vrai tableau Markdown
            pass
            
        # Détecter la fin du tableau - quand on quitte le format du tableau ou qu'on a une ligne vide
        elif in_table and (not stripped or not stripped.startswith("|")):
            if current_table_start >= 0:
                table_start_indices.append(current_table_start)
                table_end_indices.append(i - 1)
                current_table_start = -1
            in_table = False
    
    # Si on est toujours dans un tableau à la fin du texte
    if in_table and current_table_start >= 0:
        table_start_indices.append(current_table_start)
        table_end_indices.append(len(lines) - 1)
    
    # Extraire les tableaux avec un meilleur traitement
    tables = []
    for start, end in zip(table_start_indices, table_end_indices):
        table_lines = lines[start:end+1]
        
        # Vérifier si c'est un tableau valide (doit avoir un séparateur d'en-tête)
        has_separator = any(re.match(r"\|\s*[-:]+\s*\|", line.strip()) for line in table_lines)
        if not has_separator:
            continue
            
        # Traiter le tableau et préserver l'alignement
        table_data = []
        separator_line_index = -1
        
        for j, line in enumerate(table_lines):
            stripped = line.strip()
            # Trouver la ligne de séparation (---|---)
            if re.match(r"\|\s*[-:]+\s*\|", stripped):
                separator_line_index = j
                continue
                
            # Extraire les cellules avec une meilleure préservation du contenu
            cells = []
            # Diviser par | mais garder les cellules vides
            # Ignorer les | dans les cellules qui contiennent du markdown (ex: |texte \| texte|)
            parts = []
            current_part = ""
            escape_mode = False
            
            for char in stripped.strip("|"):
                if char == '\\':
                    escape_mode = True
                    current_part += char
                elif char == '|' and not escape_mode:
                    parts.append(current_part)
                    current_part = ""
                else:
                    current_part += char
                    escape_mode = False
            
            # Ajouter la dernière partie
            parts.append(current_part)
            
            for part in parts:
                cells.append(part.strip())
                
            table_data.append(cells)
        
        # S'assurer que toutes les lignes ont le même nombre de colonnes
        max_cols = max(len(row) for row in table_data) if table_data else 0
        for row in table_data:
            while len(row) < max_cols:
                row.append("")
        
        if table_data:  # Ajouter uniquement les tableaux non vides
            tables.append(table_data)
    
    # Supprimer les lignes de tableau du texte
    cleaned_lines = []
    i = 0
    while i < len(lines):
        if any(start <= i <= end for start, end in zip(table_start_indices, table_end_indices)):
            i += 1
            continue
        cleaned_lines.append(lines[i])
        i += 1
    
    return tables, "\n".join(cleaned_lines)

def create_text_clip(text, fontsize, width, position, align="West", duration=SLIDE_DUR):
    """Create a text clip with proper error handling for empty text"""
    if not text or not text.strip():
        text = " "  # Use a space character instead of empty string
    
    try:
        clip = TextClip(
            text, 
            fontsize=fontsize,
            color=TEXT_COLOR,
            method="caption",
            align=align,
            size=(width, None),
            # Add line spacing for better readability
            interline=1.5
        )
        return clip.set_position(position).set_duration(duration)
    except Exception as e:
        print(f"⚠️ Erreur création TextClip: {e}")
        # Fallback: create a minimal text clip
        return TextClip(" ", fontsize=fontsize, color=TEXT_COLOR,
                       method="caption", size=(width, None)
                       ).set_position(position).set_duration(duration)

def create_table_clip(table_data, width, max_height, position, duration=SLIDE_DUR):
    """Create a visual representation of a Markdown table with improved clarity"""
    if not table_data or len(table_data) == 0:
        return None
    
    try:
        # Calculer les dimensions des cellules
        num_rows = len(table_data)
        num_cols = max(len(row) for row in table_data)
        
        # Largeur minimale de cellule et plus d'espace entre les cellules
        cell_width = max(75, min(width // num_cols, 200))  # Largeur minimale augmentée
        
        # Plus d'espace pour chaque ligne
        cell_height = max(35, min(max_height / (num_rows + 1), 50))  # Hauteur minimale augmentée
        
        # Recalculer les dimensions du tableau
        table_width = int(cell_width * num_cols)
        table_height = int(cell_height * num_rows)
        
        # Ajouter un rembourrage autour du tableau
        padded_width = table_width + 20
        padded_height = table_height + 20
        
        # Créer un clip de base pour le tableau avec une bordure plus propre
        table_bg = ColorClip((padded_width, padded_height), color=(240, 240, 240)).set_duration(duration)
        inner_bg = ColorClip((table_width + 10, table_height + 10), color=(255, 255, 255)).set_duration(duration)
        inner_bg = inner_bg.set_position(("center", "center"))
        
        clips = [table_bg, inner_bg]
        
        # Créer des cellules avec plus d'espacement
        for row_idx, row in enumerate(table_data):
            # Améliorer le contraste entre l'en-tête et les lignes
            if row_idx == 0:
                bg_color = TABLE_HEADER_BG  # Plus foncé pour l'en-tête
            else:
                bg_color = TABLE_ROW_BG_1 if row_idx % 2 == 1 else TABLE_ROW_BG_2  # Alternance subtile
            
            # Ajouter des cellules pour cette ligne
            for col_idx, cell_content in enumerate(row):
                if col_idx >= num_cols:
                    continue
                
                # Format de cellule optimisé
                cell_text = format_cell_text(cell_content, max_length=int(cell_width/8))
                
                # Fond de cellule avec meilleur espacement
                cell_bg = ColorClip(
                    (max(1, int(cell_width - 4)), max(1, int(cell_height - 4))),  # Moins de bordure
                    color=bg_color
                ).set_duration(duration)
                
                # Meilleur positionnement des cellules avec plus d'espace entre elles
                cell_pos = (
                    int(col_idx * cell_width + 7),  # Décalage de 7px pour la marge
                    int(row_idx * cell_height + 7)   # Décalage de 7px pour la marge
                )
                cell_bg = cell_bg.set_position(cell_pos)
                
                # Taille de police adaptative basée sur la longueur du contenu
                if row_idx == 0:  # En-tête
                    font_size = FONT_SIZE_TABLE  # Garder l'en-tête plus grand
                else:
                    if len(str(cell_content)) > 30:
                        font_size = max(FONT_SIZE_TABLE - 6, 20)
                    elif len(str(cell_content)) > 15:
                        font_size = max(FONT_SIZE_TABLE - 3, 22)
                    else:
                        font_size = FONT_SIZE_TABLE
                
                # Césure pour le texte long au lieu de troncature
                text_width = max(1, int(cell_width - 16))  # Plus de marge dans la cellule
                text_height = max(1, int(cell_height - 12))
                
                # Créer du texte avec césure
                text_clip = TextClip(
                    cell_text,
                    fontsize=font_size,
                    color=TEXT_COLOR,
                    method="caption",
                    align="center",
                    size=(text_width, text_height)
                ).set_duration(duration)
                
                # Meilleur centrage du texte dans la cellule
                text_pos = (
                    int(col_idx * cell_width + 11),  # Meilleur centrage horizontal
                    int(row_idx * cell_height + 6)   # Meilleur positionnement vertical
                )
                text_clip = text_clip.set_position(text_pos)
                
                clips.append(cell_bg)
                clips.append(text_clip)
                
                # Ajouter un effet gras à l'en-tête
                if row_idx == 0:
                    # Ajouter une légère ombre pour simuler du texte en gras
                    shadow_clip = TextClip(
                        cell_text,
                        fontsize=font_size,
                        color="dark" + TEXT_COLOR if TEXT_COLOR != "black" else "gray20",
                        method="caption",
                        align="center",
                        size=(text_width, text_height)
                    ).set_duration(duration)
                    
                    shadow_pos = (
                        int(col_idx * cell_width + 10.5),  # Léger décalage
                        int(row_idx * cell_height + 5.5)   # Léger décalage
                    )
                    shadow_clip = shadow_clip.set_position(shadow_pos)
                    
                    # Ajouter l'ombre derrière le texte
                    clips.insert(-1, shadow_clip)
        
        # Ajouter des lignes de grille fines pour une structure de tableau plus claire
        for i in range(num_rows + 1):
            y_pos = int(i * cell_height + 5)
            line = ColorClip((table_width + 4, 1), color=TABLE_BORDER).set_duration(duration)
            line = line.set_position((5, y_pos))
            clips.append(line)
        
        for j in range(num_cols + 1):
            x_pos = int(j * cell_width + 5)
            line = ColorClip((1, table_height + 4), color=TABLE_BORDER).set_duration(duration)
            line = line.set_position((x_pos, 5))
            clips.append(line)
        
        # Créer le clip composite du tableau
        table_clip = CompositeVideoClip(clips, size=(padded_width, padded_height))
        return table_clip.set_position(position).set_duration(duration)
    
    except Exception as e:
        print(f"⚠️ Erreur création table: {e}")
        return None

def split_text_into_blocks(text):
    """Split text into smaller logical blocks for better slide content"""
    if not text or not text.strip():
        return []
    
    # Diviser d'abord par en-têtes (# Titre)
    header_pattern = re.compile(r'^(#+)\s+(.+)$', re.MULTILINE)
    headers = list(header_pattern.finditer(text))
    
    blocks = []
    
    if not headers:
        # S'il n'y a pas d'en-têtes, diviser par paragraphes
        paragraphs = re.split(r'\n\s*\n', text.strip())
        
        # Regrouper les paragraphes en blocs plus petits
        current_block = []
        current_length = 0
        
        for paragraph in paragraphs:
            stripped = paragraph.strip()
            if not stripped:
                continue
                
            # Si le bloc atteint une certaine taille, créer un nouveau bloc
            if current_length + len(stripped) > 300:  # Réduire la taille des blocs
                if current_block:
                    blocks.append('\n\n'.join(current_block))
                    current_block = []
                    current_length = 0
            
            # Les listes commencent toujours un nouveau bloc
            if current_block and (stripped.startswith(('•', '-', '*')) or re.match(r'^\d+\.', stripped)):
                # Chercher si le bloc actuel contient déjà des éléments de liste
                has_list = any(p.lstrip().startswith(('•', '-', '*')) or re.match(r'^\d+\.', p.lstrip()) for p in current_block)
                # Si oui et que le caractère est différent, commencer un nouveau bloc
                if has_list and not any(stripped.lstrip().startswith(t) for t in ('•', '-', '*', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                    blocks.append('\n\n'.join(current_block))
                    current_block = []
                    current_length = 0
            
            current_block.append(stripped)
            current_length += len(stripped)
        
        # Ajouter le dernier bloc s'il existe
        if current_block:
            blocks.append('\n\n'.join(current_block))
    else:
        # S'il y a des en-têtes, diviser le texte en sections
        for i in range(len(headers)):
            start = headers[i].start()
            end = headers[i+1].start() if i < len(headers) - 1 else len(text)
            
            section = text[start:end].strip()
            
            # Diviser la section en sous-blocs si elle est trop longue
            if len(section) > 300:
                section_paragraphs = re.split(r'\n\s*\n', section)
                
                # Le premier paragraphe contient l'en-tête
                blocks.append(section_paragraphs[0])
                
                # Regrouper les paragraphes restants en blocs plus petits
                current_block = []
                current_length = 0
                
                for paragraph in section_paragraphs[1:]:
                    stripped = paragraph.strip()
                    if not stripped:
                        continue
                    
                    # Si le bloc atteint une certaine taille, créer un nouveau bloc
                    if current_length + len(stripped) > 250:  # Taille réduite pour plus de lisibilité
                        if current_block:
                            blocks.append('\n\n'.join(current_block))
                            current_block = []
                            current_length = 0
                    
                    current_block.append(stripped)
                    current_length += len(stripped)
                
                # Ajouter le dernier bloc s'il existe
                if current_block:
                    blocks.append('\n\n'.join(current_block))
            else:
                blocks.append(section)
    
    # Vérification finale: ne pas avoir de blocs trop grands
    final_blocks = []
    for block in blocks:
        if len(block) > 400:  # Si un bloc est encore trop grand
            # Diviser en sous-blocs plus petits
            sub_paragraphs = re.split(r'\n\s*\n', block.strip())
            
            current_sub_block = []
            current_length = 0
            
            for paragraph in sub_paragraphs:
                stripped = paragraph.strip()
                if not stripped:
                    continue
                
                if current_length + len(stripped) > 350:
                    if current_sub_block:
                        final_blocks.append('\n\n'.join(current_sub_block))
                        current_sub_block = []
                        current_length = 0
                
                current_sub_block.append(stripped)
                current_length += len(stripped)
            
            if current_sub_block:
                final_blocks.append('\n\n'.join(current_sub_block))
        else:
            final_blocks.append(block)
    
    return final_blocks
def format_cell_text(text, max_length=30):  # Réduit la longueur max des cellules
    """Format cell text for better display in tables"""
    if text is None:
        return ""
        
    text = str(text).strip()
    
    # Préserver les sauts de ligne dans le contenu original
    if '\n' in text:
        lines = text.split('\n')
        if len(lines) > 2:  # Limiter à 2 lignes maximum
            return '\n'.join(lines[:2]) + '\n...'
        return text
        
    # Pour du texte d'une seule ligne, envelopper uniquement si nécessaire
    if len(text) <= max_length:
        return text
    
    # Couper intelligemment le texte long
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        if len(' '.join(current_line + [word])) <= max_length:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Le mot est trop long, le tronquer
                lines.append(word[:max_length-3] + "...")
    
    if current_line:
        lines.append(' '.join(current_line))
    
    if len(lines) > 2:  # Limiter à 2 lignes maximum
        return lines[0] + '\n' + lines[1] + '\n...'
    else:
        return '\n'.join(lines)

def slide_clip(title, text_content, images=None, tables=None, duration=SLIDE_DUR, animate_text=True):
    # Create a background
    bg = ColorClip((WIDTH, HEIGHT), color=BG_COLOR).set_duration(duration)
    
    # Create layers one by one
    layers = [bg]
    
    # Create title clip if title is provided
    title_height = 0
    if title and title.strip():
        try:
            title_clip = create_text_clip(
                title, 
                FONT_SIZE_TITLE, 
                WIDTH - 100, 
                ("center", 20),
                align="center", 
                duration=duration
            )
            title_height = title_clip.size[1]
            layers.append(title_clip)
        except Exception as e:
            print(f"⚠️ Erreur création titre: {e}")
    
    # Determine starting Y position after title
    y_position = 30 + title_height + 20
    
    # Calculate available height for content
    available_height = HEIGHT - y_position - 40
    
    # Determine layout based on content
    has_image = images and len(images) > 0
    has_table = tables and len(tables) > 0
    
    # Renommer la variable text_content pour éviter les conflits
    slide_text = text_content.strip() if text_content else " "
    
    text_y_position = y_position
    text_width = WIDTH - 2 * TEXT_MARGIN
    text_pos_x = TEXT_MARGIN
    
    if has_image:
        # If there's an image, use right side for text
        text_width = (WIDTH // 2) - TEXT_MARGIN - 20
        text_pos_x = (WIDTH // 2) + 20
    
    try:
        if animate_text:
            # Créer un clip avec texte animé
            text_clip = create_animated_text_clip(slide_text, None, duration)
            
            # Ajuster la position
            if has_image:
                text_clip = text_clip.crop(x1=0, y1=0, x2=text_width, y2=None)
                text_clip = text_clip.set_position((text_pos_x, text_y_position))
            else:
                text_clip = text_clip.set_position((text_pos_x, text_y_position))
                
            layers.append(text_clip)
            text_height = text_clip.size[1]
        else:
            # Utiliser le clip de texte standard
            text_clip = create_text_clip(
                slide_text,
                FONT_SIZE_TEXT,
                text_width,
                (text_pos_x, text_y_position),
                duration=duration
            )
            layers.append(text_clip)
            text_height = text_clip.size[1]
    except Exception as e:
        print(f"⚠️ Erreur création texte: {e}")
        text_height = 0
    
    # Le reste du code reste inchangé...
    
    # Reste du code existant pour les images, tableaux, logo...
    # (Ajoutez votre code existant pour les images et tableaux ici)
    
    # Handle images with error catching
    if has_image:
        try:
            image_path = images[0]
            # Calculate image size to fit within available space
            image_width = (WIDTH // 2) - TEXT_MARGIN - 20
            
            # Add target_resolution to reduce memory usage
            image_clip = ImageClip(str(image_path)).resize(width=image_width)
            image_height = image_clip.size[1]
            
            # Center image vertically if it's not too tall
            image_y = y_position
            if image_height < available_height:
                image_y = y_position + (available_height - image_height) // 2
                
            image_clip = image_clip.set_duration(duration).set_position((TEXT_MARGIN, image_y))
            layers.append(image_clip)
        except Exception as e:
            print(f"⚠️ Erreur image : {e}")
    
    # Handle tables with improved positioning
    if has_table:
        try:
            for i, table_data in enumerate(tables):
                # Calculate table position
                if has_image:
                    # Table goes on the same side as text
                    table_width = text_width
                    table_x = text_pos_x
                    table_y = text_y_position + text_height + 40
                else:
                    # Table goes below text
                    table_width = WIDTH - 2 * TEXT_MARGIN
                    table_x = TEXT_MARGIN
                    table_y = text_y_position + text_height + 40
                
                # Calculate maximum height for table
                table_max_height = max(1, HEIGHT - table_y - 40)
                
                # Create table clip with constraints
                table_clip = create_table_clip(
                    table_data,
                    int(table_width),
                    int(table_max_height),
                    (int(table_x), int(table_y)),
                    duration=duration
                )
                
                if table_clip:
                    layers.append(table_clip)
                
                # Only show first table per slide to avoid overcrowding
                break
        except Exception as e:
            print(f"⚠️ Erreur tableau : {e}")
    
    # Add logo
    if LOGO_PATH.exists():
        try:
            logo_clip = ImageClip(str(LOGO_PATH)).resize(width=120).set_duration(duration)
            logo_clip = logo_clip.set_position(("right", "top")).margin(right=10, top=10)
            layers.append(logo_clip)
        except Exception as e:
            print(f"⚠️ Erreur logo : {e}")
    
    # Create composite
    import gc
    result = CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
    gc.collect()
    return result

def match_images_and_tables_to_blocks(text, image_references, tables):
    """Match images and tables to text blocks with better distribution and preservation"""
    # Split text into logical blocks
    blocks = split_text_into_blocks(text)
    
    if not blocks:
        # If no text blocks, create a placeholder for tables/images
        if tables or image_references:
            blocks = [""]
        else:
            return []
    
    # Calculate optimal distribution
    num_blocks = len(blocks)
    
    # More intelligent distribution of tables to related content
    tables_per_block = [[] for _ in range(num_blocks)]
    
    # Try to match tables with relevant text blocks by looking for table references
    for table_idx, table in enumerate(tables):
        best_block = 0
        best_score = -1
        
        # Look for references to tables in blocks
        for block_idx, block in enumerate(blocks):
            block_lower = block.lower()
            score = 0
            
            # Check for table references
            if re.search(r'tableau|table', block_lower):
                score += 5
                
            # Check for content similarity with table headers
            if table and len(table) > 0 and len(table[0]) > 0:
                for header_cell in table[0]:
                    header_text = str(header_cell).lower()
                    if header_text in block_lower:
                        score += 3
                        
            # Check for numeric references that might match table index
            if re.search(rf'tableau\s*{table_idx + 1}|table\s*{table_idx + 1}', block_lower):
                score += 10
                
            # If this block has better score, assign table to it
            if score > best_score:
                best_score = score
                best_block = block_idx
        
        # If no good match found, distribute evenly
        if best_score <= 0:
            min_tables_idx = min(range(num_blocks), key=lambda i: len(tables_per_block[i]))
            tables_per_block[min_tables_idx].append(table)
        else:
            tables_per_block[best_block].append(table)
    
    # Match images to blocks similarly
    image_assignments = [[] for _ in range(num_blocks)]
    for img_path, img_line in image_references:
        # Simple assignment: distribute evenly if we can't determine position
        if img_line < 0:
            min_images_idx = min(range(num_blocks), key=lambda i: len(image_assignments[i]))
            image_assignments[min_images_idx].append(img_path)
        else:
            # Try to match with appropriate block based on proximity
            best_block = 0
            best_distance = float('inf')
            
            for i in range(num_blocks):
                # Use a simple metric: just assign to the closest block
                distance = abs(i - img_line / 10)  # Arbitrary scaling
                if distance < best_distance:
                    best_distance = distance
                    best_block = i
            
            image_assignments[best_block].append(img_path)
    
    # Create result with blocks, images, and tables
    result = []
    for i in range(num_blocks):
        # Clean and format the text for better display
        clean_text = clean_text_for_display(blocks[i])
        result.append((clean_text, image_assignments[i], tables_per_block[i]))
    
    return result
def split_markdown_into_segments(content):
    """Meilleure division du contenu Markdown en segments logiques"""
    print("📑 Analyse et découpage amélioré du contenu...")
    
    # Utilisez '## --- Page' comme séparateur de base
    pages = re.split(r"## --- Page \d+ ---", content)[1:]
    
    segments = []
    current_title = ""
    buffer = ""
    
    # Fonction pour ajouter un segment nettoyé
    def add_segment(title, content):
        if content.strip():
            # Nettoyer le titre des caractères de formatage Markdown
            clean_title = re.sub(r'^#+\s*', '', title).strip()
            segments.append((clean_title or f"Partie {len(segments)+1}", content.strip()))
    
    for i, page in enumerate(pages):
        page_content = page.strip()
        if not page_content:
            continue
            
        # Détecter les titres (##, ###) pour diviser en segments
        headers = re.finditer(r'^(#{2,3})\s+(.+)$', page_content, re.MULTILINE)
        headers_list = list(headers)
        
        if not headers_list:
            # Si pas d'en-tête, traiter la page comme un segment unique
            if buffer:
                add_segment(current_title, buffer)
                buffer = ""
            
            first_line = page_content.split('\n', 1)[0].strip()
            page_title = first_line if not first_line.startswith('#') else ""
            add_segment(page_title or f"Page {i+1}", page_content)
            current_title = ""
        else:
            # Traiter chaque section entre en-têtes
            for j, header in enumerate(headers_list):
                header_start = header.start()
                header_end = header.end()
                header_text = header.group(2)
                header_level = len(header.group(1))
                
                # Ajouter le contenu précédent s'il existe
                if j == 0 and header_start > 0:
                    # Contenu avant le premier en-tête
                    if buffer:
                        add_segment(current_title, buffer)
                    buffer = page_content[:header_start].strip()
                    if buffer:
                        add_segment(f"Introduction Page {i+1}", buffer)
                    buffer = ""
                
                # Déterminer la fin de la section actuelle
                if j < len(headers_list) - 1:
                    next_header_start = headers_list[j+1].start()
                    section_content = page_content[header_end:next_header_start]
                else:
                    section_content = page_content[header_end:]
                
                # Ajouter la section comme segment
                add_segment(header_text, section_content)
            
            current_title = ""
            buffer = ""
    
    # Ajouter le dernier buffer s'il existe
    if buffer:
        add_segment(current_title, buffer)
    
    print(f"🧩 {len(segments)} segments identifiés avec la nouvelle méthode")
    return segments
def create_full_presentation(segments):
    """Create a single presentation video from all segments with animated text"""
    print("🎬 Génération de la présentation complète avec animations...")
    
    output_path = OUTPUT_DIR / "presentation_complete.mp4"
    audio_path = OUTPUT_DIR / "presentation_complete.wav"
    
    all_slides = []
    full_narration = ""
    
    # Create intro slide with animation
    intro = slide_clip("🎓 Présentation", "Introduction", [], [], duration=INTRO_DUR, animate_text=True)
    all_slides.append(intro)
    full_narration += "Présentation. Introduction. "
    
    # Create slides for each segment
    for i, (title, body) in enumerate(segments, 1):
        print(f"  📊 Traitement segment {i}/{len(segments)}: {title}")
        
        # Extract images and tables from text
        image_references, cleaned_text = extract_images_from_text(body)
        tables, cleaned_text_without_tables = extract_tables_from_text(cleaned_text)
        
        # Match images and tables to text blocks
        block_with_content = match_images_and_tables_to_blocks(
            cleaned_text_without_tables, 
            image_references, 
            tables
        )
        
        # Handle empty results
        if not block_with_content:
            if tables:
                # If we have tables but no text blocks, create slides for tables
                for table in tables:
                    block_with_content.append(("", [], [table]))
            else:
                block_with_content = [(cleaned_text_without_tables or title, [], [])]
        
        # Add narration for this segment
        segment_narration = f"{title}. " + " ".join([block for block, _, _ in block_with_content if block])
        full_narration += segment_narration + " "
        
        # Create slides for each block with its associated content
        for j, (block, images, tables) in enumerate(block_with_content):
            # First slide of segment includes the title
            slide_title = title if j == 0 else ""
            
            # Create one slide for each table if multiple tables
            if len(tables) > 1:
                # Premier slide avec texte animé
                clip = slide_clip(slide_title, block, images, tables[:1], animate_text=True)
                all_slides.append(clip)
                
                # Slides additionnels pour les tableaux restants (sans animation)
                for idx, table in enumerate(tables[1:], 1):
                    subtitle = f"{title} (Tableau {idx+1}/{len(tables)})" if title else f"Tableau {idx+1}/{len(tables)}"
                    table_clip = slide_clip(subtitle, "", [], [table], animate_text=False)
                    all_slides.append(table_clip)
            else:
                # Cas normal - un slide avec tout (avec animation)
                clip = slide_clip(slide_title, block, images, tables, animate_text=True)
                all_slides.append(clip)
            
        # Force garbage collection between segments
        import gc
        gc.collect()
        
        # Progress reporting
        if i % 5 == 0 or i == len(segments):
            print(f"  ⏳ Progression: {i}/{len(segments)} segments traités ({int(i/len(segments)*100)}%)")
    
    # Create outro slide with animation
    outro = slide_clip("📘 Merci pour votre attention", "Conclusion", [], [], duration=OUTRO_DUR, animate_text=True)
    all_slides.append(outro)
    full_narration += "Merci pour votre attention. Conclusion."
    
    # Save full audio narration
    try:
        print("  🔊 Génération de la narration audio...")
        engine.save_to_file(full_narration.replace('\n', ' '), str(audio_path))
        engine.runAndWait()
        engine.stop()
        time.sleep(1)
    except Exception as e:
        print(f"❌ Erreur génération audio : {e}")
        return False
    
    if not audio_path.exists():
        print(f"⚠️ Audio non généré : {audio_path.name}")
        return False
    
    try:
        print("  🎵 Chargement de l'audio...")
        audio = AudioFileClip(str(audio_path))
    except Exception as e:
        print(f"❌ Erreur lecture audio : {e}")
        return False
    
    # Combine all slides with transitions
    print("  🔄 Assemblage des slides...")
    
    # Concatenate all slides with transitions
    final_clip = concatenate_videoclips(all_slides, method="compose")
    
    # Set audio to match the video duration
    audio_duration = final_clip.duration
    if audio.duration > audio_duration:
        print(f"  ✂️ Ajustement de la durée audio: {audio.duration:.1f}s → {audio_duration:.1f}s")
        audio = audio.subclip(0, audio_duration)
    elif audio.duration < audio_duration:
        # If audio is shorter, we need to extend it with silence
        silence_duration = audio_duration - audio.duration
        print(f"  ➕ Extension de l'audio avec {silence_duration:.1f}s de silence")
        silence = AudioClip(lambda t: 0, duration=silence_duration)
        audio = concatenate_audioclips([audio, silence])
    
    final_clip = final_clip.set_audio(audio)
    
    # Write the final video
    try:
        print("  💾 Écriture du fichier vidéo final...")
        # Use a lower preset for faster encoding
        final_clip.write_videofile(
            str(output_path), 
            fps=24, 
            codec='libx264', 
            preset='faster',
            audio_codec='aac',
            threads=4
        )
        print(f"✅ Vidéo complète générée : {output_path.name}")
        
        # Nettoyer les fichiers temporaires d'animation
        print("  🧹 Nettoyage des images d'animation temporaires...")
        for f in ANIMATION_DIR.glob("*.png"):
            try:
                f.unlink()
            except Exception as e:
                print(f"⚠️ Impossible de supprimer {f.name} : {e}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur écriture vidéo : {e}")
        return False
    finally:
        # Clean up resources
        if hasattr(final_clip, 'close'):
            final_clip.close()
        if hasattr(audio, 'close'):
            audio.close()
        for slide in all_slides:
            if hasattr(slide, 'close'):
                slide.close()
        import gc
        gc.collect()

# Lecture fichier markdown
print("📄 Lecture du fichier markdown...")
with INPUT_MD.open(encoding="utf-8") as f:
    content = f.read()

# Amélioration de la répartition des segments
print("📑 Analyse et découpage du contenu...")
pages = re.split(r"## --- Page \d+ ---", content)[1:]
segments, buffer, current_title = [], "", ""

for i, page in enumerate(pages):
    lines = [l.strip() for l in page.strip().split("\n") if l.strip()]
    if not lines: continue
    text = "\n".join(lines)
    heading = lines[0]
    is_new = len(lines) <= 5 or len(text) > 300 or "!" in text
    if buffer and is_new:
        segments.append((current_title or f"Partie {len(segments)+1}", buffer.strip()))
        buffer = text
        current_title = heading
    else:
        buffer += "\n\n" + text
if buffer:
    segments.append((current_title or f"Partie {len(segments)+1}", buffer.strip()))

print(f"🧩 {len(segments)} segments identifiés")

# Au lieu de générer des vidéos individuelles, créer une seule présentation complète
create_full_presentation(segments)