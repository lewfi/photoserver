import hashlib
import os
import re
import secrets
import shutil
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image

from fastapi import (
    FastAPI, File, UploadFile, Request, Depends,
    HTTPException, status, Form,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PHOTOS_DIR = Path("/mnt/photos")
THUMBS_DIR = PHOTOS_DIR / ".thumbnails"
THUMBS_DIR.mkdir(exist_ok=True)

RAW_EXTENSIONS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2"}

app = FastAPI()

load_dotenv()
security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    valid_user = secrets.compare_digest(credentials.username, os.environ["AUTH_USERNAME"])
    valid_pass = secrets.compare_digest(credentials.password, os.environ["AUTH_PASSWORD"])
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def sanitize_folder_name(name: str) -> str:
    name = name.strip().lstrip(".")
    if not name:
        return date.today().isoformat()
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    if not name or name.lower() == "thumbnails":
        return date.today().isoformat()
    return name


def generate_thumbnail(path: Path, thumb_folder: Path):
    if path.suffix.lower() in RAW_EXTENSIONS:
        return
    try:
        img = Image.open(path)
        img.thumbnail((300, 300))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        thumb_folder.mkdir(parents=True, exist_ok=True)
        img.save(thumb_folder / path.name, "JPEG", quality=80)
    except Exception:
        pass


templates = Jinja2Templates(directory="templates")
app.mount("/files", StaticFiles(directory=PHOTOS_DIR), name="files")
app.mount("/thumbnails", StaticFiles(directory=THUMBS_DIR), name="thumbnails")


@app.get("/", response_class=HTMLResponse)
def albums(request: Request, user: str = Depends(verify_credentials)):
    total, used, free = shutil.disk_usage(PHOTOS_DIR)
    storage = {
        "used_gb": round(used / (1024**3), 1),
        "total_gb": round(total / (1024**3), 1),
        "percent": round(used / total * 100, 1),
    }

    folder_list = []
    for entry in sorted(PHOTOS_DIR.iterdir(), reverse=True):
        if not entry.is_dir() or entry.name == ".thumbnails":
            continue
        files_in_folder = [p for p in entry.iterdir() if p.is_file()]
        if not files_in_folder:
            continue
        cover = None
        thumb_folder = THUMBS_DIR / entry.name
        if thumb_folder.exists():
            for p in files_in_folder:
                if (thumb_folder / p.name).exists():
                    cover = f"{entry.name}/{p.name}"
                    break
        folder_list.append({"name": entry.name, "count": len(files_in_folder), "cover": cover})

    return templates.TemplateResponse(request, "albums.html", {"folders": folder_list, "storage": storage})


@app.get("/folder/{folder_name}", response_class=HTMLResponse)
def folder_view(
    request: Request,
    folder_name: str,
    sort: str = "date",
    type: str = "all",
    user: str = Depends(verify_credentials),
):
    safe_folder = Path(folder_name).name
    folder_path = PHOTOS_DIR / safe_folder
    if not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Album not found")

    files = [p for p in folder_path.iterdir() if p.is_file()]

    if type == "raw":
        files = [p for p in files if p.suffix.lower() in RAW_EXTENSIONS]
    elif type == "image":
        files = [p for p in files if p.suffix.lower() not in RAW_EXTENSIONS]

    if sort == "name":
        files.sort(key=lambda p: p.name.lower())
    else:
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    thumb_folder = THUMBS_DIR / safe_folder
    thumbs = {p.name for p in thumb_folder.iterdir() if p.is_file()} if thumb_folder.exists() else set()

    return templates.TemplateResponse(request, "folder.html", {
        "folder": safe_folder,
        "files": [p.name for p in files],
        "thumbs": thumbs,
        "sort": sort,
        "type": type,
    })


@app.post("/upload")
def upload(
    file: UploadFile = File(...),
    file_hash: str = Form(...),
    folder: str = Form(""),
    user: str = Depends(verify_credentials),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    safe_folder = sanitize_folder_name(folder)
    folder_path = PHOTOS_DIR / safe_folder
    folder_path.mkdir(exist_ok=True)

    dest = folder_path / file.filename
    stem, suffix, counter = dest.stem, dest.suffix, 1
    while dest.exists():
        dest = folder_path / f"{stem}_{counter}{suffix}"
        counter += 1

    hasher = hashlib.sha256()
    with open(dest, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            hasher.update(chunk)
            f.write(chunk)

    if hasher.hexdigest() != file_hash:
        dest.unlink()
        return {"filename": file.filename, "folder": safe_folder, "status": "failed"}

    generate_thumbnail(dest, THUMBS_DIR / safe_folder)
    return {"filename": dest.name, "folder": safe_folder, "status": "ok"}


@app.post("/delete")
def delete(filename: str = Form(...), folder: str = Form(...), user: str = Depends(verify_credentials)):
    safe_folder = Path(folder).name
    safe_name = Path(filename).name

    target = (PHOTOS_DIR / safe_folder / safe_name).resolve()
    if not str(target).startswith(str(PHOTOS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if target.exists():
        target.unlink()

    thumb = THUMBS_DIR / safe_folder / safe_name
    if thumb.exists():
        thumb.unlink()

    return RedirectResponse(url=f"/folder/{safe_folder}", status_code=303)