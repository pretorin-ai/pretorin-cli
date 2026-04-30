"""Custom (non-OSCAL) catalog → unified.json converter.

Ported verbatim from monorepo `data/tools/custom_to_unified.py`. Drops the
path-walking entrypoints; keeps the format detector and all 12
per-format converters as pure functions.

Public surface:
    detect_custom_format(data) -> str | None
    is_oscal_format(data) -> bool
    convert(data, framework_id) -> dict   # raises UnknownCustomFormatError
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any


class UnknownCustomFormatError(ValueError):
    """Raised when the input shape doesn't match any known custom format."""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def map_safeguard_type_to_impl_level(safeguard_type: str | None) -> str | None:
    """Map custom safeguard_type values to unified implementation_level.

    Used for frameworks like HIPAA that have safeguard categorization.
    """
    if not safeguard_type:
        return None

    safeguard_type = safeguard_type.lower()

    if safeguard_type in ("administrative", "organizational", "documentation", "privacy", "breach notification"):
        return "organization"

    if safeguard_type in ("technical",):
        return "system"

    if safeguard_type in ("physical",):
        return "hybrid"

    return None


def is_oscal_format(data: dict[str, Any]) -> bool:
    """Check if a catalog is in OSCAL format."""
    if "catalog" in data:
        inner = data["catalog"]
        return isinstance(inner, dict) and "uuid" in inner and "groups" in inner
    return "uuid" in data and "groups" in data


def detect_custom_format(data: dict[str, Any]) -> str | None:
    """Detect the specific custom format pattern. Returns format key or None."""
    if "process_requirement_catalog" in data:
        return "process_requirement"

    if "governance_requirement_catalog" in data:
        return "governance_requirement"

    if "framework_catalog" in data:
        return "framework_catalog"

    if "cryptographic_module_validation_catalog" in data:
        return "crypto_validation"

    if "framework" in data and "metadata" in data.get("framework", {}):
        return "framework_wrapper"

    if "catalog_metadata" in data and "domains" in data:
        return "domains"

    if "standards" in data:
        return "standards_specs"

    if "metadata" in data and "controls" in data:
        first_control = data.get("controls", [{}])[0]
        if "safeguards" in first_control:
            return "cis_safeguards"
        return "metadata_controls"

    if "control_themes" in data and "controls" in data:
        return "control_themes"

    if "control_objectives" in data and "requirements" in data:
        return "pci_dss"

    if "control_families" in data and "controls" in data:
        return "control_families"

    return None


# =============================================================================
# FORMAT-SPECIFIC CONVERTERS
# =============================================================================


