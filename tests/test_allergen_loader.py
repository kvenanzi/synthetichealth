import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.terminology.loaders import load_allergen_entries, load_allergy_reaction_entries


def test_allergen_entries_have_breadth():
    entries = load_allergen_entries()
    assert len(entries) >= 40
    displays = {entry.display for entry in entries}
    assert any(name in displays for name in ["Peanut", "Peanut Oil", "Almond", "Shrimp"])
    assert any("Penicillin" in name for name in displays)


def test_allergy_reactions_have_snomed_codes():
    reactions = load_allergy_reaction_entries()
    assert reactions, "Expected reaction entries"
    lookup = {item["display"]: item.get("code") for item in reactions}
    assert lookup.get("Anaphylaxis") == "39579001"
