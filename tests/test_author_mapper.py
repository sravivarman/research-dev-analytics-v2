from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from core.author_mapper import apply_author_mappings, load_mapping, save_mapping, suggest_mappings


def test_author_name_normalization_variants():
    names = ["N. Karuppiah", "Karuppiah N", "Karuppiah Natarajan", "Natarajan Karuppiah"]
    suggested = suggest_mappings(names)
    assert len(set(suggested.values())) == 1
    assert suggested["N. Karuppiah"] == "Natarajan Karuppiah"


def test_saved_mapping_is_visible_and_applied():
    frame = pd.DataFrame({
        "Original Faculty Name": ["P. Balachandran"], "Publication ID": ["A"], "Publication Type": ["Journal"]
    })
    before = apply_author_mappings(frame, {})
    mapped = apply_author_mappings(frame, {"P. Balachandran": "Praveen Kumar Balachandran"})
    assert before.loc[0, "Faculty Name"] == "P. Balachandran"
    assert mapped.loc[0, "Faculty Name"] == "Praveen Kumar Balachandran"
    assert mapped.loc[0, "Mapping Status"] == "User mapped"


def test_frequent_clean_variant_becomes_canonical():
    names = ["Ravivarman Shanmugasundaram"] * 3 + ["Ravivarman Shanmugasundaramc", "Dr. S. Ravivarman"]
    suggested = suggest_mappings(names)
    assert suggested["Ravivarman Shanmugasundaramc"] == "Ravivarman Shanmugasundaram"


def test_user_mapping_persists_to_json():
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "author_mapping.json"
        save_mapping({"N. Karuppiah": "Karuppiah Natarajan"}, path)
        assert load_mapping(path) == {"N. Karuppiah": "Karuppiah Natarajan"}
