import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PHOTOS_DIR = Path("/mnt/photos")
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/files", StaticFiles(directory=PHOTOS_DIR), name="files")


@app.get("/", response_class=HTMLResponse)
def gallery(request: Request):
    files = [p.name for p in PHOTOS_DIR.iterdir() if p.is_file()]
    return templates.TemplateResponse(request, "index.html", {"files": files})

@app.post("/upload")
def upload(files: list[UploadFile] = File(...)):
    for file in files:
        dest = PHOTOS_DIR / file.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
    return HTMLResponse('<a href="/">Done — back to gallery</a>')