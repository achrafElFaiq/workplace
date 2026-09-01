import os
import shutil
import subprocess
import tempfile

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".pdf")


class LatexCompileError(Exception):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


def compile_tex(tex_content: str, asset_dir: str = None, filename: str = "document.tex") -> bytes:
    """Compile a LaTeX source string to PDF bytes using tectonic.

    asset_dir: directory holding relative assets (images, etc.) the tex
    references — copied into the compile workspace so relative paths resolve.
    """
    with tempfile.TemporaryDirectory(prefix="jt_latex_") as tmp:
        if asset_dir and os.path.isdir(asset_dir):
            for entry in os.listdir(asset_dir):
                src = os.path.join(asset_dir, entry)
                if os.path.isfile(src) and entry.lower().endswith(IMAGE_EXTENSIONS):
                    shutil.copy(src, os.path.join(tmp, entry))

        tex_path = os.path.join(tmp, filename)
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        result = subprocess.run(
            ["tectonic", filename],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=120,
        )

        pdf_path = tex_path[:-4] + ".pdf"
        if result.returncode != 0 or not os.path.exists(pdf_path):
            raise LatexCompileError(
                "La compilation LaTeX a echoue",
                log=result.stdout + "\n" + result.stderr,
            )

        with open(pdf_path, "rb") as f:
            return f.read()
