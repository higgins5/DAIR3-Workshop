"""
file_loader.py
File classification + content extraction for drag-and-drop uploads.

classify_file(path) -> (category, mime_type)
  category is one of:
    - 'text'        : .txt, .md, .csv, .json, .yaml, .log, source code, etc.
                      Read with read_text() and inline in the chat message.
    - 'image'       : image/jpeg, image/png, image/gif, image/webp.
                      Read with read_base64() and send via the engine's
                      native image content block.
    - 'pdf'         : application/pdf.
                      Read with read_base64() and send via the engine's
                      native document/file content block.
    - 'unsupported' : anything else. Caller should report a clear error.

By Juan B. Gutiérrez, Professor of Mathematics
University of Texas at San Antonio.

License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
"""
import os
import base64
import mimetypes

# Extensions we treat as plain text regardless of MIME guesses.
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst",
    ".csv", ".tsv", ".json", ".jsonl",
    ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".log",
    ".tex", ".bib",
    ".py", ".r", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".h",
    ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".sh", ".bash", ".zsh",
    ".html", ".htm", ".xml", ".css", ".scss", ".sass",
    ".sql",
}

IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
PDF_MIME_TYPE = "application/pdf"


def classify_file(path):
    mime, _ = mimetypes.guess_type(path)
    ext = os.path.splitext(path)[1].lower()
    if mime in IMAGE_MIME_TYPES:
        return ("image", mime)
    if mime == PDF_MIME_TYPE or ext == ".pdf":
        return ("pdf", PDF_MIME_TYPE)
    if mime and mime.startswith("text/"):
        return ("text", mime)
    if ext in TEXT_EXTENSIONS:
        return ("text", mime or "text/plain")
    return ("unsupported", mime)


def read_text(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def read_base64(path):
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("ascii")
