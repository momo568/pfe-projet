import os
import re
import time
import unicodedata
import pyttsx3
from pathlib import Path
from moviepy.editor import *
from moviepy.config import change_settings

# CONFIG ImageMagick
change_settings({
    "IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16\\magick.exe"
})

# CHEMINS
INPUT_MD = Path(r"C:\\Users\\OUMAIMA\\Desktop\\pfe\\eca1.md")
AVATAR_VIDEO = Path(r"C:\\Users\\OUMAIMA\\Desktop\\pfe\\avatar.mp4")
LOGO_PATH = Path(r"C:\\Users\\OUMAIMA\\Desktop\\pfe\\teamwill_logo.png")
BASE_DIR = INPUT_MD.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Nettoyage fichiers audio corrompus
for f in OUTPUT_DIR.glob("*.wav"):
    try:
        f.unlink()
    except Exception as e:
        print(f"❌ Impossible de supprimer {f.name} : {e}")

# PARAMÈTRES
FONT_SIZE_TITLE = 60
FONT_SIZE_TEXT = 42
WIDTH, HEIGHT = 1280, 720
BG_COLOR = (255, 255, 255)
TEXT_COLOR = "black"
INTRO_DUR = 3
OUTRO_DUR = 3
SLIDE_DUR = 8
TRANSITION_DUR = 1

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

def split_text_into_blocks(text):
    """Split text into logical blocks based on paragraphs or bullet points"""
    blocks = re.split(r'\n\s*\n|(?=❑|❖|•|- )', text)
    # Remove empty blocks and short fragments
    return [b.strip() for b in blocks if len(b.strip()) > 20]

def match_images_to_blocks(text, image_references):
    """Match images to the closest text blocks"""
    blocks = split_text_into_blocks(text)
    
    if not blocks:
        return []
    
    # Calculate line numbers for each block
    block_line_ranges = []
    line_count = 0
    for block in blocks:
        start_line = line_count
        block_lines = len(block.split('\n'))
        line_count += block_lines
        block_line_ranges.append((start_line, line_count, block))
    
    # Match images to blocks based on proximity
    result = []
    for i, (block_start, block_end, block_text) in enumerate(block_line_ranges):
        matching_images = []
        
        for img_path, img_line in image_references:
            # If image appears before this block but after previous block
            if (i > 0 and block_line_ranges[i-1][1] <= img_line < block_start) or \
               (i == 0 and img_line < block_start) or \
               (block_start <= img_line < block_end):
                matching_images.append(img_path)
        
        result.append((block_text, matching_images))
    
    return result

def create_text_clip(text, fontsize, width, position, align="West", duration=SLIDE_DUR):
    """Create a text clip with proper error handling for empty text"""
    if not text or not text.strip():
        text = " "  # Use a space character instead of empty string
    
    try:
        clip = TextClip(text, fontsize=fontsize, color=TEXT_COLOR,
                        method="caption", align=align,
                        size=(width, None))
        return clip.set_position(position).set_duration(duration)
    except Exception as e:
        print(f"⚠️ Erreur création TextClip: {e}")
        # Fallback: create a minimal text clip
        return TextClip(" ", fontsize=fontsize, color=TEXT_COLOR,
                       method="caption", size=(width, None)
                       ).set_position(position).set_duration(duration)

