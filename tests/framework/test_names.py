from jersa.pages.names import name_pattern


def test_name_pattern_matches_any_whitespace():
    pattern = name_pattern("SUKIENKA  STELLA")
    assert pattern.search("SUKIENKA STELLA 460 zł")
    assert pattern.search("SUKIENKA  STELLA")


def test_name_pattern_escapes_special_characters():
    pattern = name_pattern("Komplet (2 szt.)")
    assert pattern.search("Komplet (2 szt.)")
    assert not pattern.search("Komplet 2 szt")
