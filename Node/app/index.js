const express = require("express");
const multer = require("multer");
const archiver = require("archiver");
const crypto = require("crypto");

const app = express();

/* ========= MULTER ========= */

const upload = multer({

  storage: multer.memoryStorage(),

  limits: {
    fileSize: 10 * 1024 * 1024,
    files: 10
  }
});

/* ========= ROUTES ========= */

app.get("/health", (req, res) => {

  res
    .status(200)
    .json({ status: "ok" });
});

/* ========= MAIN PAGE ========= */

app.get("/", (req, res) => {

  res.send(`
    <h2>Upload files for archiving</h2>

    <form
      action="/upload"
      method="post"
      enctype="multipart/form-data"
    >

      <input
        type="file"
        name="files"
        multiple
        required
      />

      <button type="submit">
        Archive
      </button>

    </form>
  `);
});

/* ========= UPLOAD ========= */

app.post(
  "/upload",
  upload.array("files"),
  async (req, res) => {

    const start =
      process.hrtime.bigint();

    try {

      if (
        !req.files ||
        req.files.length === 0
      ) {

        return res
          .status(400)
          .send("No files");
      }

      const zipName =
        `${crypto.randomUUID()}.zip`;

      res.setHeader(
        "Content-Type",
        "application/zip"
      );

      res.setHeader(
        "Content-Disposition",
        `attachment; filename="${zipName}"`
      );

      const archive = archiver(
        "zip",
        {
          zlib: { level: 1 }
        }
      );

      archive.on("error", err => {

        console.error(
          "ARCHIVE ERROR:",
          err
        );

        if (!res.headersSent) {

          res
            .status(500)
            .send("Archive error");
        }
      });

      archive.on("warning", err => {

        console.warn(
          "ARCHIVE WARNING:",
          err
        );
      });

      // HEADERS BEFORE PIPE

      const archiveTimeMs = () => {

        const end =
          process.hrtime.bigint();

        return (
          Number(end - start) /
          1_000_000
        ).toFixed(3);
      };

      res.setHeader(
        "X-Archive-Time-Ms",
        archiveTimeMs()
      );

      res.setHeader(
        "X-Zip-Name",
        zipName
      );

      archive.pipe(res);

      for (const file of req.files) {

        archive.append(
          file.buffer,
          {
            name: file.originalname
          }
        );
      }

      await archive.finalize();

    } catch (err) {

      console.error(
        "UPLOAD ERROR:",
        err
      );

      if (!res.headersSent) {

        res
          .status(500)
          .send("Internal error");
      }
    }
  }
);

/* ========= GLOBAL ERROR HANDLER ========= */

app.use((err, req, res, next) => {

  console.error(
    "GLOBAL ERROR:",
    err
  );

  if (!res.headersSent) {

    res
      .status(500)
      .send("Server error");
  }
});

/* ========= START ========= */

const PORT = 3000;

app.listen(
  PORT,
  "0.0.0.0",
  () => {

    console.log(
      `Server running on port ${PORT}`
    );
  }
);

/* GET /download/{zip} */
/*app.get("/download/:zip", (req, res) => {
  const zipPath = path.join(UPLOAD_DIR, req.params.zip);

  if (!fs.existsSync(zipPath)) {
    return res.status(404).send("Archive not found");
  }

  res.download(zipPath, "archive_node.zip");
}); */