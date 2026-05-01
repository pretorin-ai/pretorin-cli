"""Tests for custom_to_unified converters.

Covers format detection plus two representative shapes (control_families
used by GDPR/HIPAA/SOC2, and cis_safeguards with nested safeguards). The
remaining 10 converters share the same shape — covering one of each
structural family is enough.
"""

import pytest

from pretorin.frameworks import custom_to_unified
from pretorin.frameworks.validate import validate_unified


def test_detect_oscal_format_returns_none():
    oscal_like = {"uuid": "x", "groups": []}
    assert custom_to_unified.is_oscal_format(oscal_like) is True
    assert custom_to_unified.detect_custom_format(oscal_like) is None


def test_detect_control_families():
    data = {"control_families": [], "controls": []}
    assert custom_to_unified.detect_custom_format(data) == "control_families"


def test_detect_cis_safeguards():
    data = {"metadata": {}, "controls": [{"safeguards": []}]}
    assert custom_to_unified.detect_custom_format(data) == "cis_safeguards"


def test_detect_unknown_shape():
    assert custom_to_unified.detect_custom_format({"foo": "bar"}) is None


def test_convert_raises_on_oscal_input():
    with pytest.raises(custom_to_unified.UnknownCustomFormatError, match="OSCAL"):
        custom_to_unified.convert({"uuid": "x", "groups": []}, "x")


def test_convert_raises_on_unknown_shape():
    with pytest.raises(custom_to_unified.UnknownCustomFormatError, match="Unrecognized"):
        custom_to_unified.convert({"foo": "bar"}, "x")


def test_convert_control_families_shape():
    """GDPR/HIPAA/SOC2-style control_families + controls."""
    data = {
        "catalog_name": "Example Privacy Framework",
        "version": "1.0",
        "regulatory_authority": "Authority X",
        "description": "Privacy controls.",
        "control_families": [
            {
                "family_id": "DSP",
                "family_name": "Data Subject Protection",
                "description": "Rights and remedies.",
            }
        ],
        "controls": [
            {
                "control_id": "DSP-1",
                "control_name": "Right to Access",
                "family_id": "DSP",
                "control_intent": "Subjects can access their data.",
                "guidance": "Provide a request portal.",
                "citation": "Article 15",
                "obligation_type": "mandatory",
            }
        ],
    }

    unified = custom_to_unified.convert(data, "example-privacy")

    assert unified["framework_id"] == "example-privacy"
    assert unified["custom_format_type"] == "control_families"
    assert unified["metadata"]["title"] == "Example Privacy Framework"
    assert unified["metadata"]["publisher"] == "Authority X"

    family = unified["families"][0]
    assert family["id"] == "DSP"
    assert len(family["controls"]) == 1

    ctrl = family["controls"][0]
    assert ctrl["id"] == "DSP-1"
    assert ctrl["statement"] == "Subjects can access their data."
    assert ctrl["guidance"] == "Provide a request portal."
    assert ctrl["references"] == [{"title": "Article 15"}]
    assert ctrl["_custom"]["obligation_type"] == "mandatory"


def test_convert_control_families_passes_schema():
    data = {
        "control_families": [{"family_id": "ac", "family_name": "Access Control"}],
        "controls": [
            {
                "control_id": "ac-1",
                "control_name": "Policy",
                "family_id": "ac",
                "control_intent": "Develop policy.",
            }
        ],
    }
    unified = custom_to_unified.convert(data, "test")
    result = validate_unified(unified)
    assert result.valid, [str(e) for e in result.errors]


def test_convert_cis_safeguards_shape():
    """CIS pattern: each control becomes a family; nested safeguards become controls."""
    data = {
        "metadata": {"framework_name": "CIS Critical Security Controls", "version": "8.0"},
        "controls": [
            {
                "control_id": 1,
                "control_name": "Inventory of Enterprise Assets",
                "description": "Actively manage assets.",
                "safeguards": [
                    {
                        "safeguard_id": "1.1",
                        "safeguard_name": "Establish and Maintain Detailed Inventory",
                        "description": "Maintain accurate inventory.",
                        "implementation_groups": ["IG1", "IG2", "IG3"],
                        "asset_type": "Devices",
                    },
                    {
                        "safeguard_id": "1.2",
                        "safeguard_name": "Address Unauthorized Assets",
                        "description": "Quarantine unauthorized assets.",
                        "implementation_groups": ["IG2", "IG3"],
                    },
                ],
            }
        ],
    }

    unified = custom_to_unified.convert(data, "cis-v8")

    assert unified["custom_format_type"] == "cis_safeguards"
    assert unified["metadata"]["publisher"] == "Center for Internet Security"

    family = unified["families"][0]
    assert family["id"] == "control-1"
    assert family["title"] == "Inventory of Enterprise Assets"
    assert len(family["controls"]) == 2

    sg11 = family["controls"][0]
    assert sg11["id"] == "1.1"
    assert sg11["implementation_level"] == "system"
    assert sg11["_custom"]["implementation_groups"] == ["IG1", "IG2", "IG3"]


def test_convert_cis_safeguards_passes_schema():
    data = {
        "metadata": {"framework_name": "CIS"},
        "controls": [
            {
                "control_id": 1,
                "control_name": "Inventory",
                "safeguards": [
                    {"safeguard_id": "1.1", "safeguard_name": "Maintain inventory", "description": "Do it."}
                ],
            }
        ],
    }
    unified = custom_to_unified.convert(data, "cis")
    result = validate_unified(unified)
    assert result.valid, [str(e) for e in result.errors]


def test_safeguard_type_mapping():
    assert custom_to_unified.map_safeguard_type_to_impl_level(None) is None
    assert custom_to_unified.map_safeguard_type_to_impl_level("administrative") == "organization"
    assert custom_to_unified.map_safeguard_type_to_impl_level("Technical") == "system"
    assert custom_to_unified.map_safeguard_type_to_impl_level("physical") == "hybrid"
    assert custom_to_unified.map_safeguard_type_to_impl_level("unknown-type") is None
