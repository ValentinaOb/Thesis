import os
import random
import hashlib
import json
from pathlib import Path

# =========================
# CONFIG
# =========================
OUTPUT_DIR = "pdf_corpus"
SEED = 42

SETS = {
    "small": 10,
    "medium": 50,
    "large": 100
}

BASE_SIZES_MB = [2, 3, 4, 5, 6, 7, 8, 9, 10]

# =========================
# INIT
# =========================
random.seed(SEED)
Path(OUTPUT_DIR).mkdir(exist_ok=True)

manifest = []

# =========================
# PDF GENERATION
# =========================
def generate_fake_pdf_bytes(target_size_bytes):
    """
    Створює псевдо-PDF файл заданого розміру.
    PDF валідний мінімально (header + body + footer).
    """
    header = b"%PDF-1.4\n"
    footer = b"\n%%EOF"

    content_size = target_size_bytes - len(header) - len(footer)
    if content_size < 0:
        content_size = 0

    # детермінований "рандом"
    content = bytearray(random.getrandbits(8) for _ in range(content_size))

    return header + content + footer


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# =========================
# MAIN LOGIC
# =========================
for set_name, count in SETS.items():
    set_dir = Path(OUTPUT_DIR) / set_name
    set_dir.mkdir(exist_ok=True)

    for i in range(count):
        # базовий розмір + невелика випадковість (±0.5MB)
        base_mb = BASE_SIZES_MB[i % len(BASE_SIZES_MB)]
        variation = random.uniform(-0.5, 0.5)
        size_mb = max(1, base_mb + variation)

        size_bytes = int(size_mb * 1024 * 1024)

        filename = f"file_{i+1:03d}.pdf"
        filepath = set_dir / filename

        pdf_bytes = generate_fake_pdf_bytes(size_bytes)

        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        file_hash = sha256_file(filepath)

        manifest.append({
            "set": set_name,
            "file": str(filepath),
            "size_bytes": size_bytes,
            "sha256": file_hash
        })

        print(f"[+] Generated: {filepath} ({size_mb:.2f} MB)")

# =========================
# SAVE MANIFEST
# =========================
manifest_path = Path(OUTPUT_DIR) / "manifest.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump({
        "seed": SEED,
        "total_files": len(manifest),
        "files": manifest
    }, f, indent=4)

print(f"\n[✓] Manifest saved: {manifest_path}")