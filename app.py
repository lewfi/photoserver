import os
import secrets
import shutil
import hashlib

from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request, Depends, HTTPException, status, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PHOTOS_DIR = Path("/mnt/photos")
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

templates = Jinja2Templates(directory="templates")
app.mount("/files", StaticFiles(directory=PHOTOS_DIR), name="files")

@app.get("/", response_class=HTMLResponse)
def gallery(request: Request, user: str = Depends(verify_credentials)):
    files = [p.name for p in PHOTOS_DIR.iterdir() if p.is_file()]
    total, used, free = shutil.disk_usage(PHOTOS_DIR)
    storage = {
        "used_gb": round(used / (1024**3), 1),
        "total_gb": round(total / (1024**3), 1),
        "percent": round(used / total * 100, 1),
    }
    return templates.TemplateResponse(request, "index.html", {"files": files, "storage": storage})

@app.post("/upload")
def upload(
    file: UploadFile = File(...),
    file_hash: str = Form(...),
    user: str = Depends(verify_credentials),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    dest = PHOTOS_DIR / file.filename
    stem, suffix, counter = dest.stem, dest.suffix, 1
    while dest.exists():
        dest = PHOTOS_DIR / f"{stem}_{counter}{suffix}"
        counter += 1

    hasher = hashlib.sha256()
    with open(dest, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            hasher.update(chunk)
            f.write(chunk)

    if hasher.hexdigest() == file_hash:
        return {"filename": dest.name, "status": "ok"}
    dest.unlink()
    return {"filename": file.filename, "status": "failed"}

@app.post("/delete")
def delete(filename: str = Form(...), user: str = Depends(verify_credentials)):
    safe_name = Path(filename).name
    target = (PHOTOS_DIR / safe_name).resolve()
    if not str(target).startswith(str(PHOTOS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if target.exists():
        target.unlink()
    return RedirectResponse(url="/", status_code=303)