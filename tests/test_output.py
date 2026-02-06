"""Unit tests for the JSON output module."""

import json

from pydantic import BaseModel

from pretorin.cli.output import is_json_mode, print_json, set_json_mode


class SampleModel(BaseModel):
    """Test model for print_json."""

    name: str
    value: int


class TestJsonModeFlag:
    """Tests for the JSON mode flag."""

    def teardown_method(self) -> None:
        set_json_mode(False)

    def test_default_is_false(self) -> None:
        set_json_mode(False)
        assert is_json_mode() is False

    def test_set_true(self) -> None:
        set_json_mode(True)
        assert is_json_mode() is True

    def test_set_false(self) -> None:
        set_json_mode(True)
        set_json_mode(False)
        assert is_json_mode() is False


class TestPrintJson:
    """Tests for print_json serialization."""

    def test_dict(self, capsys: object) -> None:
        import _pytest.capture

        capsys_fixture: _pytest.capture.CaptureFixture[str] = capsys  # type: ignore[assignment]
        print_json({"key": "value", "count": 42})
        captured = capsys_fixture.readouterr()
        data = json.loads(captured.out)
        assert data == {"key": "value", "count": 42}

    def test_pydantic_model(self, capsys: object) -> None:
        import _pytest.capture

        capsys_fixture: _pytest.capture.CaptureFixture[str] = capsys  # type: ignore[assignment]
        model = SampleModel(name="test", value=10)
        print_json(model)
        captured = capsys_fixture.readouterr()
        data = json.loads(captured.out)
        assert data == {"name": "test", "value": 10}

    def test_list_of_models(self, capsys: object) -> None:
        import _pytest.capture

        capsys_fixture: _pytest.capture.CaptureFixture[str] = capsys  # type: ignore[assignment]
        models = [SampleModel(name="a", value=1), SampleModel(name="b", value=2)]
        print_json(models)
        captured = capsys_fixture.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 2
        assert data[0]["name"] == "a"
        assert data[1]["value"] == 2

    def test_list_of_dicts(self, capsys: object) -> None:
        import _pytest.capture

        capsys_fixture: _pytest.capture.CaptureFixture[str] = capsys  # type: ignore[assignment]
        print_json([{"x": 1}, {"x": 2}])
        captured = capsys_fixture.readouterr()
        data = json.loads(captured.out)
        assert data == [{"x": 1}, {"x": 2}]

    def test_dict_with_model_values(self, capsys: object) -> None:
        import _pytest.capture

        capsys_fixture: _pytest.capture.CaptureFixture[str] = capsys  # type: ignore[assignment]
        print_json({"item": SampleModel(name="nested", value=99)})
        captured = capsys_fixture.readouterr()
        data = json.loads(captured.out)
        assert data["item"] == {"name": "nested", "value": 99}

    def test_output_is_valid_json(self, capsys: object) -> None:
        import _pytest.capture

        capsys_fixture: _pytest.capture.CaptureFixture[str] = capsys  # type: ignore[assignment]
        print_json({"nested": {"a": [1, 2, 3]}})
        captured = capsys_fixture.readouterr()
        # Should not raise
        json.loads(captured.out)
