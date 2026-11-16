"""Macierz śledzenia wymagań: wymaganie → przypadek testowy → test automatyczny.

Źródłem danych jest `docs/traceability.json`. PDF buduje `scripts/build_traceability.py`.
"""

import json
import re
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

from jersa.config import PROJECT_ROOT

DATA_FILE = PROJECT_ROOT / "docs" / "traceability.json"
LEVELS = ("Kontrakt", "API", "Baza", "E2E")
AUTOMATED = "zautomatyzowany"
PLANNED = "zaplanowany"
STATUSES = (AUTOMATED, PLANNED)

Data = dict[str, Any]


def load(path: Path = DATA_FILE) -> Data:
    return json.loads(path.read_text(encoding="utf-8"))


def problems(data: Data) -> list[str]:
    """Niespójności w danych macierzy. Pusta lista oznacza, że dane są poprawne."""
    found: list[str] = []
    requirement_ids = [r["id"] for r in data["requirements"]]
    for req_id, count in Counter(requirement_ids).items():
        if count > 1:
            found.append(f"{req_id}: powtórzone ID wymagania")
    known = set(requirement_ids)
    seen: set[str] = set()
    for case in data["cases"]:
        case_id = case["id"]
        if case_id in seen:
            found.append(f"{case_id}: powtórzone ID przypadku")
            continue
        seen.add(case_id)
        if not case["reqs"]:
            found.append(f"{case_id}: brak wymagania")
        found.extend(
            f"{case_id}: nieznane wymaganie {req}" for req in case["reqs"] if req not in known
        )
        if case["level"] not in LEVELS:
            found.append(f"{case_id}: nieznany poziom {case['level']}")
        if case["status"] not in STATUSES:
            found.append(f"{case_id}: nieznany status {case['status']}")
    return found


def missing_tests(data: Data, root: Path = PROJECT_ROOT) -> list[str]:
    """Przypadki oznaczone jako zautomatyzowane, których testu nie ma w kodzie."""
    found: list[str] = []
    for case in data["cases"]:
        if case["status"] != AUTOMATED:
            continue
        for node in case["tests"]:
            file_name, _, function = node.partition("::")
            path = root / file_name
            source = path.read_text(encoding="utf-8") if path.is_file() else ""
            if not re.search(rf"^def {re.escape(function)}\(", source, re.MULTILINE):
                found.append(f"{case['id']}: brak testu {node}")
    return found


def uncovered(data: Data) -> list[str]:
    """Wymagania, do których nie prowadzi żaden przypadek testowy."""
    covered = {req for case in data["cases"] for req in case["reqs"]}
    return [r["id"] for r in data["requirements"] if r["id"] not in covered]


_CSS = """
:root{--ink:#1f2933;--muted:#5b6770;--line:#d3dade;--soft:#f4f6f7;--green:#1c7a56;
--amber:#a65f00;--red:#b3362b}
*{box-sizing:border-box}
html,body{margin:0;background:#fff;color:var(--ink);font-family:"Segoe UI",Arial,sans-serif;
font-size:9.6pt;line-height:1.4;-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1{font-size:21pt;line-height:1.15;margin:0 0 1mm}
h2{font-size:14pt;margin:0 0 2mm;break-before:page}
h3{font-size:10.5pt;margin:4mm 0 1.2mm}
p{margin:0 0 2mm}
.lead{color:var(--muted);font-size:11pt;margin-bottom:3mm}
.date{color:var(--muted);font-size:9pt;margin-bottom:3mm}
table{border-collapse:collapse;width:100%;margin:1mm 0 2.5mm}
thead{display:table-header-group}
tr{break-inside:avoid}
th{text-align:left;border-bottom:1.4px solid var(--ink);padding:1mm 2mm 1mm 0;font-weight:700}
td{border-bottom:1px solid var(--line);padding:1mm 2mm 1mm 0;vertical-align:top}
code{font-family:Consolas,monospace;font-size:.9em}
ul,ol{margin:0 0 2mm;padding-left:5mm}
li{margin-bottom:.8mm}
.cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5mm;margin:1mm 0 3mm}
.cols div{border-top:2px solid var(--ink);padding-top:1.5mm}
.cols b{display:block;margin-bottom:.6mm}
.two{display:grid;grid-template-columns:1fr 1fr;gap:8mm}
.id{white-space:nowrap;font-weight:700}
.ok{color:var(--green);font-weight:700}
.wait{color:var(--amber)}
.gap{color:var(--red);font-weight:700}
.muted{color:var(--muted)}
.num{text-align:right;white-space:nowrap}
.small{font-size:8.6pt}
.ref{white-space:nowrap}
.grid{font-size:8.8pt}
.grid td{padding:.75mm 2mm .75mm 0}
.grid code{font-size:.86em}
"""

