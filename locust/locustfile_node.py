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

FRAMEWORK = os.getenv("FRAMEWORK", "node")
VCPU = os.getenv("VCPU", "0")
CONCURRENCY = os.getenv("CONCURRENCY", "0")
RUN = os.getenv("RUN", "0")

PDF_SET = os.getenv("PDF_SET", "small")

RESULT_DIR = "/mnt/results"

# PATHS

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

PDF_DIR = os.path.join(
    "/mnt/pdf_corpus",
    PDF_SET
)

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


# LOAD PDF FILES


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


class NodeArchiveUser(HttpUser):

    wait_time = between(0.01, 0.05)

    @task
    def full_flow(self):

        # HEALTH

        with self.client.get(
            "/health",
            name="GET /health",
            catch_response=True
        ) as resp:

            if resp.status_code != 200:

                resp.failure(
                    f"Status {resp.status_code}"
                )

                return

            resp.success()

        # MAIN PAGE

        with self.client.get(
            "/",
            name="GET /",
            catch_response=True
        ) as resp:

            if resp.status_code != 200:

                resp.failure(
                    "Main page unavailable"
                )

                return

            resp.success()

        # SELECT RANDOM PDF FILES

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

            if resp.status_code != 200:

                resp.failure(
                    f"Upload failed {resp.status_code}"
                )

                return

            # =============================================
            # HEADER
            # =============================================

            archive_time = resp.headers.get(
                "X-Archive-Time-Ms"
            )

            if not archive_time:

                resp.failure(
                    "Missing X-Archive-Time-Ms"
                )

                return

            try:

                archive_time = float(
                    archive_time
                )

            except ValueError:

                resp.failure(
                    "Invalid X-Archive-Time-Ms"
                )

                return

            # =============================================
            # CUSTOM EVENT
            # =============================================

            events.request.fire(
                request_type="ARCHIVE",
                name=f"archive_time_{PDF_SET}",
                response_time=archive_time,
                response_length=0,
                exception=None,
            )

            # =============================================
            # VALIDATE ZIP
            # =============================================

            try:

                zip_bytes = io.BytesIO(
                    resp.content
                )

                with zipfile.ZipFile(
                    zip_bytes,
                    "r"
                ) as zipf:

                    names = zipf.namelist()

                    if len(names) == 0:

                        resp.failure(
                            "ZIP empty"
                        )

                        return

            except Exception as e:

                resp.failure(
                    f"Invalid ZIP: {e}"
                )

                return

            resp.success()