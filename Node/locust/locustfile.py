from locust import HttpUser, task, between
import io
import re

class NodeArchiveUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def flow(self):

        # GET /
        r = self.client.get("/", name="GET /")
        if r.status_code != 200:
            return

        # POST /upload
        files = [
            ("files", ("file1.txt", io.BytesIO(b"Hello 1"), "text/plain")),
            ("files", ("file2.txt", io.BytesIO(b"Hello 2"), "text/plain")),
        ]

        with self.client.post("/upload", files=files, catch_response=True) as resp:

            if resp.status_code != 200:
                resp.failure("Upload failed")
                return

            data = resp.json()
            zip_name = data.get("zip_name")

            if not zip_name:
                resp.failure("No zip_name returned")
                return

            resp.success()

        self.client.get(f"/download/{zip_name}", name="GET /download")
            

        '''# extract /download/{zip}
        match = re.search(r'/download/([a-f0-9\-]+\.zip)', r.text)
        if not match:
            return

        zip_url = match.group(0)

        # GET /download/{zip}
        self.client.get(
            zip_url,
            name="GET /download"
        )'''