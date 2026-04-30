"""Unified.json → OSCAL catalog regenerator.

Ported verbatim from monorepo `data/tools/unified_to_oscal.py` with the
path-walking entrypoints stripped. Uses preserved `_oscal` metadata for
lossless regeneration.

Public surface:
    convert(unified) -> dict
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def regenerate_params(parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Regenerate OSCAL params from unified parameters."""
    result = []
    for param in parameters:
        oscal_param: dict[str, Any] = {
            "id": param.get("id", ""),
            "label": param.get("label", ""),
        }

        if param.get("description"):
            oscal_param["usage"] = param["description"]

        guidelines = param.get("guidelines", [])
        if guidelines:
            oscal_param["guidelines"] = [{"prose": g} for g in guidelines]

        if "_oscal" in param:
            props = param["_oscal"].get("props", [])
            if props:
                oscal_param["props"] = props

        result.append(oscal_param)

    return result


def regenerate_control(control: dict[str, Any]) -> dict[str, Any]:
    """Regenerate an OSCAL control from unified format."""
    oscal_data = control.get("_oscal", {})

    oscal_control: dict[str, Any] = {
        "id": control.get("oscal_id", control.get("id", "")),
        "class": oscal_data.get("class", "requirement"),
        "title": control.get("title", ""),
    }

    parameters = control.get("parameters", [])
    if parameters:
        oscal_control["params"] = regenerate_params(parameters)

    props = oscal_data.get("props", [])
    if props:
        oscal_control["props"] = props

    links = oscal_data.get("links", [])
    if links:
        oscal_control["links"] = links

    parts = oscal_data.get("parts", [])
    if parts:
        oscal_control["parts"] = parts
    else:
        oscal_control["parts"] = []

        ctrl_id = control.get("id", "")

        if control.get("statement") or control.get("statement_parts"):
            statement_part: dict[str, Any] = {
                "id": f"statement_{ctrl_id}",
                "name": "statement",
                "class": "security_requirement",
                "parts": [],
            }
            for sp in control.get("statement_parts", []):
                item: dict[str, Any] = {
                    "id": f"SR-{ctrl_id}.{sp['id']}",
                    "name": "item",
                    "props": [{"name": "label", "value": f"SR-{ctrl_id}.{sp['id']}"}],
                    "prose": sp.get("text", ""),
                }
                if "parts" in sp:
                    item["parts"] = []
                    for nested in sp["parts"]:
                        nested_id = f"SR-{ctrl_id}.{sp['id']}.{nested['id']}"
                        nested_item = {
                            "id": nested_id,
                            "name": "item",
                            "props": [{"name": "label", "value": nested_id}],
                            "prose": nested.get("text", ""),
                        }
                        item["parts"].append(nested_item)
                statement_part["parts"].append(item)
            oscal_control["parts"].append(statement_part)

        if control.get("guidance"):
            guidance_part = {
                "id": f"guidance_{ctrl_id}",
                "name": "guidance",
                "prose": control["guidance"],
            }
            oscal_control["parts"].append(guidance_part)

        assessment = control.get("assessment", {})
        for obj in assessment.get("objectives", []):
            obj_part: dict[str, Any] = {
                "id": f"assessment-objective_{obj.get('id', '')}",
                "name": "assessment-objective",
                "prose": obj.get("text", ""),
            }
            if obj.get("tests_part"):
                obj_part["links"] = [
                    {
                        "href": f"#{obj['tests_part']}",
                        "rel": "assessment-for",
                    }
                ]
            oscal_control["parts"].append(obj_part)

    return oscal_control


def regenerate_group(family: dict[str, Any]) -> dict[str, Any]:
    """Regenerate an OSCAL group from unified family."""
    oscal_data = family.get("_oscal", {})

    oscal_group: dict[str, Any] = {
        "id": family.get("oscal_id", family.get("id", "")),
        "class": oscal_data.get("class", "family"),
        "title": family.get("title", ""),
    }

    props = oscal_data.get("props", [])
    if props:
        oscal_group["props"] = props

    oscal_group["controls"] = []
    for control in family.get("controls", []):
        oscal_control = regenerate_control(control)
        oscal_group["controls"].append(oscal_control)

    return oscal_group


def convert(unified: dict[str, Any]) -> dict[str, Any]:
    """Regenerate a full OSCAL catalog from unified format.

    Returns the full OSCAL wrapper: `{"catalog": {...}}`.
    """
    oscal_catalog_data = unified.get("_oscal", {})

    if oscal_catalog_data.get("metadata"):
        metadata = oscal_catalog_data["metadata"]
    else:
        metadata = {
            "title": unified.get("metadata", {}).get("title", ""),
            "version": unified.get("metadata", {}).get("version", ""),
            "oscal-version": unified.get("metadata", {}).get("oscal_version", ""),
            "last-modified": _utcnow_iso(),
        }

    catalog: dict[str, Any] = {
        "uuid": oscal_catalog_data.get("uuid", ""),
        "metadata": metadata,
        "groups": [],
    }

    for family in unified.get("families", []):
        oscal_group = regenerate_group(family)
        catalog["groups"].append(oscal_group)

    if "back_matter" in unified:
        catalog["back-matter"] = unified["back_matter"]

    return {"catalog": catalog}


__all__ = ["convert"]
