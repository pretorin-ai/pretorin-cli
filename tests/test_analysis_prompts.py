"""Tests for analysis prompts and templates."""


from pretorin.mcp.analysis_prompts import (
    CONTROL_ANALYSIS_PROMPTS,
    FRAMEWORK_GUIDES,
    format_control_analysis_prompt,
    get_artifact_schema,
    get_available_controls,
    get_control_prompt,
    get_control_summary,
    get_framework_guide,
)


class TestGetArtifactSchema:
    """Tests for get_artifact_schema function."""

    def test_returns_string(self):
        """Test that schema is returned as string."""
        schema = get_artifact_schema()
        assert isinstance(schema, str)

    def test_contains_required_fields(self):
        """Test that schema documentation contains required fields."""
        schema = get_artifact_schema()
        assert "framework_id" in schema
        assert "control_id" in schema
        assert "component" in schema
        assert "confidence" in schema

    def test_contains_implementation_status_values(self):
        """Test that schema documents valid implementation statuses."""
        schema = get_artifact_schema()
        assert "implemented" in schema
        assert "partial" in schema
        assert "planned" in schema
        assert "not-applicable" in schema


class TestGetFrameworkGuide:
    """Tests for get_framework_guide function."""

    def test_fedramp_moderate_guide(self):
        """Test FedRAMP Moderate guide retrieval."""
        guide = get_framework_guide("fedramp-moderate")
        assert guide is not None
        assert "FedRAMP" in guide
        assert "Moderate" in guide

    def test_nist_800_53_guide(self):
        """Test NIST 800-53 guide retrieval."""
        guide = get_framework_guide("nist-800-53-r5")
        assert guide is not None
        assert "NIST 800-53" in guide

    def test_nist_800_171_guide(self):
        """Test NIST 800-171 guide retrieval."""
        guide = get_framework_guide("nist-800-171-r3")
        assert guide is not None
        assert "NIST 800-171" in guide

    def test_case_insensitive(self):
        """Test that guide lookup is case insensitive."""
        guide_lower = get_framework_guide("fedramp-moderate")
        guide_upper = get_framework_guide("FEDRAMP-MODERATE")
        assert guide_lower == guide_upper

    def test_unknown_framework_returns_none(self):
        """Test that unknown framework returns None."""
        guide = get_framework_guide("unknown-framework-xyz")
        assert guide is None

    def test_partial_match(self):
        """Test partial framework ID matching."""
        # Should match fedramp-moderate
        guide = get_framework_guide("fedramp")
        assert guide is not None


class TestGetControlPrompt:
    """Tests for get_control_prompt function."""

    def test_ac2_prompt(self):
        """Test AC-2 control prompt retrieval."""
        prompt = get_control_prompt("ac-2")
        assert prompt is not None
        assert prompt["title"] == "Account Management"
        assert prompt["family"] == "Access Control"

    def test_au2_prompt(self):
        """Test AU-2 control prompt retrieval."""
        prompt = get_control_prompt("au-2")
        assert prompt is not None
        assert prompt["title"] == "Audit Events"

    def test_ia2_prompt(self):
        """Test IA-2 control prompt retrieval."""
        prompt = get_control_prompt("ia-2")
        assert prompt is not None
        assert "Authentication" in prompt["title"]

    def test_sc7_prompt(self):
        """Test SC-7 control prompt retrieval."""
        prompt = get_control_prompt("sc-7")
        assert prompt is not None
        assert "Boundary" in prompt["title"]

    def test_cm2_prompt(self):
        """Test CM-2 control prompt retrieval."""
        prompt = get_control_prompt("cm-2")
        assert prompt is not None
        assert "Configuration" in prompt["title"]

    def test_case_insensitive(self):
        """Test that control lookup is case insensitive."""
        prompt_lower = get_control_prompt("ac-2")
        prompt_upper = get_control_prompt("AC-2")
        assert prompt_lower == prompt_upper

    def test_unknown_control_returns_none(self):
        """Test that unknown control returns None."""
        prompt = get_control_prompt("unknown-control-xyz")
        assert prompt is None

    def test_prompt_has_required_sections(self):
        """Test that prompts have all required sections."""
        required_keys = [
            "title",
            "family",
            "summary",
            "what_to_look_for",
            "evidence_examples",
            "implementation_status_guidance",
        ]
        for control_id in get_available_controls():
            prompt = get_control_prompt(control_id)
            for key in required_keys:
                assert key in prompt, f"Missing {key} in {control_id}"


