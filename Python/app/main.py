#uvicorn main:app --reload
 
import time
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
import zipfile, os, uuid

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def main_form():
    return """
    <h2>Upload files for archiving</h2>
    <form action="/upload" enctype="multipart/form-data" method="post">
      <input name="files" type="file" multiple>
      <button type="submit">Архівувати</button>
    </form>
    """

@app.post("/upload")
async def upload_files(files: list[UploadFile]):
    start = time.time()

    if not files:
        return HTMLResponse("No files selected")

    zip_name = f"{uuid.uuid4().hex}.zip"
    zip_path = os.path.join(UPLOAD_DIR, zip_name)

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in files:
            content = await file.read()
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                f.write(content)
            zipf.write(file_path, arcname=file.filename)
            os.remove(file_path)

    tta = round((time.time() - start) * 1000, 3)

    response = FileResponse(zip_path, media_type="application/zip")
    response.headers["X-Archive-Time-Ms"] = str(tta)
    response.headers["X-Zip-Name"] = zip_name
    return response

    #return HTMLResponse(f"""<h3> Successfully! </h3> <a href="/download/{zip_name}">Download ZIP</a>""")

@app.get("/download/{zip_name}")
async def download_file(zip_name: str):
    return FileResponse(os.path.join(UPLOAD_DIR, zip_name), filename="archive_py.zip")
