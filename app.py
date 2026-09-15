import os
import secrets
import shutil

from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
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
    return templates.TemplateResponse(request, "index.html", {"files": files})

@app.post("/upload")
def upload(files: list[UploadFile] = File(...), user: str = Depends(verify_credentials)):
    for file in files:
        if not file.filename:
            continue
        dest = PHOTOS_DIR / file.filename
        stem, suffix, counter = dest.stem, dest.suffix, 1
        while dest.exists():
            dest = PHOTOS_DIR / f"{stem}_{counter}{suffix}"
            counter += 1
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
    return HTMLResponse('<a href="/">Done — back to gallery</a>')