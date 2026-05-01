"""Round-trip tests for OSCAL ↔ unified converters.

A synthetic OSCAL catalog exercises the transform; we don't vendor a real
catalog because they run megabytes.
"""

from pretorin.frameworks import oscal_to_unified, unified_to_oscal
from pretorin.frameworks.validate import validate_unified


def _synthetic_oscal_catalog() -> dict:
    return {
        "catalog": {
            "uuid": "11111111-2222-3333-4444-555555555555",
            "metadata": {
                "title": "Synthetic Test Catalog",
                "version": "1.0",
                "oscal-version": "1.1.2",
                "published": "2026-04-30T00:00:00Z",
                "last-modified": "2026-04-30T00:00:00Z",
                "parties": [
                    {
                        "type": "organization",
                        "name": "Test Org",
                        "short-name": "TEST",
                    }
                ],
            },
            "groups": [
                {
                    "id": "ac",
                    "class": "family",
                    "title": "Access Control",
                    "props": [{"name": "sort-id", "value": "ac"}],
                    "controls": [
                        {
                            "id": "ac-01",
                            "class": "SP800-53",
                            "title": "Policy and Procedures",
                            "props": [
                                {"name": "sort-id", "value": "ac-01"},
                                {"name": "implementation-level", "value": "organization"},
                            ],
                            "params": [
                                {
                                    "id": "ac-01_prm_1",
                                    "label": "personnel or roles",
                                    "usage": "Specify personnel.",
                                }
                            ],
                            "parts": [
                                {
                                    "id": "ac-01_smt",
                                    "name": "statement",
                                    "prose": "The organization develops AC policy.",
                                },
                                {
                                    "id": "ac-01_gdn",
                                    "name": "guidance",
                                    "prose": "Reference NIST SP 800-12.",
                                },
                            ],
                            "controls": [
                                {
                                    "id": "ac-01.1",
                                    "class": "SP800-53-enhancement",
                                    "title": "Automated Enforcement",
                                    "props": [{"name": "sort-id", "value": "ac-01.01"}],
                                }
                            ],
                        },
                        {
                            "id": "ac-02",
                            "class": "SP800-53",
                            "title": "Account Management",
                            "props": [{"name": "status", "value": "withdrawn"}],
                            "parts": [
                                {
                                    "id": "ac-02_smt",
                                    "name": "statement",
                                    "prose": "Withdrawn.",
                                }
                            ],
                        },
                    ],
                }
            ],
            "back-matter": {
                "resources": [
                    {
                        "uuid": "ref-uuid-1",
                        "title": "NIST SP 800-12",
                        "rlinks": [{"href": "https://example.com/sp800-12"}],
                    }
                ]
            },
        }
    }


def test_oscal_format_detected():
    catalog = _synthetic_oscal_catalog()
    assert oscal_to_unified.is_oscal_format(catalog) is True
    assert oscal_to_unified.is_oscal_format(catalog["catalog"]) is True
    assert oscal_to_unified.is_oscal_format({"families": []}) is False


def test_oscal_to_unified_basic_shape():
    unified = oscal_to_unified.convert(_synthetic_oscal_catalog(), "synthetic")

    assert unified["framework_id"] == "synthetic"
    assert unified["source_format"] == "oscal"
    assert unified["metadata"]["title"] == "Synthetic Test Catalog"
    assert unified["metadata"]["publisher"] == "TEST"
    assert len(unified["families"]) == 1

    family = unified["families"][0]
    assert family["title"] == "Access Control"
    assert len(family["controls"]) == 2

    ac01 = family["controls"][0]
    assert ac01["id"] == "ac-01"
    assert ac01["title"] == "Policy and Procedures"
    assert ac01["status"] == "active"
    assert ac01["implementation_level"] == "organization"
    assert ac01["statement"] == "The organization develops AC policy."
    assert ac01["guidance"] == "Reference NIST SP 800-12."
    assert len(ac01["parameters"]) == 1
    assert ac01["parameters"][0]["label"] == "personnel or roles"
    assert len(ac01["enhancements"]) == 1
    assert ac01["enhancements"][0]["id"] == "ac-01.01"

    ac02 = family["controls"][1]
    assert ac02["status"] == "withdrawn"


def test_oscal_converted_artifact_passes_schema():
    unified = oscal_to_unified.convert(_synthetic_oscal_catalog(), "synthetic")
    result = validate_unified(unified)
    assert result.valid, [str(e) for e in result.errors]


def test_unified_to_oscal_round_trip_preserves_structure():
    original = _synthetic_oscal_catalog()
    unified = oscal_to_unified.convert(original, "synthetic")
    regenerated = unified_to_oscal.convert(unified)

    assert "catalog" in regenerated
    cat = regenerated["catalog"]
    assert cat["uuid"] == original["catalog"]["uuid"]
    assert cat["metadata"]["title"] == "Synthetic Test Catalog"
    assert len(cat["groups"]) == 1
    assert cat["groups"][0]["title"] == "Access Control"
    assert len(cat["groups"][0]["controls"]) == 2
    # Preserved _oscal blocks restore original parts verbatim
    assert cat["groups"][0]["controls"][0]["parts"] == original["catalog"]["groups"][0]["controls"][0]["parts"]
    # Back-matter preserved
    assert cat["back-matter"]["resources"][0]["title"] == "NIST SP 800-12"


def test_unified_to_oscal_reconstructs_parts_when_no_oscal_metadata():
    """If a unified artifact has no preserved _oscal, OSCAL parts are reconstructed."""
    unified = {
        "framework_id": "scratch",
        "version": "1.0",
        "source_format": "custom",
        "metadata": {"title": "Scratch", "version": "1.0", "last_modified": "2026-04-30T00:00:00Z"},
        "families": [
            {
                "id": "ac",
                "title": "Access Control",
                "controls": [
                    {
                        "id": "ac-01",
                        "title": "Policy",
                        "statement": "Org develops AC policy.",
                        "guidance": "See NIST SP 800-12.",
                        "statement_parts": [
                            {"id": "a", "text": "Develop policy."},
                        ],
                    }
                ],
            }
        ],
    }
    regenerated = unified_to_oscal.convert(unified)
    parts = regenerated["catalog"]["groups"][0]["controls"][0]["parts"]
    names = [p["name"] for p in parts]
    assert "statement" in names
    assert "guidance" in names
