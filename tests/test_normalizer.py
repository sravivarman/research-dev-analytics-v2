import pandas as pd
import pytest

from core.normalizer import add_duplicate_flags, indexing_flags, normalize_quartile, parse_year


@pytest.mark.parametrize(
    ("label", "sci", "esci", "scopus"),
    [
        ("SCI", 1, 0, 0),
        ("SCIE", 1, 0, 0),
        ("ESCI", 0, 1, 0),
        ("Scopus", 0, 0, 1),
        ("Non Scopus", 0, 0, 0),
        ("Scopus + ESCI", 0, 1, 1),
    ],
)
def test_indexing_classification(label, sci, esci, scopus):
    flags = indexing_flags(label)
    assert flags["SCI_SCIE_Flag"] == sci
    assert flags["ESCI_Flag"] == esci
    assert flags["Scopus_Flag"] == scopus


@pytest.mark.parametrize("source, expected", [("Q1", "Q1"), ("q 2", "Q2"), ("Quartile 3", "Q3"), ("Q4 Journal", "Q4"), ("", "")])
def test_quartile_extraction(source, expected):
    assert normalize_quartile(source) == expected


def test_same_complete_doi_with_different_titles_requires_review():
    frame = pd.DataFrame({"DOI": ["https://doi.org/10.1234/ABC", "doi:10.1234/abc"], "Title": ["One", "Two"]})
    result = add_duplicate_flags(frame)
    assert set(result["Possible Duplicate"]) == {"Yes"}
    assert set(result["Duplicate Classification"]) == {"Review Required"}
    assert set(result["Duplicate Reason"]) == {"Same complete DOI but different titles"}


def test_same_complete_doi_and_title_is_strong_duplicate():
    frame = pd.DataFrame(
        {"DOI": ["https://doi.org/10.1234/ABC", "doi:10.1234/abc"], "Title": ["One Paper", "One paper"]}
    )
    result = add_duplicate_flags(frame)
    assert set(result["Duplicate Classification"]) == {"Strong Duplicate"}


def test_duplicate_title_detection_without_doi():
    frame = pd.DataFrame({"DOI": ["", ""], "Title": ["A Useful Paper", "A useful-paper!"]})
    result = add_duplicate_flags(frame)
    assert set(result["Possible Duplicate"]) == {"Yes"}
    assert set(result["Duplicate Classification"]) == {"Review Required"}
    assert set(result["Duplicate Reason"]) == {"Same normalized title; review required"}


def test_same_title_across_publication_types_requires_review():
    frame = pd.DataFrame(
        {"DOI": ["", ""], "Title": ["A Useful Paper", "A useful-paper!"], "Publication Type": ["Book", "Journal"]}
    )
    result = add_duplicate_flags(frame)
    assert set(result["Duplicate Classification"]) == {"Review Required"}
    assert set(result["Duplicate Reason"]) == {"Same normalized title across publication types"}


@pytest.mark.parametrize(
    "identifier",
    ["https://doi.org/10.37391/", "https://ieeexplore.ieee.org/document/12345678"],
)
def test_incomplete_doi_or_document_url_is_not_duplicate_evidence(identifier):
    frame = pd.DataFrame({"DOI": [identifier, identifier], "Title": ["Different One", "Different Two"]})
    result = add_duplicate_flags(frame)
    assert set(result["Possible Duplicate"]) == {"No"}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("https://doi.org/10.1504/IJPT.2026.154600 PDF", "10.1504/ijpt.2026.154600"),
        ("DOI: https://doi.org/10.32397/tesea.vol5.n2.571", "10.32397/tesea.vol5.n2.571"),
        ("https://onlinelibrary.wiley.com/doi/abs/10.1002/9781394384990.ch13", "10.1002/9781394384990.ch13"),
        ("https://doi.org/10.1155/etep/7935636Digital Object Identifier (DOI)", "10.1155/etep/7935636"),
    ],
)
def test_doi_extraction_from_real_workbook_patterns(source, expected):
    from core.normalizer import normalize_doi

    assert normalize_doi(source) == expected


def test_invalid_date_handling():
    year, stamp, status = parse_year("not a publication date")
    assert year is None
    assert stamp is None
    assert status == "Invalid"
