# tests/test_simulation.py

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

# Adjust path to import source code
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# We ignore E402 (import not at top) and E501 (line too long) due to path hack
from sanskrit_heritage.segmenter.interface import HeritageSegmenter  # noqa: E402, E501
from sanskrit_heritage import config  # noqa: E402, F401

# --- CONSTANTS & MOCK DATA ---
# Realistic Sanskrit input: "Rama goes"
TEST_INPUT_WX = "rAmogacCawi"
TEST_INPUT_DN = "रामोगच्छति"

SYSTEM_PATH = Path("/usr/lib/cgi-bin/SKT/interface2.cgi")
BUNDLED_PATH = config.PACKAGE_DIR / "assets" / "bin" / "linux" / "interface2"
CUSTOM_PATH = Path("/custom/location/interface2")

MOCK_JSON_SUCCESS = '{"segmentation": ["rAmaH gacCawi"]}'
MOCK_JSON_UNRECOGNIZED = (
    '{"segmentation": ["?rAma"], '
    '"morph": [{"word": "?rAma", "inflectional_morphs": ["?"]}]}'
)
MOCK_GARBAGE = "Fatal Error: OCaml Segfault"


class TestSerialization:
    """Tests the static serialize_result method."""

    def test_serialize_text_mode(self):
        # List input -> Raw string
        data = ["rAmaH gacCawi"]
        res = HeritageSegmenter.serialize_result(data, "text")
        assert res == "rAmaH gacCawi"

        # Empty list -> Empty string
        res = HeritageSegmenter.serialize_result([], "text")
        assert res == ""

    def test_serialize_list_mode(self):
        # List input -> JSON Array string
        data = ["rAmaH gacCawi"]
        res = HeritageSegmenter.serialize_result(data, "list")
        assert res == '["rAmaH gacCawi"]'

    def test_serialize_json_mode_indent(self):
        # Dict input -> JSON string with indent
        data = {"status": "Success"}
        res = HeritageSegmenter.serialize_result(data, "json", indent=2)
        assert "{\n  \"status\"" in res  # Checks for newline and spaces

    def test_serialize_json_mode_compact(self):
        # Dict input -> Compact JSON string
        data = {"status": "Success"}
        res = HeritageSegmenter.serialize_result(data, "json", indent=None)
        assert res == '{"status": "Success"}'


class TestFacadeAPI:
    """Tests the user-friendly wrappers (segment, analyze)."""

    def setup_method(self):
        with patch(
            "sanskrit_heritage.config.resolve_binary_path",
            return_value=None
        ):
            self.segmenter = HeritageSegmenter()

    def test_segment_wrapper(self):
        """Verify segment() calls process_text with strict defaults."""
        with patch.object(self.segmenter, 'process_text') as mock_process:
            mock_process.return_value = ["res"]

            res = self.segmenter.segment("test")

            assert res == ["res"]
            mock_process.assert_called_once_with(
                "test", process_mode="seg", output_format="list"
            )

    def test_analyze_word_wrapper(self):
        """
        Verify analyze_word() forces text_type='word' and restores it.
        """
        # 1. Start in 'sent' mode (default)
        self.segmenter.text_type = "sent"

        with patch.object(self.segmenter, 'process_text') as mock_process:
            expected_return = {"morph": ["dummy_data"]}
            mock_process.return_value = expected_return

            # 2. Call the method
            res = self.segmenter.analyze_word("testword")

            # 3. Verify arguments passed to process_text
            # It should have received text_type="word" (via state change)
            # BUT since we mock process_text, we check the side effect or
            # simply check the flow.
            assert res == expected_return

            # Let's verify the call arguments
            mock_process.assert_called_once_with(
                "testword",
                process_mode="morph",
                output_format="json"
            )

        # 4. CRITICAL: Verify state was restored to 'sent'
        assert self.segmenter.text_type == "sent"

    def test_analyze_wrapper(self):
        """Verify analyze() calls process_text with strict defaults."""
        with patch.object(self.segmenter, 'process_text') as mock_process:
            mock_process.return_value = {"morph": []}

            res = self.segmenter.analyze("test")

            assert res == {"morph": []}
            mock_process.assert_called_once_with(
                "test", process_mode="seg-morph", output_format="json"
            )