class TestFormatControlAnalysisPrompt:
    """Tests for format_control_analysis_prompt function."""

    def test_known_control_formatting(self):
        """Test formatting for known control."""
        prompt = format_control_analysis_prompt("fedramp-moderate", "ac-2")
        assert "AC-2" in prompt
        assert "Account Management" in prompt
        assert "fedramp-moderate" in prompt
        assert "analysis://schema" in prompt

    def test_unknown_control_fallback(self):
        """Test formatting for unknown control provides generic guidance."""
        prompt = format_control_analysis_prompt("fedramp-moderate", "unknown-99")
        assert "UNKNOWN-99" in prompt
        assert "No specific analysis guidance" in prompt
        assert "analysis://schema" in prompt

    def test_includes_framework_id(self):
        """Test that formatted prompt includes framework ID."""
        prompt = format_control_analysis_prompt("nist-800-53-r5", "au-2")
        assert "nist-800-53-r5" in prompt


class TestGetAvailableControls:
    """Tests for get_available_controls function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        controls = get_available_controls()
        assert isinstance(controls, list)

    def test_contains_core_controls(self):
        """Test that all 5 core controls are available."""
        controls = get_available_controls()
        expected = ["ac-2", "au-2", "ia-2", "sc-7", "cm-2"]
        for control in expected:
            assert control in controls

    def test_count_matches_prompts(self):
        """Test that count matches CONTROL_ANALYSIS_PROMPTS."""
        controls = get_available_controls()
        assert len(controls) == len(CONTROL_ANALYSIS_PROMPTS)


class TestGetControlSummary:
    """Tests for get_control_summary function."""

    def test_ac2_summary(self):
        """Test AC-2 summary."""
        summary = get_control_summary("ac-2")
        assert summary is not None
        assert "Account Management" in summary
        assert "Access Control" in summary

    def test_unknown_control_returns_none(self):
        """Test that unknown control returns None."""
        summary = get_control_summary("unknown-control")
        assert summary is None

    def test_all_controls_have_summaries(self):
        """Test that all available controls have summaries."""
        for control_id in get_available_controls():
            summary = get_control_summary(control_id)
            assert summary is not None, f"Missing summary for {control_id}"


class TestControlPromptContent:
    """Tests for the content quality of control prompts."""

    def test_what_to_look_for_has_file_patterns(self):
        """Test that what_to_look_for includes file patterns."""
        for control_id in get_available_controls():
            prompt = get_control_prompt(control_id)
            what_to_look_for = prompt["what_to_look_for"]
            # Should have file pattern suggestions
            assert "**/" in what_to_look_for or "File Patterns" in what_to_look_for

    def test_what_to_look_for_has_keywords(self):
        """Test that what_to_look_for includes keywords."""
        for control_id in get_available_controls():
            prompt = get_control_prompt(control_id)
            what_to_look_for = prompt["what_to_look_for"]
            # Should mention keywords to search
            assert "keyword" in what_to_look_for.lower() or "search" in what_to_look_for.lower()

    def test_evidence_examples_has_examples(self):
        """Test that evidence examples show actual examples."""
        for control_id in get_available_controls():
            prompt = get_control_prompt(control_id)
            examples = prompt["evidence_examples"]
            # Should have at least one JSON example
            assert "description" in examples.lower()
            assert "{" in examples  # JSON structure


class TestFrameworkGuideContent:
    """Tests for the content quality of framework guides."""

    def test_fedramp_has_control_families(self):
        """Test that FedRAMP guide covers key control families."""
        guide = get_framework_guide("fedramp-moderate")
        families = ["Access Control", "Audit", "Identification", "System"]
        for family in families:
            assert family in guide

    def test_guides_have_analysis_guidance(self):
        """Test that guides include analysis guidance."""
        for framework_id in FRAMEWORK_GUIDES:
            guide = FRAMEWORK_GUIDES[framework_id]
            # Should have analysis-related content
            assert "analysis" in guide.lower() or "control" in guide.lower()