def convert_control_families_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Standard control_families + controls. Used by GDPR, HIPAA, SOC2."""
    families_lookup: dict[str, dict[str, Any]] = {}
    for fam in data.get("control_families", []):
        fam_id = fam.get("family_id", "")
        families_lookup[fam_id] = {
            "id": fam_id,
            "title": fam.get("family_name", ""),
            "description": fam.get("description", ""),
            "controls": [],
        }

    for ctrl in data.get("controls", []):
        family_id = ctrl.get("family_id", "unknown")
        if family_id not in families_lookup:
            families_lookup[family_id] = {
                "id": family_id,
                "title": family_id,
                "description": "",
                "controls": [],
            }

        references = []
        if "citation" in ctrl:
            references.append({"title": ctrl["citation"]})
        elif "article_reference" in ctrl:
            references.append({"title": ctrl["article_reference"]})

        custom_meta = {}
        for key in [
            "safeguard_type",
            "required_or_addressable",
            "obligation_type",
            "chapter",
            "trust_service_category",
        ]:
            if key in ctrl:
                custom_meta[key] = ctrl[key]

        unified_ctrl = {
            "id": ctrl.get("control_id", ""),
            "title": ctrl.get("control_name", ""),
            "status": "active",
            "implementation_level": map_safeguard_type_to_impl_level(ctrl.get("safeguard_type")),
            "family": families_lookup[family_id]["title"],
            "family_id": family_id,
            "statement": ctrl.get("control_intent", ctrl.get("description", "")),
            "statement_parts": [],
            "guidance": ctrl.get("guidance", ""),
            "assessment": {"objectives": [], "methods": []},
            "parameters": [],
            "enhancements": [],
            "references": references,
            "related_controls": [],
            "ai_context": {},
            "_custom": custom_meta,
        }

        families_lookup[family_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "control_families",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": data.get("catalog_name", data.get("framework_name", framework_id)),
            "description": data.get("description", ""),
            "publisher": data.get("regulatory_authority", ""),
            "version": data.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_cis_safeguards_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """CIS format with nested safeguards. Each control becomes a family."""
    metadata = data.get("metadata", {})

    families_lookup: dict[str, dict[str, Any]] = {}
    for fam in data.get("control_families", []):
        fam_id = fam.get("id", "")
        families_lookup[fam_id] = {
            "id": fam_id,
            "title": fam.get("name", ""),
            "description": fam.get("description", ""),
            "controls": [],
        }

    for ctrl in data.get("controls", []):
        ctrl_id = str(ctrl.get("control_id", ""))
        family_id = f"control-{ctrl_id}"
        families_lookup[family_id] = {
            "id": family_id,
            "title": ctrl.get("control_name", ""),
            "description": ctrl.get("description", ""),
            "sort_id": ctrl_id,
            "controls": [],
        }

        for sg in ctrl.get("safeguards", []):
            custom_meta = {}
            for key in ["implementation_groups", "asset_type", "security_function", "frequency"]:
                if key in sg:
                    custom_meta[key] = sg[key]

            unified_ctrl = {
                "id": sg.get("safeguard_id", ""),
                "title": sg.get("safeguard_name", ""),
                "status": "active",
                "implementation_level": "system",
                "family": ctrl.get("control_name", ""),
                "family_id": family_id,
                "statement": sg.get("description", ""),
                "statement_parts": [],
                "guidance": sg.get("control_intent", ""),
                "assessment": {"objectives": [], "methods": []},
                "parameters": [],
                "enhancements": [],
                "references": [],
                "related_controls": [],
                "ai_context": {},
                "_custom": custom_meta,
            }
            families_lookup[family_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "cis_safeguards",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("framework_name", framework_id),
            "description": "",
            "publisher": "Center for Internet Security",
            "version": metadata.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_domains_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """CSA-CCM domain-based format."""
    catalog_meta = data.get("catalog_metadata", {})

    families_lookup: dict[str, dict[str, Any]] = {}
    for dom in data.get("domains", []):
        dom_id = dom.get("domain_id", "")
        families_lookup[dom_id] = {
            "id": dom_id,
            "title": dom.get("domain_name", ""),
            "description": "",
            "controls": [],
        }

    for ctrl in data.get("controls", []):
        domain_id = ctrl.get("domain", "unknown")
        if domain_id not in families_lookup:
            families_lookup[domain_id] = {
                "id": domain_id,
                "title": domain_id,
                "description": "",
                "controls": [],
            }

        custom_meta = {}
        for key in ["cloud_applicability", "shared_responsibility"]:
            if key in ctrl:
                custom_meta[key] = ctrl[key]

        unified_ctrl = {
            "id": ctrl.get("control_id", ""),
            "title": ctrl.get("control_name", ""),
            "status": "active",
            "implementation_level": None,
            "family": families_lookup[domain_id]["title"],
            "family_id": domain_id,
            "statement": ctrl.get("description", ""),
            "statement_parts": [],
            "guidance": "",
            "assessment": {"objectives": [], "methods": []},
            "parameters": [],
            "enhancements": [],
            "references": [],
            "related_controls": [],
            "ai_context": {},
            "_custom": custom_meta,
        }

        families_lookup[domain_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "domains",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": catalog_meta.get("framework_name", framework_id),
            "description": "",
            "publisher": "Cloud Security Alliance",
            "version": catalog_meta.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_control_themes_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """ISO-27001 control_themes format."""
    families_lookup: dict[str, dict[str, Any]] = {}
    for theme in data.get("control_themes", []):
        theme_id = theme.get("theme_id", "")
        families_lookup[theme_id] = {
            "id": theme_id,
            "title": theme.get("theme_name", ""),
            "description": "",
            "sort_id": theme.get("identifier_prefix", ""),
            "controls": [],
        }

    theme_name_to_id = {t.get("theme_name", "").lower(): t.get("theme_id", "") for t in data.get("control_themes", [])}

    for ctrl in data.get("controls", []):
        theme_name = ctrl.get("control_theme", "").lower()
        theme_id = theme_name_to_id.get(theme_name, theme_name)

        if theme_id not in families_lookup:
            families_lookup[theme_id] = {
                "id": theme_id,
                "title": ctrl.get("control_theme", ""),
                "description": "",
                "controls": [],
            }

        custom_meta = {}
        if "applicability_guidance" in ctrl:
            custom_meta["applicability_guidance"] = ctrl["applicability_guidance"]
            custom_meta["is_new_2022"] = ctrl.get("is_new_2022", False)

        unified_ctrl = {
            "id": ctrl.get("control_id", ""),
            "title": ctrl.get("control_name", ""),
            "status": "active",
            "implementation_level": None,
            "family": ctrl.get("control_theme", ""),
            "family_id": theme_id,
            "statement": ctrl.get("control_intent", ""),
            "statement_parts": [],
            "guidance": "",
            "assessment": {"objectives": [], "methods": []},
            "parameters": [],
            "enhancements": [],
            "references": [],
            "related_controls": [],
            "ai_context": {},
            "_custom": custom_meta,
        }

        families_lookup[theme_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "control_themes",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": data.get("catalog_name", framework_id),
            "description": "",
            "publisher": "ISO/IEC",
            "version": data.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_pci_dss_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """PCI-DSS with control_objectives, requirements, and controls."""
    families_lookup: dict[str, dict[str, Any]] = {}
    for req in data.get("requirements", []):
        req_num = str(req.get("requirement_number", ""))
        families_lookup[req_num] = {
            "id": f"req-{req_num}",
            "title": req.get("requirement_title", ""),
            "description": "",
            "sort_id": req_num,
            "controls": [],
        }

    for ctrl in data.get("controls", []):
        ctrl_id = str(ctrl.get("control_id", ""))
        req_num = ctrl_id.split(".")[0] if "." in ctrl_id else ctrl_id

        if req_num not in families_lookup:
            families_lookup[req_num] = {
                "id": f"req-{req_num}",
                "title": f"Requirement {req_num}",
                "description": "",
                "controls": [],
            }

        custom_meta = {}
        for key in ["applicability", "defined_approach_requirements", "customized_approach_objective"]:
            if key in ctrl:
                custom_meta[key] = ctrl[key]

        unified_ctrl = {
            "id": ctrl_id,
            "title": ctrl.get("control_name", ""),
            "status": "active",
            "implementation_level": None,
            "family": families_lookup[req_num]["title"],
            "family_id": f"req-{req_num}",
            "statement": ctrl.get("control_intent", ctrl.get("testing_requirement", "")),
            "statement_parts": [],
            "guidance": ctrl.get("testing_guidance", ""),
            "assessment": {"objectives": [], "methods": []},
            "parameters": [],
            "enhancements": [],
            "references": [],
            "related_controls": [],
            "ai_context": {},
            "_custom": custom_meta,
        }

        families_lookup[req_num]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "pci_dss",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": data.get("catalog_name", framework_id),
            "description": data.get("description", ""),
            "publisher": "PCI Security Standards Council",
            "version": data.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_process_requirement_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Process requirement catalog. Used by DoDI 8510.01, FISMA+RMF, ICD-503."""
    catalog = data.get("process_requirement_catalog", {})
    metadata = catalog.get("metadata", {})

    families_lookup: dict[str, dict[str, Any]] = {}

    for req in catalog.get("requirements", []):
        rmf_step = req.get("rmf_step", "General")
        family_id = rmf_step.lower().replace(" ", "-").replace("/", "-")

        if family_id not in families_lookup:
            families_lookup[family_id] = {
                "id": family_id,
                "title": rmf_step,
                "description": "",
                "controls": [],
            }

        custom_meta = {
            "requirement_type": req.get("requirement_type", "process"),
            "normative_keyword": req.get("normative_keyword", ""),
            "dod_specific": req.get("dod_specific", False),
        }
        if "source_reference" in req:
            custom_meta["source_reference"] = req["source_reference"]
        if "related_roles" in req:
            custom_meta["related_roles"] = req["related_roles"]

        unified_ctrl = {
            "id": req.get("requirement_id", ""),
            "title": req.get("title", ""),
            "status": "active",
            "implementation_level": "organization",
            "family": rmf_step,
            "family_id": family_id,
            "statement": req.get("requirement_text", ""),
            "statement_parts": [],
            "guidance": "",
            "assessment": {"objectives": [], "methods": []},
            "parameters": [],
            "enhancements": [],
            "references": [],
            "related_controls": [],
            "ai_context": {},
            "_custom": custom_meta,
        }
        families_lookup[family_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "process_requirement",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("title", framework_id),
            "description": metadata.get("description", ""),
            "publisher": metadata.get("governs_control_catalog", ""),
            "version": metadata.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_governance_requirement_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Governance requirement catalog. Used by NIST AI RMF."""
    catalog = data.get("governance_requirement_catalog", {})
    metadata = catalog.get("metadata", {})

    families_lookup: dict[str, dict[str, Any]] = {}
    for func in catalog.get("ai_rmf_functions", []):
        func_id = func.get("function_id", "")
        families_lookup[func_id] = {
            "id": func_id.lower(),
            "title": func.get("function_name", ""),
            "description": func.get("function_description", ""),
            "controls": [],
        }

    for req in catalog.get("requirements", catalog.get("subcategories", [])):
        req_id = req.get("subcategory_id", req.get("requirement_id", ""))
        func_id = req_id.split("-")[0].upper() if "-" in req_id else "GOVERN"

        func_mapping = {"GV": "GOVERN", "MP": "MAP", "MS": "MEASURE", "MG": "MANAGE"}
        func_id = func_mapping.get(func_id, func_id)

        if func_id not in families_lookup:
            families_lookup[func_id] = {
                "id": func_id.lower(),
                "title": func_id,
                "description": "",
                "controls": [],
            }

        custom_meta = {}
        for key in ["trustworthiness_characteristics", "gai_actions", "suggested_actions"]:
            if key in req:
                custom_meta[key] = req[key]

        unified_ctrl = {
            "id": req_id,
            "title": req.get("subcategory_name", req.get("title", "")),
            "status": "active",
            "implementation_level": "organization",
            "family": families_lookup[func_id]["title"],
            "family_id": func_id.lower(),
            "statement": req.get("description", req.get("requirement_text", "")),
            "statement_parts": [],
            "guidance": "",
            "assessment": {"objectives": [], "methods": []},
            "parameters": [],
            "enhancements": [],
            "references": [],
            "related_controls": [],
            "ai_context": {},
            "_custom": custom_meta,
        }

        families_lookup[func_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "governance_requirement",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("title", framework_id),
            "description": metadata.get("description", ""),
            "publisher": "NIST",
            "version": metadata.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_framework_catalog_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """framework_catalog format (MITRE ATLAS — threat catalog with separate file refs)."""
    catalog = data.get("framework_catalog", {})
    metadata = catalog.get("metadata", {})

    unified: dict[str, Any] = {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "framework_catalog",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("title", framework_id),
            "description": catalog.get("catalog_type_justification", {}).get("statement", ""),
            "publisher": "MITRE",
            "version": metadata.get("version", ""),
        },
        "families": [],
        "_note": "This is a threat catalog. See tactics.json, techniques.json, and mitigations.json for full content.",
    }

    if "normalized_files" in catalog:
        unified["_normalized_files"] = catalog["normalized_files"]["files"]

    return unified


def convert_crypto_validation_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Cryptographic module validation catalog (FIPS 140-3)."""
    catalog = data.get("cryptographic_module_validation_catalog", {})
    metadata = catalog.get("metadata", {})

    families_lookup: dict[str, dict[str, Any]] = {}

    for area in catalog.get("security_areas", []):
        area_id = area.get("area_id", "")
        families_lookup[area_id] = {
            "id": area_id.lower(),
            "title": area.get("area_name", ""),
            "description": area.get("description", ""),
            "controls": [],
        }

        for req in area.get("requirements", []):
            unified_ctrl = {
                "id": req.get("requirement_id", ""),
                "title": req.get("title", ""),
                "status": "active",
                "implementation_level": "system",
                "family": area.get("area_name", ""),
                "family_id": area_id.lower(),
                "statement": req.get("description", ""),
                "statement_parts": [],
                "guidance": "",
                "assessment": {"objectives": [], "methods": []},
                "parameters": [],
                "enhancements": [],
                "references": [],
                "related_controls": [],
                "ai_context": {},
                "_custom": {},
            }
            families_lookup[area_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "crypto_validation",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("framework_name", framework_id),
            "description": metadata.get("scope", {}).get("description", ""),
            "publisher": "NIST",
            "version": metadata.get("fips_publication", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_framework_wrapper_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """framework wrapper format (DISA STIGs — references external STIG files)."""
    framework = data.get("framework", {})
    metadata = framework.get("metadata", {})

    unified: dict[str, Any] = {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "framework_wrapper",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("framework_name", framework_id),
            "description": metadata.get("scope", {}).get("description", ""),
            "publisher": metadata.get("authority", {}).get("name", "DISA"),
            "version": metadata.get("version", ""),
        },
        "families": [],
        "_note": "This is a technical hardening framework. See stig_packages/ for specific STIG content.",
    }

    if "checklist_concepts" in data:
        unified["_checklist_concepts"] = data["checklist_concepts"]

    return unified


def convert_standards_specs_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Standards with implementation_specifications. Used by HIPAA-NIST-800-66."""
    families_lookup: dict[str, dict[str, Any]] = {}

    for std in data.get("standards", []):
        category = std.get("safeguard_category", "General")
        family_id = category.lower().replace(" ", "-")

        if family_id not in families_lookup:
            families_lookup[family_id] = {
                "id": family_id,
                "title": f"{category} Safeguards",
                "description": "",
                "controls": [],
            }

        specs = std.get("implementation_specifications", [])

        if specs:
            for spec in specs:
                related_controls = []
                if "nist_800_53_refs" in spec:
                    related_controls = [{"id": r, "framework": "nist-800-53"} for r in spec.get("nist_800_53_refs", [])]

                custom_meta: dict[str, Any] = {
                    "cfr_reference": spec.get("cfr_reference", ""),
                    "requirement_type": spec.get("requirement_type", ""),
                    "parent_standard": std.get("standard_id", ""),
                }
                if "nist_csf_refs" in spec:
                    custom_meta["nist_csf_refs"] = spec["nist_csf_refs"]

                unified_ctrl = {
                    "id": spec.get("spec_id", ""),
                    "title": spec.get("name", ""),
                    "status": "active",
                    "implementation_level": map_safeguard_type_to_impl_level(category),
                    "family": f"{category} Safeguards",
                    "family_id": family_id,
                    "statement": spec.get("description", ""),
                    "statement_parts": [],
                    "guidance": "",
                    "assessment": {"objectives": [], "methods": []},
                    "parameters": [],
                    "enhancements": [],
                    "references": [],
                    "related_controls": related_controls,
                    "ai_context": {},
                    "_custom": custom_meta,
                }

                families_lookup[family_id]["controls"].append(unified_ctrl)
        else:
            related_controls = []
            if "nist_800_53_refs" in std:
                related_controls = [{"id": r, "framework": "nist-800-53"} for r in std["nist_800_53_refs"]]

            unified_ctrl = {
                "id": std.get("standard_id", ""),
                "title": std.get("standard_name", ""),
                "status": "active",
                "implementation_level": map_safeguard_type_to_impl_level(category),
                "family": f"{category} Safeguards",
                "family_id": family_id,
                "statement": std.get("description", ""),
                "statement_parts": [],
                "guidance": "",
                "assessment": {"objectives": [], "methods": []},
                "parameters": [],
                "enhancements": [],
                "references": [],
                "related_controls": related_controls,
                "ai_context": {},
                "_custom": {
                    "cfr_reference": std.get("cfr_reference", ""),
                    "requirement_type": std.get("requirement_type", ""),
                },
            }
            families_lookup[family_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "standards_specs",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": data.get("catalog_name", framework_id),
            "description": data.get("description", ""),
            "publisher": data.get("regulatory_authority", ""),
            "version": data.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


def convert_metadata_controls_format(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Generic metadata + controls format without nested safeguards."""
    metadata = data.get("metadata", {})

    families_lookup: dict[str, dict[str, Any]] = {}
    for fam in data.get("control_families", []):
        fam_id = fam.get("id", fam.get("family_id", ""))
        families_lookup[fam_id] = {
            "id": fam_id,
            "title": fam.get("name", fam.get("family_name", "")),
            "description": fam.get("description", ""),
            "controls": [],
        }

    if not families_lookup:
        families_lookup["general"] = {
            "id": "general",
            "title": "General Controls",
            "description": "",
            "controls": [],
        }

    for ctrl in data.get("controls", []):
        family_id = ctrl.get("family_id", ctrl.get("control_family", "general"))
        if family_id not in families_lookup:
            families_lookup[family_id] = {
                "id": family_id,
                "title": family_id,
                "description": "",
                "controls": [],
            }

        unified_ctrl = {
            "id": ctrl.get("control_id", ""),
            "title": ctrl.get("control_name", ""),
            "status": "active",
            "implementation_level": None,
            "family": families_lookup[family_id]["title"],
            "family_id": family_id,
            "statement": ctrl.get("description", ctrl.get("control_intent", "")),
            "statement_parts": [],
            "guidance": "",
            "assessment": {"objectives": [], "methods": []},
            "parameters": [],
            "enhancements": [],
            "references": [],
            "related_controls": [],
            "ai_context": {},
            "_custom": {},
        }

        families_lookup[family_id]["controls"].append(unified_ctrl)

    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "custom_format_type": "metadata_controls",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": metadata.get("framework_name", framework_id),
            "description": "",
            "publisher": "",
            "version": metadata.get("version", ""),
        },
        "families": list(families_lookup.values()),
    }


