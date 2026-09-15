from app import PHOTOS_DIR, THUMBS_DIR, RAW_EXTENSIONS, generate_thumbnail

for folder in PHOTOS_DIR.iterdir():
    if not folder.is_dir() or folder.name == ".thumbnails":
        continue
    for photo in folder.iterdir():
        if not photo.is_file() or photo.name.startswith("."):
            continue
        if photo.suffix.lower() in RAW_EXTENSIONS:
            continue
        thumb_path = THUMBS_DIR / folder.name / photo.name
        if not thumb_path.exists():
            print(f"Generating: {folder.name}/{photo.name}")
            generate_thumbnail(photo, THUMBS_DIR / folder.name)

print("Done.")