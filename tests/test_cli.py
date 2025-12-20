# tests/test_cli.py

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Adjust path to import source code
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Ignore E402 as strict import order isn't possible with sys.path hack
# NOTE: Corrected import from 'interface' to 'segmenter' module
from sanskrit_heritage.segmenter import cli  # noqa: E402


def test_cli_no_args():
    """Running CLI with no args should exit with error."""
    with patch.object(sys, 'argv', ['sh-segment']), pytest.raises(SystemExit):
        cli.main()


def test_cli_basic_flow():
    """Test a basic CLI call parameters."""
    test_args = [
        "sh-segment",
        "-t", "test_input",
        "--binary_path", "dummy_bin"  # Pass dummy so it attempts init
    ]

    # Mock HeritageSegmenter so the engine is not actually run
    with patch.object(sys, 'argv', test_args), patch(
        "sanskrit_heritage.segmenter.cli.HeritageSegmenter"
    ) as MockSegmenter:

        # Setup mock instance
        mock_instance = MockSegmenter.return_value
        mock_instance.get_segmentation.return_value = {"status": "Success"}

        cli.main()

        # Check if Segmenter was initialized with correct args
        MockSegmenter.assert_called_once()
        _, kwargs = MockSegmenter.call_args
        assert kwargs['timeout'] == 30  # Default check

        # Check if the method was called
        mock_instance.get_segmentation.assert_called_once_with("test_input")
