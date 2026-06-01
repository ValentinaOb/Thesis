import zipfile
from locust import HttpUser, task, between
import io
import re


class PythonArchiveUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def full_flow(self):

        # GET /
        with self.client.get("/", name="GET /", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure("Main page unavailable")
                return

        # POST /upload
        files = [
            ("files", ("file1.txt", io.BytesIO(b"Hello 1"), "text/plain")),
            ("files", ("file2.txt", io.BytesIO(b"Hello 2"), "text/plain")),
        ]

        with self.client.post(
            "/upload",
            files=files,
            name="POST /upload",
            catch_response=True
        ) as resp:

            # 1. статус
            if resp.status_code != 200:
                resp.failure(f"Status != 200: {resp.status_code}")
                return

            # 2. Content-Type
            content_type = resp.headers.get("Content-Type", "")
            if "application/zip" not in content_type:
                resp.failure(f"Not a zip! Content-Type: {content_type}")
                return

            # 3. перевірка кастомного header
            archive_time = resp.headers.get("X-Archive-Time-Ms")
            if not archive_time:
                resp.failure("Missing X-Archive-Time-Ms header")
                return

            # 4. перевірка що це реально zip
            try:
                zip_bytes = io.BytesIO(resp.content)
                with zipfile.ZipFile(zip_bytes, 'r') as zipf:
                    file_list = zipf.namelist()

                    if len(file_list) == 0:
                        resp.failure("Zip is empty")
                        return

            except Exception as e:
                resp.failure(f"Invalid ZIP: {str(e)}")
                return

            # 5. (опціонально) розмір
            if len(resp.content) < 50:
                resp.failure("Zip too small")
                return

            # все ок
            resp.success()
            
        # GET /download/{zip_name}
        zip_name = resp.headers.get("X-Zip-Name")
        with self.client.get(
            f"/download/{zip_name}",
            name="GET /download/{zip}",
            catch_response=True
        ) as resp:

            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure("Download failed")
