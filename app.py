import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PHOTOS_DIR = Path("/mnt/photos")
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/files", StaticFiles(directory=PHOTOS_DIR), names="files")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <body>
      <h1>Upload a photo</h1>
      <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">Upload</button>
      </form>
    </body>
    </html>
    """

@app.post("/upload")
def upload(files: list[UploadFile] = File(...)):
    for file in files:
        dest = PHOTOS_DIR / file.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
    return HTMLResponse('<a href="/">Done — back to gallery</a>')
