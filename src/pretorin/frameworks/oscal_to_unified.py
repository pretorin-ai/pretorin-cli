"""OSCAL catalog → unified.json converter.

Ported verbatim from monorepo `data/tools/oscal_to_unified.py` with the
path-walking entrypoints stripped. Keeps lossless OSCAL regeneration via the
preserved `_oscal` blocks.

Public surface:
    is_oscal_format(data) -> bool
    convert(catalog_data, framework_id) -> dict
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_oscal_format(data: dict[str, Any]) -> bool:
    """Detect OSCAL shape from in-memory dict."""
    if "catalog" in data:
        inner = data["catalog"]
        return isinstance(inner, dict) and "uuid" in inner and "groups" in inner
    return "uuid" in data and "groups" in data


def extract_sort_id(control: dict[str, Any]) -> str:
    for prop in control.get("props", []):
        if prop.get("name") == "sort-id":
            value = prop.get("value", "")
            return str(value) if value else ""
    return ""


def extract_status(control: dict[str, Any]) -> str:
    """Return 'active' or 'withdrawn'."""
    for prop in control.get("props", []):
        if prop.get("name") == "status":
            value = prop.get("value", "").lower()
            if value == "withdrawn":
                return "withdrawn"
    return "active"


def extract_implementation_level(control: dict[str, Any]) -> str | None:
    """Returns 'organization', 'system', 'hybrid', or None."""
    levels = set()
    for prop in control.get("props", []):
        if prop.get("name") == "implementation-level":
            value = prop.get("value", "").lower()
            if value in ("organization", "system"):
                levels.add(value)

    if len(levels) == 2:
        return "hybrid"
    elif len(levels) == 1:
        return str(levels.pop())
    return None


def extract_statement_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recursively extract OSCAL statement parts into unified format."""
    result = []
    for part in parts:
        part_id = part.get("id", "")
        label = ""
        for prop in part.get("props", []):
            if prop.get("name") == "label":
                label = prop.get("value", "")
                break

        statement_part: dict[str, Any] = {
            "id": label or (part_id.split(".")[-1] if "." in part_id else part_id),
            "text": part.get("prose", ""),
        }

        if "parts" in part:
            nested = extract_statement_parts(part.get("parts", []))
            if nested:
                statement_part["parts"] = nested

        result.append(statement_part)

    return result


def extract_control_parts(control: dict[str, Any]) -> dict[str, Any]:
    """Extract statement, guidance, and assessment from control parts."""
    result: dict[str, Any] = {
        "statement": "",
        "statement_parts": [],
        "guidance": "",
        "assessment": {
            "objectives": [],
            "methods": ["examine", "interview", "test"],
        },
    }

    for part in control.get("parts", []):
        name = part.get("name", "")

        if name == "statement":
            prose_parts = []
            nested_parts = part.get("parts", [])
            if nested_parts:
                result["statement_parts"] = extract_statement_parts(nested_parts)
                for sp in result["statement_parts"]:
                    text = sp.get("text", "")
                    if text:
                        prose_parts.append(f"{sp['id']}. {text}")
            result["statement"] = "\n".join(prose_parts) if prose_parts else part.get("prose", "")

        elif name == "guidance":
            result["guidance"] = part.get("prose", "")

        elif name == "assessment-objective":
            obj_id = part.get("id", "")
            prose = part.get("prose", "")
            tests_part = ""
            for link in part.get("links", []):
                if link.get("rel") == "assessment-for":
                    href = link.get("href", "")
                    tests_part = href.lstrip("#")
                    break

            result["assessment"]["objectives"].append(
                {
                    "id": obj_id.replace("assessment-objective_", ""),
                    "text": prose,
                    "tests_part": tests_part,
                }
            )

    return result


