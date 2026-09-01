import os

from config import CV_TEX_PATH, GENERATED_DIR
from latex.compiler import compile_tex


def _dir_for(app_id: int) -> str:
    return os.path.join(GENERATED_DIR, str(app_id))


def save_generated(app_id: int, kind: str, tex_content: str) -> str:
    """Persist the LaTeX source actually used for this application's CV/cover
    letter (kind: "cv" or "lettre"). Only the .tex is kept — the PDF is
    recompiled on demand, since caching it too would be heavier for no real
    benefit (compilation is deterministic and fast)."""
    d = _dir_for(app_id)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{kind}.tex")
    with open(path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    return path


def get_generated_tex(app_id: int, kind: str) -> str | None:
    path = os.path.join(_dir_for(app_id), f"{kind}.tex")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def compile_generated(app_id: int, kind: str) -> bytes | None:
    """Recompile the persisted .tex for this application into a PDF.
    Returns None if nothing was generated for this application/kind."""
    tex_content = get_generated_tex(app_id, kind)
    if tex_content is None:
        return None
    return compile_tex(tex_content, asset_dir=os.path.dirname(CV_TEX_PATH))