def slide_clip(title, text, images=None, duration=SLIDE_DUR):
    # Create a simpler background (using a solid color instead of an array)
    bg = ColorClip((WIDTH, HEIGHT), color=BG_COLOR).set_duration(duration)
    
    # Create layers one by one and immediately add to a list to avoid keeping multiple references
    layers = [bg]
    
    # Create title clip if title is provided
    if title and title.strip():
        try:
            title_clip = create_text_clip(
                title, 
                FONT_SIZE_TITLE, 
                WIDTH - 100, 
                ("center", 30), 
                align="center", 
                duration=duration
            )
            layers.append(title_clip)
        except Exception as e:
            print(f"⚠️ Erreur création titre: {e}")
    
    # Handle text
    text = text.strip() if text else " "
    text_width = WIDTH // 2 - 60 if images else WIDTH - 120
    text_pos_x = WIDTH // 2 + 30 if images else 60
    
    try:
        text_clip = create_text_clip(
            text,
            FONT_SIZE_TEXT,
            text_width,
            (text_pos_x, 150),
            duration=duration
        )
        layers.append(text_clip)
    except Exception as e:
        print(f"⚠️ Erreur création texte: {e}")
    
    # Handle avatar video with memory optimization
    if not images and AVATAR_VIDEO.exists():
        try:
            # Use lower resolution and reduced frame rate
            avatar_clip = VideoFileClip(str(AVATAR_VIDEO), audio=False, target_resolution=(360, 640))
            avatar_clip = avatar_clip.loop(duration=duration).resize(width=WIDTH // 2 - 80)
            avatar_clip = avatar_clip.set_position((50, 150))
            layers.append(avatar_clip)
        except Exception as e:
            print(f"⚠️ Erreur avatar : {e}")
    
    # Handle images with error catching
    if images and images[0]:
        try:
            image_path = images[0]
            # Add target_resolution to reduce memory usage
            image_clip = ImageClip(str(image_path)).resize(width=WIDTH // 2 - 60)
            image_clip = image_clip.set_duration(duration).set_position((50, 150))
            layers.append(image_clip)
        except Exception as e:
            print(f"⚠️ Erreur image : {e}")
    
    # Add logo
    if LOGO_PATH.exists():
        try:
            logo_clip = ImageClip(str(LOGO_PATH)).resize(width=150).set_duration(duration)
            logo_clip = logo_clip.set_position(("right", "top")).margin(right=20, top=20)
            layers.append(logo_clip)
        except Exception as e:
            print(f"⚠️ Erreur logo : {e}")
    
    # Create composite with explicit garbage collection
    import gc
    result = CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
    gc.collect()
    return result
def build_video(title, body, index):
    import gc
    
    # [existing code...]
    
    # Process videos in smaller chunks with gc between steps
    for i, (block, images) in enumerate(block_with_images):
        slide_title = title if i == 0 else ""
        clip = slide_clip(slide_title, block, images)
        slides.append(clip)
        gc.collect()  # Force garbage collection between slides
    
    # [rest of function...]
    
    # Clean up after writing video
    final.close()
    if hasattr(audio, 'close'):
        audio.close()
    for slide in slides:
        if hasattr(slide, 'close'):
            slide.close()
    gc.collect()
def transition(c1, c2, duration=1):
    return concatenate_videoclips([
        c1.crossfadeout(duration),
        c2.crossfadein(duration)
    ], method="compose")

def build_video(title, body, index):
    print(f"\n🎬 Génération : {title}")
    safe_title = slugify(title[:20])
    audio_path = OUTPUT_DIR / f"{index:02d}_{safe_title}.wav"
    video_path = OUTPUT_DIR / f"{index:02d}_{safe_title}.mp4"

    # Extract images and prepare text
    image_references, cleaned_text = extract_images_from_text(body)
    block_with_images = match_images_to_blocks(cleaned_text, image_references)
    
    # Handle empty results
    if not block_with_images:
        # Create a simple block with no images if no blocks were found
        block_with_images = [(cleaned_text or title, [])]
    
    # Save audio
    try:
        # Join all text blocks for audio narration
        narration_text = f"{title}. " + " ".join([block for block, _ in block_with_images])
        engine.save_to_file(narration_text.replace('\n', ' '), str(audio_path))
        engine.runAndWait()
        engine.stop()
        time.sleep(1)
    except Exception as e:
        print(f"❌ Erreur génération audio : {e}")
        return

    if not audio_path.exists():
        print(f"⚠️ Audio non généré : {audio_path.name}")
        return

    try:
        audio = AudioFileClip(str(audio_path))
    except Exception as e:
        print(f"❌ Erreur lecture audio : {e}")
        return

    # Create slides for each block with its associated images
    slides = []
    for i, (block, images) in enumerate(block_with_images):
        # First slide includes the title
        slide_title = title if i == 0 else ""
        clip = slide_clip(slide_title, block, images)
        slides.append(clip)

    if not slides:
        print(f"⚠️ Aucune slide trouvée pour : {title}")
        return

    # Combine all slides with transitions
    full = slides[0]
    for s in slides[1:]:
        full = transition(full, s, TRANSITION_DUR)
    full = full.set_audio(audio)

    # Add intro and outro
    intro = slide_clip(f"🎓 {title}", "Introduction", [], duration=INTRO_DUR)
    outro = slide_clip("📘 Merci pour votre attention", "Conclusion", [], duration=OUTRO_DUR)

    final = concatenate_videoclips([intro, full, outro], method="compose")

    try:
        final.write_videofile(str(video_path), fps=24)
        print(f"✅ Vidéo générée : {video_path.name}")
    except Exception as e:
        print(f"❌ Erreur écriture vidéo : {e}")

# Lecture fichier markdown
with INPUT_MD.open(encoding="utf-8") as f:
    content = f.read()

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

for i, (title, body) in enumerate(segments, 1):
    build_video(title, body, i)