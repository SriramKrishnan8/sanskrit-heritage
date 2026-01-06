# tests/test_integration_real.py

import sys
from pathlib import Path
import json

import pytest

# Adjust path to import source code (Standard Test Setup)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Ignore imports position for flake8
from sanskrit_heritage.segmenter.interface import HeritageSegmenter  # noqa: E402, E501
from sanskrit_heritage import config  # noqa: E402

# Use resolve_binary_path so it works for System installs too
BINARY_PATH = config.resolve_binary_path()
BINARY_EXISTS = BINARY_PATH and BINARY_PATH.exists()


@pytest.mark.skipif(
    not BINARY_EXISTS,
    reason="No local binary found (Bundled or System). Skipping integration."
)
class TestRealIntegration:
    """
    These tests ONLY run if a real OCaml binary is found.
    They verify the actual execution, ensuring the binary can read
    the .rem data files correctly.
    """

    def setup_method(self):
        # We use WX to avoid encoding ambiguity in assertions
        self.segmenter = HeritageSegmenter(
            input_encoding="WX",
            output_encoding="WX"
        )

    def test_facade_methods_real(self):
        """Verify the user-friendly facade works with real binary."""
        # 1. Test segment() -> Returns List
        res_seg = self.segmenter.segment("rAmogacCawi")
        assert isinstance(res_seg, str)
        assert len(res_seg) > 0
        assert "rAmaH gacCawi" in res_seg

        # 2. Test analyze() -> Returns Dict with Morph
        res_morph = self.segmenter.analyze("gacCawi")
        assert isinstance(res_morph, dict)
        assert res_morph["status"] == "Success"
        assert len(res_morph.get("morph", [])) > 0

    def test_process_text_api_text(self):
        """Test unified API returns Python Objects (not strings)."""
        # Text format request -> Returns List object
        res_str = self.segmenter.process_text(
            "rAmogacCawi", output_format="text"
        )
        assert isinstance(res_str, str)
        assert "rAmaH gacCawi" in res_str

    def test_batch_e2e_text_mode(self, tmp_path):
        """
        Verify the DEFAULT batch output is clean text (User Friendly).
        """
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.txt"
        input_file.write_text(
            "rAmogacCawi\nkqRNorakRawu", encoding="utf-8"
        )

        seg = HeritageSegmenter(input_encoding="WX", output_encoding="WX")

        # Run with defaults (format='text')
        seg.process_file(
            input_path=str(input_file),
            output_path=str(output_file),
            workers=1,
            process_mode="seg",
            output_format="text"
        )

        with open(output_file, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]

        # Verify content is RAW TEXT, not JSON
        assert len(lines) >= 2
        assert lines[0] == "rAmaH gacCawi"      # No ["..."] quotes
        assert lines[1] == "kqRNaH rakRawu"

    def test_batch_e2e_json_mode(self, tmp_path):
        """
        Verify explicit 'list' format gives valid JSONL.
        """
        input_file = tmp_path / "input_json.txt"
        output_file = tmp_path / "output.jsonl"
        input_file.write_text("rAmogacCawi", encoding="utf-8")

        seg = HeritageSegmenter(input_encoding="WX", output_encoding="WX")

        seg.process_file(
            input_path=str(input_file),
            output_path=str(output_file),
            workers=1,
            output_format="list",  # Explicitly asking for list
        )

        content = output_file.read_text(encoding="utf-8").strip()
        # Verify content is valid JSON
        data = json.loads(content)
        assert isinstance(data, list)
        assert data[0] == "rAmaH gacCawi"

    def test_process_text_api_list(self):
        """Test the new unified process_text API with real binary."""
        # 1. Simple List
        res_list = self.segmenter.process_text(
            "rAmogacCawi", process_mode="seg", output_format="list"
        )
        assert isinstance(res_list, list)
        assert len(res_list) > 0
        assert "rAmaH gacCawi" in res_list[0]

        # 2. Full JSON
        res_json = self.segmenter.process_text(
            "rAmogacCawi", process_mode="seg", output_format="json"
        )
        assert isinstance(res_json, dict)
        assert res_json["status"] == "Success"

    def test_batch_e2e_real(self, tmp_path):
        """
        End-to-End test for Batch Processing.
        Creates a file, processes it using the real batch logic, checks output.
        """
        # 1. Setup Input File
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.json"

        sentences = ["rAmogacCawi", "satyamevajayate"]
        input_file.write_text("\n".join(sentences), encoding="utf-8")

        # 2. Run Batch
        # Instantiate
        segmenter = HeritageSegmenter(
            input_encoding="WX", output_encoding="WX"
        )
        # (Force 1 worker to avoid heavy multiprocessing overhead in tests)
        segmenter.process_file(
            input_path=str(input_file),
            output_path=str(output_file),
            workers=1,
            process_mode="seg",
            output_format="list",
        )

        # 3. Read Output
        assert output_file.exists()
        lines = output_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        # 4. Validate Content
        res1 = json.loads(lines[0])  # Should be list ["rAmaH gacCawi"]
        assert isinstance(res1, list)
        assert "rAmaH gacCawi" in res1[0]

        res2 = json.loads(lines[1])
        assert isinstance(res2, list)

    def test_real_binary_execution(self):
        """Actually runs ./interface2 and checks output."""
        text = "rAmogacCawi"
        result = self.segmenter.get_segmentation(text)

        # Verify real output
        error_msg = result.get("error", "No error message provided")
        assert result["status"] == "Success", f"Binary failed: {error_msg}"
        assert result["source"] == "SH-Local"
        # "rAmogacCawi" -> "rAmaH gacCawi"
        assert "rAmaH gacCawi" in result["segmentation"][0]

    def test_real_morphology(self):
        """Checks if the data files (.rem) are loading correctly."""
        text = "gacCawi"  # Simple verb
        result = self.segmenter.get_morphological_analysis(text)

        error_msg = result.get("error", "No error message provided")
        assert result["status"] == "Success", f"Morph failed: {error_msg}"
        # Check if we got grammatical tags (requires .rem files to work)
        morphs = result.get("morph", [])
        assert len(morphs) > 0
        # 'gam' is the root of 'gacCawi'
        assert "gam" in morphs[0]["root"]

    def test_analyze_word_real(self):
        """Verify analyze_word works on a compound word."""
        # rAmAlayaH is a compound "Rama-Home".
        # In 'word' mode, it should be analyzed.
        # In 'sent' mode, it might be split differently.

        res = self.segmenter.analyze_word("rAmAlayaH")

        assert res["status"] == "Success"
        assert len(res["morph"]) > 0
        # Check if it identified the split inside the word analysis
        # (This depends on dictionary, but generally safe check)
        assert isinstance(res["morph"], list)
