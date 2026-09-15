import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

PHOTOS_DIR = Path("/mnt/photos")
app = FastAPI()

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
def upload(file: UploadFile = File(...)):
    dest = PHOTOS_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename" : file.filename, "status": "uploaded"}