_INTRO = """
<h1>Macierz śledzenia wymagań</h1>
<div class="date">Traceability matrix · jersa-storefront + jersa_test_framework ·
stan na {updated}</div>
<p class="lead">Pokazuje, który test sprawdza którą regułę sklepu. Łączy trzy rzeczy:
wymaganie, przypadek testowy i test automatyczny.</p>
<h3>Do czego służy</h3>
<div class="cols">
<div><b>Czy wszystko jest pokryte?</b>Każde wymaganie ma wiersz. Pusty wiersz to luka:
reguła, której żaden test nie sprawdza.</div>
<div><b>Po co jest ten test?</b>Każdy przypadek wskazuje wymaganie. Test bez wymagania
sprawdza coś, czego nikt nie zamówił, albo brakuje spisanej reguły.</div>
<div><b>Co sprawdzić po zmianie?</b>Gdy zmienia się reguła, z jej wiersza od razu widać,
które testy trzeba poprawić i uruchomić.</div>
</div>
<div class="two">
<div>
<h3>Jak czytać</h3>
<ul>
<li><b>Wymaganie (R…)</b>: reguła biznesowa sklepu. Źródło mówi, kto ją potwierdził.</li>
<li><b>Przypadek testowy</b>: co sprawdzamy i na jakim poziomie.
Litera w ID to poziom: K kontrakt, A API, D baza, E przeglądarka (E2E).</li>
<li><b>Test automatyczny</b>: plik i funkcja pytest, która wykonuje przypadek.</li>
<li><span class="ok">Zielone ID</span>: test już działa.
<span class="wait">Pomarańczowe ID</span>: przypadek zaplanowany, testu jeszcze nie ma.</li>
<li><span class="gap">LUKA</span>: wymaganie bez żadnego przypadku.</li>
</ul>
<h3>Czego macierz nie mówi</h3>
<p>Pokazuje, że test istnieje, a nie, że jest dobry. Jakość testu ocenia przegląd kodu
i to, czy test pada, gdy zepsuje się sprawdzaną regułę.</p>
</div>
<div>
<h3>Stan</h3>
<table>
<tr><td>Wymagania</td><td class="num">{n_reqs}</td></tr>
<tr><td>Przypadki testowe</td><td class="num">{n_cases}</td></tr>
<tr><td>w tym <span class="ok">zautomatyzowane</span></td><td class="num">{n_auto}</td></tr>
<tr><td>w tym <span class="wait">zaplanowane</span></td><td class="num">{n_planned}</td></tr>
<tr><td>Wymagania bez pokrycia</td><td class="num {gap_class}">{gaps}</td></tr>
</table>
<h3>Jak aktualizować</h3>
<ol>
<li>Zmień dane w <code>docs/traceability.json</code>.</li>
<li>Uruchom <code>uv run python scripts/build_traceability.py</code>.</li>
</ol>
<p>Test <code>tests/framework/test_traceability.py</code> pilnuje w CI, żeby każdy przypadek miał
wymaganie, a każdy przypadek oznaczony jako zautomatyzowany miał test w kodzie.</p>
</div>
</div>
"""


