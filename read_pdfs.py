import fitz
import os

desktop = r"c:\Users\alanb\OneDrive\Рабочий стол"
files = [
    "Описание универсального Api ExelyPMS (1.0.0).pdf",
    "Exely PMS booking API Developer manual 1.7.0.pdf",
    "Exely PMS guest profile API Developer manual 1.2.0.pdf",
]

for fname in files:
    path = os.path.join(desktop, fname)
    out = os.path.join(desktop, fname.replace(".pdf", ".txt"))
    doc = fitz.open(path)
    with open(out, "w", encoding="utf-8") as f:
        for page in doc:
            f.write(page.get_text())
    print(f"Done: {out}")
