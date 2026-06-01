import os
import io
import zipfile
import random

from locust import (
    HttpUser,
    task,
    between,
    events
)


# ENV

FRAMEWORK = os.getenv("FRAMEWORK", "python")
VCPU = os.getenv("VCPU", "0")
CONCURRENCY = os.getenv("CONCURRENCY", "0")
RUN = os.getenv("RUN", "0")

PDF_SET = os.getenv("PDF_SET", "small")

RESULT_DIR = "/mnt/results"


# PDF PATHS


PDF_DIR = os.path.join(
    "/mnt/pdf_corpus",
    PDF_SET
)

if not os.path.exists(PDF_DIR):
    raise FileNotFoundError(
        f"PDF directory not found: {PDF_DIR}"
    )

PDF_FILES = [
    os.path.join(PDF_DIR, f)
    for f in os.listdir(PDF_DIR)
    if f.lower().endswith(".pdf")
]

if len(PDF_FILES) == 0:
    raise RuntimeError(
        f"No PDF files found in: {PDF_DIR}"
    )


# USER


class PythonArchiveUser(HttpUser):

    wait_time = between(0.01, 0.05)

    @task
    def full_flow(self):

        # SAFE MKDIR

        try:
            os.makedirs(
                RESULT_DIR,
                exist_ok=True
            )
        except Exception:
            RESULT_DIR = "/tmp"

        # TTA FILE

        TTA_FILE = os.path.join(
            RESULT_DIR,
            f"tta_{FRAMEWORK}_{PDF_SET}_{VCPU}_{CONCURRENCY}_{RUN}.txt"
        )

        # HEALTH

        with self.client.get(
            "/health",
            catch_response=True
        ) as resp:

            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(
                    f"Status {resp.status_code}"
                )

        # MAIN PAGE

        with self.client.get(
            "/",
            name="GET /",
            catch_response=True
        ) as resp:

            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(
                    "Main page unavailable"
                )
                return

        # RANDOM PDF FILES

        selected_files = random.sample(
            PDF_FILES,
            min(2, len(PDF_FILES))
        )

        files = []

        for path in selected_files:

            filename = os.path.basename(path)

            with open(path, "rb") as f:
                file_data = f.read()

            files.append(
                (
                    "files",
                    (
                        filename,
                        io.BytesIO(file_data),
                        "application/pdf"
                    )
                )
            )

        # UPLOAD

        with self.client.post(
            "/upload",
            files=files,
            name=f"POST /upload [{PDF_SET}]",
            catch_response=True
        ) as resp:

            # STATUS

            if resp.status_code != 200:

                resp.failure(
                    f"Status != 200: {resp.status_code}"
                )

                return

            # CONTENT TYPE

            content_type = resp.headers.get(
                "Content-Type",
                ""
            )

            if "application/zip" not in content_type:

                resp.failure(
                    f"Not a zip! Content-Type: {content_type}"
                )

                return

            # ARCHIVE TIME

            archive_time = resp.headers.get(
                "X-Archive-Time-Ms"
            )

            if not archive_time:

                resp.failure(
                    "Missing X-Archive-Time-Ms header"
                )

                return

            try:

                archive_time_ms = float(
                    archive_time
                )

            except ValueError:

                resp.failure(
                    f"Invalid X-Archive-Time-Ms: {archive_time}"
                )

                return

            # CUSTOM EVENT

            events.request.fire(
                request_type="ARCHIVE",
                name=f"archive_time_{PDF_SET}",
                response_time=archive_time_ms,
                response_length=0,
                exception=None,
            )

            # VALIDATE ZIP

            try:

                zip_bytes = io.BytesIO(
                    resp.content
                )

                with zipfile.ZipFile(
                    zip_bytes,
                    "r"
                ) as zipf:

                    file_list = zipf.namelist()

                    if len(file_list) == 0:

                        resp.failure(
                            "Zip is empty"
                        )

                        return

            except Exception as e:

                resp.failure(
                    f"Invalid ZIP: {str(e)}"
                )

                return

            # ZIP SIZE

            if len(resp.content) < 50:

                resp.failure(
                    "Zip too small"
                )

                return

            resp.success()

        # DOWNLOAD

        zip_name = resp.headers.get(
            "X-Zip-Name"
        )

        if not zip_name:
            return

        with self.client.get(
            f"/download/{zip_name}",
            name="GET /download",
            catch_response=True
        ) as resp:

            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(
                    "Download failed"
                )