class TestProcessTextLogic:
    """Tests the smart dispatch logic in process_text."""

    def setup_method(self):
        # Mock resolve_binary_path to avoid filesystem checks
        with patch(
            "sanskrit_heritage.config.resolve_binary_path", return_value=None
        ):
            self.segmenter = HeritageSegmenter()

    def test_seg_mode_text_format(self):
        """Action: seg + text -> Result: List[str] (Ready for serialization)
        """
        with patch.object(self.segmenter, '_run_pipeline') as mock_get:
            mock_get.return_value = {
                "status": "Success",
                "segmentation": ["res1"]
            }

            # process_text MUST return the Data (List),
            # not the serialized string
            result = self.segmenter.process_text(
                "input", process_mode="seg", output_format="text"
            )

            assert isinstance(result, list)
            assert result == ["res1"]

    def test_seg_mode_list_format(self):
        """Action: seg + list -> Result: List[str]"""
        # Mock get_segmentation to return a full dict
        with patch.object(self.segmenter, '_run_pipeline') as mock_get:
            mock_get.return_value = {
                "status": "Success",
                "segmentation": ["res1"]
            }

            result = self.segmenter.process_text(
                "input", process_mode="seg", output_format="list"
            )

            assert isinstance(result, list)
            assert result == ["res1"]
            mock_get.assert_called_once()

    def test_seg_mode_json_format(self):
        """Action: seg + json -> Result: Dict"""
        with patch.object(self.segmenter, '_run_pipeline') as mock_get:
            mock_get.return_value = {
                "status": "Success", "segmentation": ["res1"]
            }

            result = self.segmenter.process_text(
                "input", process_mode="seg", output_format="json"
            )

            assert isinstance(result, dict)
            assert result["segmentation"] == ["res1"]

    def test_morph_mode_forces_json_with_warning(self):
        """Action: morph + list -> Warning + Result: Dict"""
        with patch.object(
            self.segmenter, '_run_pipeline'
        ) as mock_get:
            mock_get.return_value = {
                "status": "Success", "morph": []
            }

            # We expect a warning log
            with patch(
                "sanskrit_heritage.segmenter.interface.logger.warning"
            ) as mock_log:
                result = self.segmenter.process_text(
                    "input", process_mode="morph", output_format="list"
                )

                # Should force return dict despite asking for list
                assert isinstance(result, dict)
                # Verify warning was logged
                mock_log.assert_called_once()
                assert "incompatible" in mock_log.call_args[0][0]

    def test_failure_handling_in_list_mode(self):
        """Action: seg fails -> Result: Empty List"""
        with patch.object(self.segmenter, '_run_pipeline') as mock_get:
            mock_get.return_value = {
                "status": "Failure", "error": "Bad Input"
            }

            result = self.segmenter.process_text(
                "bad", process_mode="seg", output_format="list"
            )

            assert result == ["?? bad"]


class TestConfiguration:
    """Tests binary path detection, environment variables, fallback logic."""

    # --- SCENARIO 1: Clean Slate (Updated for Web Fallback) ---
    @patch("sanskrit_heritage.config.resolve_binary_path", return_value=None)
    def test_init_switches_to_web_when_no_binaries_exist(self, mock_resolve):
        """
        Scenario: If no binaries exist, we do NOT raise RuntimeError.
        We switch to Web Fallback mode.
        """
        segmenter = HeritageSegmenter()
        assert segmenter.use_web_fallback is True
        assert segmenter.execution_cwd is None

    # --- SCENARIO 2: System Install Only ---
    def test_prefer_system_install_if_bundled_missing(self):
        """
        Scenario: Bundled missing, System exists.
        Should pick System path.
        """
        def side_effect(path):
            if path is None:
                return None
            # Only System Path exists
            if str(path) == str(SYSTEM_PATH):
                return True
            return False

        with patch(
            "pathlib.Path.exists", side_effect=side_effect, autospec=True
        ):
            with patch("platform.system", return_value="Linux"):
                segmenter = HeritageSegmenter()
                assert segmenter.cgi_path == SYSTEM_PATH
                assert segmenter.use_web_fallback is False

    # --- SCENARIO 3: Bundled Binary Priority ---
    def test_fallback_to_bundled_if_system_missing(self):
        """
        Scenario: System missing, Bundled exists.
        Should pick Bundled path.
        """
        def side_effect(path):
            if path is None:
                return None
            # Only Bundled Path exists
            if str(path) == str(BUNDLED_PATH):
                return True
            return False

        with patch(
            "pathlib.Path.exists", side_effect=side_effect, autospec=True
        ):
            with patch("platform.system", return_value="Linux"):
                segmenter = HeritageSegmenter()
                assert segmenter.cgi_path == BUNDLED_PATH

    # --- SCENARIO 4: Explicit Overrides ---
    def test_environment_variable_override(self):
        """Scenario: SANSKRIT_HERITAGE_BIN env var overrides everything."""
        env_mock = {"SANSKRIT_HERITAGE_BIN": str(CUSTOM_PATH)}
        with patch.dict(os.environ, env_mock):
            with patch("pathlib.Path.exists", return_value=True):
                segmenter = HeritageSegmenter()
                assert segmenter.cgi_path == CUSTOM_PATH

    def test_constructor_argument_override(self):
        """Scenario: Constructor argument has highest priority."""
        override_path = Path("/tmp/override_bin")
        with patch("pathlib.Path.exists", return_value=True):
            segmenter = HeritageSegmenter(binary_path=override_path)
            assert segmenter.cgi_path == override_path


