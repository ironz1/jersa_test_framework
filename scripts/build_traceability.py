"""Buduje `docs/traceability-matrix.pdf` z `docs/traceability.json`.

Uruchomienie: `uv run python scripts/build_traceability.py`.
Przy niespójnych danych nic nie zapisuje i kończy się kodem 1.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jersa.config import PROJECT_ROOT  # noqa: E402
from jersa.traceability import load, missing_tests, problems, render_html  # noqa: E402

OUTPUT = PROJECT_ROOT / "docs" / "traceability-matrix.pdf"
FOOTER = (
    '<div style="width:100%;font-size:7pt;color:#5b6770;padding:0 12mm;'
    'display:flex;justify-content:space-between;font-family:Segoe UI,Arial,sans-serif">'
    "<span>Macierz śledzenia wymagań · jersa-storefront</span>"
    '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
)


def main() -> int:
    data = load()
    errors = problems(data) + missing_tests(data)
    if errors:
        print("Dane macierzy są niespójne:", *errors, sep="\n  ")
        return 1
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(render_html(data), wait_until="load")
        page.pdf(
            path=str(OUTPUT),
            format="A4",
            landscape=True,
            print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=FOOTER,
            margin={"top": "11mm", "bottom": "14mm", "left": "12mm", "right": "12mm"},
        )
        browser.close()
    print(f"Zapisano {OUTPUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
