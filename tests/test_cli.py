# tests/test_cli.py

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

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

        # Mock the static process_text
        mock_instance.process_text.return_value = ["res"]
        # Mock the static serializer to return a simple string
        MockSegmenter.serialize_result.return_value = "res"

        cli.main()

        # Check if Segmenter was initialized with correct args
        MockSegmenter.assert_called_once()
        _, kwargs = MockSegmenter.call_args
        assert kwargs['timeout'] == 30  # Default check

        # Check if the method was called
        mock_instance.process_text.assert_called_once_with(
            "test_input",
            process_mode="seg",
            output_format="text"
        )

        call_args = mock_instance.process_text.call_args
        assert call_args[0][0] == "test_input"  # First positional arg is text
        assert call_args[1]['process_mode'] == 'seg'  # Default


def test_cli_single_text_default():
    """Test default behavior: -t TEXT -> output_format='text'."""
    test_args = ["sh-segment", "-t", "rAmogacCawi"]

    with patch.object(sys, 'argv', test_args), \
         patch("sanskrit_heritage.segmenter.cli.HeritageSegmenter") \
            as MockSegmenter:

        mock_instance = MockSegmenter.return_value
        # process_text returns a list (Data)
        mock_instance.process_text.return_value = ["rAmaH gacCawi"]
        # serialize_result returns a string (Presentation)
        MockSegmenter.serialize_result.return_value = "rAmaH gacCawi"

        with patch('sys.stdout', new_callable=MagicMock) as mock_stdout:
            cli.main()

            # 1. Verify args passed to process_text (Default is now 'text')
            mock_instance.process_text.assert_called_once_with(
                "rAmogacCawi",
                process_mode="seg",
                output_format="text"
            )

            write_calls = mock_stdout.write.call_args_list
            printed_text = "".join(
                [call.args[0] for call in write_calls if call.args]
            )
            assert "rAmaH gacCawi" in printed_text

            # 2. Verify serialize was called with pretty indent (2) for screen
            MockSegmenter.serialize_result.assert_called_once_with(
                ["rAmaH gacCawi"], "text", 2
            )


def test_cli_single_text_morph_mode():
    """Test -t TEXT --process morph -> Should force JSON format logic."""
    test_args = [
        "sh-segment", "-t", "rAmogacCawi",
        "--process", "morph",
        "--output_format", "list"
    ]

    with patch.object(sys, 'argv', test_args), \
         patch("sanskrit_heritage.segmenter.cli.HeritageSegmenter") \
            as MockSegmenter:

        mock_instance = MockSegmenter.return_value
        mock_instance.process_text.return_value = {"morph": []}
        MockSegmenter.serialize_result.return_value = "{}"

        cli.main()

        mock_instance.process_text.assert_called_once_with(
            "rAmogacCawi",
            process_mode="morph",
            output_format="list"
        )


def test_cli_exception_handling():
    """Test that CLI exits gracefully (code 1) if processing crashes."""
    test_args = ["sh-segment", "-t", "crash_input"]

    with patch.object(sys, 'argv', test_args), \
         patch("sanskrit_heritage.segmenter.cli.HeritageSegmenter") \
            as MockSegmenter:

        mock_instance = MockSegmenter.return_value
        # Simulate a crash inside the library
        mock_instance.process_text.side_effect = Exception("Engine Explosion")

        with pytest.raises(SystemExit) as excinfo:
            cli.main()

        assert excinfo.value.code == 1


def test_cli_batch_parallel_dispatch():
    test_args = [
        "sh-segment", "-i", "in.txt", "-o", "out.json",
        "--jobs", "4", "--output_format", "json"
    ]
    with patch.object(sys, 'argv', test_args), \
         patch("sanskrit_heritage.segmenter.cli.run_parallel_batch") \
            as mock_batch:
        cli.main()
        mock_batch.assert_called_once()
        _, kwargs = mock_batch.call_args
        assert kwargs["output_format"] == "json"


def test_cli_batch_sequential_dispatch():
    test_args = ["sh-segment", "-i", "in.txt", "-o", "out.json", "--jobs", "1"]
    mock_file_content = "line1\nline2"

    with patch.object(sys, 'argv', test_args), \
         patch("sanskrit_heritage.segmenter.cli.HeritageSegmenter") \
            as MockSegmenter, \
         patch("builtins.open", mock_open(read_data=mock_file_content)):

        mock_instance = MockSegmenter.return_value
        MockSegmenter.serialize_result.return_value = "res"  # Mock static
        cli.main()

        # Verify both processing and serialization happen per line
        assert mock_instance.process_text.call_count == 2
        assert MockSegmenter.serialize_result.call_count == 2