class TestLogicAndValidation:
    """Tests for property validation (Scenario 5)."""

    def test_invalid_configuration_raises_value_error(self):
        """Test validation logic (Setters)."""
        # Use web fallback mode to avoid path setup overhead
        with patch(
            "sanskrit_heritage.config.resolve_binary_path",
            return_value=None
        ):
            segmenter = HeritageSegmenter()

            with pytest.raises(ValueError, match="Invalid lex"):
                segmenter.lex = "BAD_LEXICON"

            with pytest.raises(ValueError, match="Invalid mode"):
                segmenter.mode = "random_mode"

            with pytest.raises(ValueError, match="Timeout"):
                segmenter.timeout = -5


class TestWebFallback:
    """Tests for the Web Server interaction."""

    @patch("requests.get")
    @patch("sanskrit_heritage.config.resolve_binary_path", return_value=None)
    def test_web_request_success(self, mock_path, mock_get):
        """Verify successful web request."""
        # Use WX for deterministic assertion
        segmenter = HeritageSegmenter(input_encoding="WX")

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_JSON_SUCCESS
        mock_response.text = MOCK_JSON_SUCCESS
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = segmenter.get_segmentation(TEST_INPUT_WX)

        assert result["status"] == "Success"
        assert result["source"] == "SH-Web"

        # Verify arguments: input WX should be passed as-is
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["text"] == TEST_INPUT_WX
        assert kwargs["params"]["font"] == "deva"  # output maps to deva

    @patch("requests.get")
    @patch("sanskrit_heritage.config.resolve_binary_path", return_value=None)
    def test_web_request_timeout(self, mock_path, mock_get):
        """Verify web timeout."""
        segmenter = HeritageSegmenter()
        mock_get.side_effect = requests.Timeout("Network Down")

        result = segmenter.get_segmentation(TEST_INPUT_WX)

        assert result["status"] == "Timeout"
        assert "timeout" in result["error"].lower()


class TestLocalExecution:
    """Tests for subprocess interaction (Scenarios 6 & 7)."""

    @patch("psutil.Process")
    @patch("subprocess.Popen")
    @patch(
        "sanskrit_heritage.config.resolve_binary_path",
        return_value=Path("/bin/true")
    )
    def test_timeout_handling(self, mock_path, mock_popen, mock_psutil):
        """Scenario 6: The binary hangs and exceeds timeout."""
        segmenter = HeritageSegmenter()

        process_mock = MagicMock()
        # We SIMULATE the hang here. We don't need a real long sentence.
        process_mock.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="cmd", timeout=30
        )
        process_mock.pid = 1234
        mock_popen.return_value = process_mock

        result = segmenter.get_segmentation(TEST_INPUT_WX)

        assert result["status"] == "Timeout"
        mock_psutil.assert_called_with(1234)

    @patch("subprocess.Popen")
    @patch(
        "sanskrit_heritage.config.resolve_binary_path",
        return_value=Path("/bin/true")
    )
    def test_corrupt_json_handling(self, mock_path, mock_popen):
        """Scenario 7: Binary returns garbage text."""
        segmenter = HeritageSegmenter()

        process_mock = MagicMock()
        process_mock.communicate.return_value = (
            MOCK_GARBAGE.encode('utf-8'), b""
        )
        process_mock.returncode = 0
        mock_popen.return_value = process_mock

        result = segmenter.get_segmentation(TEST_INPUT_WX)

        assert result["status"] in ["Failure", "Error", "Unknown Anomaly"]

    @patch(
        "sanskrit_heritage.segmenter.interface.HeritageSegmenter._execute_cgi"
    )
    def test_unrecognized_word_handling(self, mock_exec):
        """Scenario 8: Output contains '?' markers."""
        # Force local mode to use _execute_cgi
        with patch(
            "sanskrit_heritage.config.resolve_binary_path",
            return_value=Path("/bin/true")
        ):
            segmenter = HeritageSegmenter()

            mock_exec.return_value = (MOCK_JSON_UNRECOGNIZED, "Success", "")

            # "ka" is simple, but the mock forces it to fail
            result = segmenter.get_morphological_analysis("ka")

            assert result["status"] == "Unrecognized"
            assert "SH could not recognize word" in result["error"]
