"""Render SUBMISSION.md to SUBMISSION.pdf.

    python tools/render_submission.py

Needs `pip install markdown` (docs-only, deliberately not in requirements.txt) and
Chrome or Edge, which ships with Windows. Headless print-to-pdf instead of a PDF
library: the browser is already installed, already does page breaks and already
does the CSS, so the whole renderer is a stylesheet plus a subprocess call.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "SUBMISSION.md"
OUTPUT = ROOT / "SUBMISSION.pdf"

BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font: 10.5pt/1.55 "Segoe UI", system-ui, sans-serif;
  color: #16181d; margin: 0; -webkit-print-color-adjust: exact;
}
h1 { font-size: 23pt; letter-spacing: -0.4pt; margin: 0 0 6pt; color: #10233f; }
h2 {
  font-size: 13.5pt; margin: 22pt 0 7pt; padding-top: 7pt;
  border-top: 1.5px solid #1f4e8c; color: #1f4e8c; break-after: avoid;
}
h3 { font-size: 11pt; margin: 13pt 0 4pt; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: #1f4e8c; text-decoration: none; }
code {
  font-family: Consolas, monospace; font-size: 8.8pt;
  background: #eef1f6; padding: 1px 4px; border-radius: 3px;
}
pre {
  background: #10131a; color: #dfe4ee; padding: 10pt 12pt; border-radius: 5px;
  font-size: 8pt; line-height: 1.45; overflow-x: auto; break-inside: avoid;
}
pre code { background: none; color: inherit; padding: 0; font-size: inherit; }
table {
  border-collapse: collapse; width: 100%; margin: 9pt 0;
  font-size: 9pt; break-inside: avoid;
}
th, td { border: 1px solid #ccd3df; padding: 5pt 7pt; text-align: left; vertical-align: top; }
th { background: #eef1f6; font-weight: 600; }
blockquote {
  margin: 10pt 0; padding: 7pt 13pt; border-left: 3px solid #1f4e8c;
  background: #f5f7fb; font-style: italic; break-inside: avoid;
}
hr { border: 0; border-top: 1px solid #dde2ea; margin: 16pt 0; }
/* The title block and the closing line are the only centred content. */
body > h1 { text-align: center; }
body > h1 + p, body > h1 + p + p { text-align: center; margin: 2pt 0; }
"""


def find_browser() -> str:
    for path in BROWSERS:
        if Path(path).exists():
            return path
    sys.exit("Chrome or Edge is required to render the PDF, and neither was found.")


def main() -> None:
    html = markdown.markdown(
        SOURCE.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    page = f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>{html}"

    # Chrome refuses to print a file it cannot read from a stable path, so the
    # intermediate HTML is a real temp file rather than a data: URL.
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "submission.html"
        source.write_text(page, encoding="utf-8")
        subprocess.run(
            [
                find_browser(),
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={OUTPUT}",
                source.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    print(f"{OUTPUT.relative_to(ROOT)}  ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
