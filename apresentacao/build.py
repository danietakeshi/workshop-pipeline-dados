"""Gera os HTMLs de apresentacao/ a partir dos templates + fontes (e, para a
página de introdução, a foto do instrutor).

Os HTMLs finais embutem fontes/foto como data URI (base64) para ficar 100%
independentes — abrem em qualquer navegador, sem internet. Rode este script
de novo depois de editar qualquer *.template.html.

Uso: python apresentacao/build.py
"""

import base64
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONTS_DIR = ROOT / "fonts"


def b64(path):
    return base64.b64encode(path.read_bytes()).decode("ascii")


def build_guia():
    template = (ROOT / "guia-workshop.template.html").read_text(encoding="utf-8")
    out = template.replace(
        "{{FONT_REGULAR_B64}}", b64(FONTS_DIR / "JetBrainsMono-Regular.ttf")
    ).replace(
        "{{FONT_BOLD_B64}}", b64(FONTS_DIR / "JetBrainsMono-Bold.ttf")
    )
    output = ROOT / "guia-workshop.html"
    output.write_text(out, encoding="utf-8")
    print(f"[build] {output} ({len(out):,} bytes)")


def build_introducao():
    photo_path = ROOT / "foto-instrutor.jpg"
    photo_mime = mimetypes.guess_type(photo_path.name)[0] or "image/jpeg"
    photo_src = f"data:{photo_mime};base64,{b64(photo_path)}"

    template = (ROOT / "introducao.template.html").read_text(encoding="utf-8")
    out = template.replace(
        "{{FONT_REGULAR_B64}}", b64(FONTS_DIR / "JetBrainsMono-Regular.ttf")
    ).replace(
        "{{FONT_BOLD_B64}}", b64(FONTS_DIR / "JetBrainsMono-Bold.ttf")
    ).replace(
        "{{PHOTO_SRC}}", photo_src
    )
    output = ROOT / "introducao.html"
    output.write_text(out, encoding="utf-8")
    print(f"[build] {output} ({len(out):,} bytes)")


def main():
    build_guia()
    build_introducao()


if __name__ == "__main__":
    main()
