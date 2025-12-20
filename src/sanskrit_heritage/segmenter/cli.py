# src/sanskrit_heritage/segmenter/cli.py
#
# Copyright (C) 2025 Sriram Krishnan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import argparse
import json
from tqdm import tqdm
import logging
from .interface import HeritageSegmenter


def process_text(segmenter, text, process_mode):
    """
    Helper to dispatch the correct method based on CLI args.
    This ensures logic is consistent for both single-text and bulk-file modes.
    """
    if process_mode == "seg":
        return segmenter.get_segmentation(text)
    elif process_mode == "morph":
        return segmenter.get_morphological_analysis(text)
    else:  # "seg-morph"
        return segmenter.get_analysis(text)


def main():
    parser = argparse.ArgumentParser(
        description="Sanskrit Heritage Segmenter Interface"
    )

    # --- Encoding Arguments ---
    parser.add_argument(
        "--input_encoding", default="DN",
        choices=["DN", "RN", "SL", "VH", "WX"],
        help="Input encoding"
    )
    parser.add_argument(
        "--output_encoding", default="DN", choices=["DN", "RN", "WX"],
        help="Output encoding"
    )

    # --- Mode Arguments ---
    parser.add_argument(
        "--text_type", default="sent", choices=["sent", "word"],
        help="Treat input text as a full sentence or a single word"
    )
    parser.add_argument(
        "--mode", default="first", choices=["first", "top10"],
        help="Return only the first solution or the top 10 solutions"
    )
    parser.add_argument(
        "--unsandhied", default="False", choices=["True", "False"],
        help="True: Input is already split. False: Input is a sentence."
    )
    parser.add_argument(
        "--metrics", default="word", choices=["word", "morph"],
        help="Ranking metrics: Word frequency or Morph frequency"
    )
    parser.add_argument(
        "--process", default="seg", choices=["seg", "morph", "seg-morph"],
        help="Segmentation only or with Morph Analysis"
    )
    parser.add_argument(
        "--lexicon", default="MW", choices=["MW", "SH"],
        help="Monier Williams (MW) or Sanskrit Heritage (SH)"
    )

    # --- System Arguments ---
    parser.add_argument(
        "--timeout", default=30, type=int,
        help="Maximum execution time in seconds. Should be less than 300."
    )
    parser.add_argument(
        "--binary_path", default=None, type=str,
        help="Path where Heritage is installed if known."
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable detailed debug logging"
    )

    # --- Input/Output ---
    parser.add_argument(
        "-t", "--input_text", type=str, help="Input text string"
    )
    parser.add_argument(
        "-i", "--input_file", type=str, help="Path to input file"
    )
    parser.add_argument(
        "-o", "--output_file", type=str, help="Path to output file"
    )

    args = parser.parse_args()

    # --- 1. Configure Logging ---
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # --- 2. Validation ---
    if not args.input_text and not args.input_file:
        print(
            "Error: Please specify either input text ('-t') "
            "or input file ('-i')",
            file=sys.stderr
        )
        sys.exit(1)

    # --- 3. Initialize Segmenter ---
    try:
        sh_segmenter = HeritageSegmenter(
            lex=args.lexicon,
            input_encoding=args.input_encoding,
            output_encoding=args.output_encoding,
            mode=args.mode,
            text_type=args.text_type,
            unsandhied=args.unsandhied,
            metrics=args.metrics,
            timeout=args.timeout
        )
    except Exception as e:
        print(f"Initialization Error: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 4A. Handle Single Text Input ---
    if args.input_text:
        result = process_text(sh_segmenter, args.input_text, args.process)

        output_str = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(output_str)
            print(f"Output written to {args.output_file}")
        else:
            print(output_str)

    # --- 4B. Handle Bulk File Input ---
    elif args.input_file:
        if not args.output_file:
            print(
                "Error: Output file ('-o') is required with input file",
                file=sys.stderr
            )
            sys.exit(1)

        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                input_lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Error: File {args.input_file} not found.", file=sys.stderr)
            sys.exit(1)

        print(f"Processing {len(input_lines)} sentences...")

        try:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                for line in tqdm(input_lines, desc="Processing"):
                    res = process_text(sh_segmenter, line, args.process)
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"\nError during bulk processing: {e}", file=sys.stderr)
            print(f"Partial results saved to {args.output_file}")
            sys.exit(1)

        print(f"Completed. Results written to {args.output_file}")


if __name__ == "__main__":
    main()
