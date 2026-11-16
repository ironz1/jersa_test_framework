from jersa.traceability import load, missing_tests, problems, render_html, uncovered


def _data(**overrides):
    data = {
        "updated": "2026-11-13",
        "requirements": [
            {"id": "R1", "text": "Reguła pierwsza", "source": "właściciel"},
            {"id": "R2", "text": "Reguła druga", "source": "właściciel"},
        ],
        "cases": [
            {
                "id": "A-01",
                "title": "Przypadek <b>",
                "level": "API",
                "smoke": True,
                "reqs": ["R1"],
                "tests": ["tests/api/test_x.py::test_one"],
                "status": "zautomatyzowany",
            }
        ],
    }
    data.update(overrides)
    return data


def test_project_matrix_is_consistent():
    assert problems(load()) == []


def test_automated_cases_point_to_existing_tests():
    assert missing_tests(load()) == []


def test_consistent_data_has_no_problems():
    assert problems(_data()) == []


def test_unknown_requirement_is_reported():
    data = _data()
    data["cases"][0]["reqs"] = ["R9"]
    assert problems(data) == ["A-01: nieznane wymaganie R9"]


def test_case_without_requirement_is_reported():
    data = _data()
    data["cases"][0]["reqs"] = []
    assert problems(data) == ["A-01: brak wymagania"]


def test_duplicate_case_id_is_reported():
    data = _data()
    data["cases"].append(dict(data["cases"][0]))
    assert problems(data) == ["A-01: powtórzone ID przypadku"]


def test_unknown_level_and_status_are_reported():
    data = _data()
    data["cases"][0].update(level="UI", status="gotowy")
    assert problems(data) == ["A-01: nieznany poziom UI", "A-01: nieznany status gotowy"]


def test_missing_test_function_is_reported(tmp_path):
    (tmp_path / "tests" / "api").mkdir(parents=True)
    (tmp_path / "tests" / "api" / "test_x.py").write_text("def test_other():\n    pass\n", "utf-8")
    assert missing_tests(_data(), tmp_path) == ["A-01: brak testu tests/api/test_x.py::test_one"]


def test_planned_cases_are_not_checked_for_tests(tmp_path):
    data = _data()
    data["cases"][0]["status"] = "zaplanowany"
    assert missing_tests(data, tmp_path) == []


def test_uncovered_lists_requirements_without_cases():
    assert uncovered(_data()) == ["R2"]


def test_render_shows_gap_and_escapes_text():
    html = render_html(_data())
    assert "LUKA" in html
    assert "Przypadek &lt;b&gt;" in html
    assert "tests/api/test_x.py" in html
