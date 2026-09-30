"""Gera apresentacao/guia-workshop.html a partir do template + fontes.

O HTML final embute as fontes como data URI (base64) para ficar 100%
independente — abre em qualquer navegador, sem internet. Rode este script
de novo depois de editar guia-workshop.template.html.

Uso: python apresentacao/build.py
"""

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "guia-workshop.template.html"
OUTPUT = ROOT / "guia-workshop.html"
FONTS_DIR = ROOT / "fonts"


def b64(path):
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main():
    template = TEMPLATE.read_text(encoding="utf-8")
    out = template.replace(
        "{{FONT_REGULAR_B64}}", b64(FONTS_DIR / "JetBrainsMono-Regular.ttf")
    ).replace(
        "{{FONT_BOLD_B64}}", b64(FONTS_DIR / "JetBrainsMono-Bold.ttf")
    )
    OUTPUT.write_text(out, encoding="utf-8")
    print(f"[build] {OUTPUT} ({len(out):,} bytes)")


if __name__ == "__main__":
    main()
