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
            allow_redirects=False,
            catch_response=True
        ) as resp:

            if resp.status_code != 200:
                resp.failure(f"Upload failed {resp.status_code}")
                return

            zip_name = None

            # перевірка — Content-Disposition
            cd = resp.headers.get("Content-Disposition", "")

            if "attachment" in cd:
                match = re.search(r'filename="?([^"]+)"?', cd)
                if match:
                    zip_name = match.group(1)

            # fallback
            if not zip_name:
                zip_name = "archive.zip"

            # перевірити що реально є тіло
            if len(resp.content) == 0:
                resp.failure("Empty file in response")
                return

            resp.success()



            tta = resp.headers.get("X-Archive-Time-Ms")
            if tta:
                resp.success()
                resp.context["tta"] = int(tta)