def _case_ref(case: Data) -> str:
    css = "ok" if case["status"] == AUTOMATED else "wait"
    return f'<span class="ref {css}">{escape(case["id"])}</span>'


def _matrix_rows(data: Data) -> str:
    rows = []
    for req in data["requirements"]:
        cases = [c for c in data["cases"] if req["id"] in c["reqs"]]
        cells = "".join(
            "<td>" + ", ".join(_case_ref(c) for c in cases if c["level"] == level) + "</td>"
            for level in LEVELS
        )
        note = f'<div class="muted small">{escape(req["note"])}</div>' if req.get("note") else ""
        coverage = str(len(cases)) if cases else '<span class="gap">LUKA</span>'
        rows.append(
            f'<tr><td class="id">{escape(req["id"])}</td>'
            f"<td>{escape(req['text'])}{note}</td>"
            f'<td class="small muted">{escape(req["source"])}</td>'
            f'{cells}<td class="num">{coverage}</td></tr>'
        )
    return "".join(rows)


def _case_rows(data: Data) -> str:
    rows = []
    for case in data["cases"]:
        tests = "<br>".join(
            f"<code>{escape(node).replace('::', '<wbr>::')}</code>" for node in case["tests"]
        )
        css = "ok" if case["status"] == AUTOMATED else "wait"
        rows.append(
            f'<tr><td class="id">{escape(case["id"])}</td>'
            f"<td>{escape(case['title'])}</td>"
            f"<td>{escape(case['level'])}</td>"
            f"<td>{'smoke' if case.get('smoke') else ''}</td>"
            f"<td>{escape(', '.join(case['reqs']))}</td>"
            f'<td class="small">{tests}</td>'
            f'<td class="{css}">{escape(case["status"])}</td></tr>'
        )
    return "".join(rows)


def render_html(data: Data) -> str:
    """Cały dokument jako HTML gotowy do wydruku w PDF (A4 poziomo)."""
    gaps = uncovered(data)
    statuses = Counter(case["status"] for case in data["cases"])
    intro = _INTRO.format(
        updated=escape(data["updated"]),
        n_reqs=len(data["requirements"]),
        n_cases=len(data["cases"]),
        n_auto=statuses[AUTOMATED],
        n_planned=statuses[PLANNED],
        gaps=f"{len(gaps)} ({', '.join(gaps)})" if gaps else "0",
        gap_class="gap" if gaps else "",
    )
    level_heads = "".join(f"<th>{level}</th>" for level in LEVELS)
    return (
        '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
        f"<title>Macierz śledzenia wymagań</title><style>{_CSS}</style></head><body>"
        f"{intro}"
        "<h2>Macierz: wymagania i poziomy testów</h2>"
        '<table class="grid"><colgroup><col style="width:4%"><col style="width:36%">'
        '<col style="width:11%"><col style="width:8%"><col style="width:22%">'
        '<col style="width:9%"><col style="width:5%"><col style="width:5%"></colgroup>'
        "<thead><tr><th>ID</th><th>Wymaganie</th><th>Źródło</th>"
        f'{level_heads}<th class="num">Przypadki</th></tr></thead>'
        f"<tbody>{_matrix_rows(data)}</tbody></table>"
        "<h2>Przypadki testowe</h2>"
        '<table class="grid"><colgroup><col style="width:8%"><col style="width:34%">'
        '<col style="width:7%"><col style="width:6%"><col style="width:8%">'
        '<col style="width:27%"><col style="width:10%"></colgroup>'
        "<thead><tr><th>ID</th><th>Przypadek</th><th>Poziom</th>"
        "<th>Marker</th><th>Wymagania</th><th>Test automatyczny</th><th>Status</th></tr></thead>"
        f"<tbody>{_case_rows(data)}</tbody></table>"
        "</body></html>"
    )