CONVERTERS: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
    "control_families": convert_control_families_format,
    "cis_safeguards": convert_cis_safeguards_format,
    "domains": convert_domains_format,
    "control_themes": convert_control_themes_format,
    "pci_dss": convert_pci_dss_format,
    "process_requirement": convert_process_requirement_format,
    "governance_requirement": convert_governance_requirement_format,
    "framework_catalog": convert_framework_catalog_format,
    "crypto_validation": convert_crypto_validation_format,
    "framework_wrapper": convert_framework_wrapper_format,
    "metadata_controls": convert_metadata_controls_format,
    "standards_specs": convert_standards_specs_format,
}


def convert(data: dict[str, Any], framework_id: str) -> dict[str, Any]:
    """Convert a custom (non-OSCAL) catalog dict to unified.json format.

    Raises UnknownCustomFormatError if the input shape isn't recognized.
    """
    if is_oscal_format(data):
        raise UnknownCustomFormatError("Input is OSCAL format; use pretorin.frameworks.oscal_to_unified instead.")

    format_type = detect_custom_format(data)
    if format_type is None:
        raise UnknownCustomFormatError(
            "Unrecognized custom catalog shape. Supported shapes: " + ", ".join(sorted(CONVERTERS.keys()))
        )

    converter = CONVERTERS[format_type]
    return converter(data, framework_id)


__all__ = [
    "CONVERTERS",
    "UnknownCustomFormatError",
    "convert",
    "detect_custom_format",
    "is_oscal_format",
    "map_safeguard_type_to_impl_level",
]
