# tests/test_integration_real.py

import sys
from pathlib import Path

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
