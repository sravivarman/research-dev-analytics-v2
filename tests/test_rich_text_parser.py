from core.rich_text_parser import first_bold_from_runs, looks_like_single_author


def test_one_bold_author():
    assert first_bold_from_runs([("Normal Author; ", False), ("Patil Mounica", True)]) == "Patil Mounica"


def test_multiple_bold_authors_first_wins():
    runs = [
        ("Normal Author 1; ", False),
        ("Patil Mounica", True),
        ("; Normal Author 3; ", False),
        ("Natarajan Karuppiah", True),
    ]
    assert first_bold_from_runs(runs) == "Patil Mounica"


def test_multiple_authors_inside_one_bold_run_first_wins():
    assert first_bold_from_runs([("A. Ramakrishna\n3. M. Ramesh", True)]) == "A. Ramakrishna"


def test_formatting_boundary_in_middle_of_name_is_recovered():
    assert first_bold_from_runs([("External Author, P", False), ("raveen Kumar Balachandran", True)]) == "Praveen Kumar Balachandran"


def test_numbered_bold_author_is_cleaned():
    assert first_bold_from_runs([("External Author\n", False), ("4. Praveen Kumar B", True)]) == "Praveen Kumar B"


def test_no_bold_single_author_fallback_shape():
    assert first_bold_from_runs([("S. Ravivarman", False)]) is None
    assert looks_like_single_author("S. Ravivarman")
    assert not looks_like_single_author("S. Ravivarman; N. Karuppiah")