def extract_parameters(params: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OSCAL params to unified parameters."""
    result = []
    for param in params:
        unified_param: dict[str, Any] = {
            "id": param.get("id", ""),
            "label": param.get("label", ""),
            "description": param.get("usage", ""),
        }

        guidelines = []
        for guideline in param.get("guidelines", []):
            if "prose" in guideline:
                guidelines.append(guideline["prose"])
        if guidelines:
            unified_param["guidelines"] = guidelines

        unified_param["_oscal"] = {"props": param.get("props", [])}
        result.append(unified_param)

    return result


def extract_references(links: list[dict[str, Any]], back_matter: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert OSCAL links to references with resolved titles/URLs from back-matter."""
    result = []
    resources_by_uuid: dict[str, dict[str, Any]] = {}

    for resource in back_matter.get("resources", []):
        uuid = resource.get("uuid", "")
        if uuid:
            resources_by_uuid[uuid] = resource

    for link in links:
        href = link.get("href", "")
        if href.startswith("#"):
            uuid = href[1:]
            resource = resources_by_uuid.get(uuid, {})
            if resource:
                ref: dict[str, Any] = {"uuid": uuid}
                if "title" in resource:
                    ref["title"] = resource["title"]
                for rlink in resource.get("rlinks", []):
                    if "href" in rlink:
                        ref["url"] = rlink["href"]
                        break
                result.append(ref)

    return result


def convert_enhancement(enhancement: dict[str, Any]) -> dict[str, Any]:
    """Convert an OSCAL control enhancement to unified format."""
    sort_id = extract_sort_id(enhancement)
    impl_level = extract_implementation_level(enhancement)
    parts_data = extract_control_parts(enhancement)

    unified_enh: dict[str, Any] = {
        "id": sort_id or enhancement.get("id", ""),
        "title": enhancement.get("title", ""),
    }

    if impl_level:
        unified_enh["implementation_level"] = impl_level
    if parts_data["statement"]:
        unified_enh["statement"] = parts_data["statement"]
    if parts_data["guidance"]:
        unified_enh["guidance"] = parts_data["guidance"]

    params = enhancement.get("params", [])
    if params:
        unified_enh["parameters"] = extract_parameters(params)

    if parts_data["assessment"]["objectives"]:
        unified_enh["assessment"] = parts_data["assessment"]

    return unified_enh


def convert_control(
    control: dict[str, Any],
    family_id: str,
    family_title: str,
    back_matter: dict[str, Any],
) -> dict[str, Any]:
    """Convert a single OSCAL control to unified format."""
    oscal_id = control.get("id", "")
    sort_id = extract_sort_id(control)
    status = extract_status(control)
    impl_level = extract_implementation_level(control)

    parts_data = extract_control_parts(control)

    params = control.get("params", [])
    parameters = extract_parameters(params) if params else []

    links = control.get("links", [])
    references = extract_references(links, back_matter) if links else []

    enhancements = []
    for nested in control.get("controls", []):
        nested_class = nested.get("class", "")
        if "enhancement" in nested_class.lower():
            enhancements.append(convert_enhancement(nested))

    unified: dict[str, Any] = {
        "id": sort_id or oscal_id,
        "oscal_id": oscal_id,
        "title": control.get("title", ""),
        "status": status,
        "implementation_level": impl_level,
        "family": family_title,
        "family_id": family_id,
        "statement": parts_data["statement"],
        "statement_parts": parts_data["statement_parts"],
        "guidance": parts_data["guidance"],
        "assessment": parts_data["assessment"],
        "parameters": parameters,
        "enhancements": enhancements,
        "references": references,
        "related_controls": [],
        "ai_context": {},
    }

    unified["_oscal"] = {
        "class": control.get("class", ""),
        "props": control.get("props", []),
        "links": control.get("links", []),
        "parts": control.get("parts", []),
    }

    return unified


def convert_group(group: dict[str, Any], back_matter: dict[str, Any]) -> dict[str, Any]:
    """Convert an OSCAL group to a unified family."""
    group_id = group.get("id", "")
    title = group.get("title", "")

    sort_id = ""
    for prop in group.get("props", []):
        if prop.get("name") == "sort-id":
            sort_id = prop.get("value", "")
            break

    family_id = title.lower().replace(" ", "-").replace("(", "").replace(")", "")

    unified_family: dict[str, Any] = {
        "id": family_id,
        "oscal_id": group_id,
        "title": title,
        "sort_id": sort_id,
        "controls": [],
    }

    for control in group.get("controls", []):
        unified_control = convert_control(control, family_id, title, back_matter)
        unified_family["controls"].append(unified_control)

    unified_family["_oscal"] = {
        "class": group.get("class", ""),
        "props": group.get("props", []),
    }

    return unified_family


def convert(catalog_data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Convert an OSCAL catalog to unified format.

    Accepts either an OSCAL catalog wrapper (`{"catalog": {...}}`) or a raw
    catalog dict.
    """
    catalog = catalog_data.get("catalog", catalog_data)

    metadata = catalog.get("metadata", {})
    back_matter = catalog.get("back-matter", {})

    unified: dict[str, Any] = {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "oscal",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("title", ""),
            "description": "",
            "publisher": "",
            "version": metadata.get("version", ""),
            "oscal_version": metadata.get("oscal-version", ""),
            "published": metadata.get("published", ""),
            "last_modified": metadata.get("last-modified", ""),
        },
        "families": [],
    }

    for party in metadata.get("parties", []):
        if party.get("type") == "organization":
            unified["metadata"]["publisher"] = party.get("short-name", party.get("name", ""))
            break

    for group in catalog.get("groups", []):
        unified_family = convert_group(group, back_matter)
        unified["families"].append(unified_family)

    if back_matter:
        unified["back_matter"] = back_matter

    unified["_oscal"] = {
        "uuid": catalog.get("uuid", ""),
        "metadata": metadata,
    }

    return unified


__all__ = ["convert", "is_oscal_format"]
