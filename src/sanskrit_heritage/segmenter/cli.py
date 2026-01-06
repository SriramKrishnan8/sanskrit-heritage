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
import multiprocessing
import logging

from .interface import HeritageSegmenter


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
    parser.add_argument(
        "--output_format",
        default="text",
        choices=["json", "list", "text"],
        help="Output structure: 'json' (full data) or 'list' (of strings)" +
             " or 'text' (string). 'list' is only valid for segmentation."
    )

    # --- Input/Output & Parallelism ---
    parser.add_argument(
        "-t", "--input_text", type=str, help="Input text string"
    )
    parser.add_argument(
        "-i", "--input_file", type=str, help="Path to input file"
    )
    parser.add_argument(
        "-o", "--output_file", type=str, help="Path to output file"
    )
    parser.add_argument(
        "--jobs", type=int, default=1,
        help="Number of parallel processes. 1=Sequential, 0=auto-detect."
    )

    args = parser.parse_args()

    # --- LOGGING CONFIGURATION ---
    # 1. Decide the level based on the flag
    log_level = logging.DEBUG if args.debug else logging.INFO

    # 2. Configure the root logger
    # This setting applies to ALL files (batch.py, interface.py, etc.)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr
    )

    logger = logging.getLogger("CLI")
    # -----------------------------

    # --- 2. Validation ---
    if not args.input_text and not args.input_file:
        logger.error(
            "Error: Please specify either input text ('-t') "
            "or input file ('-i')"
        )
        sys.exit(1)

    if args.input_file and not args.output_file:
        logger.error(
            "Error: Output file ('-o') is required when using input file",
        )
        sys.exit(1)

    # --- 3. Build preparation ---
    # We create a config dict to pass to the batch processor if needed
    config_dict = {
        "lex": args.lexicon,
        "input_encoding": args.input_encoding,
        "output_encoding": args.output_encoding,
        "mode": args.mode,
        "text_type": args.text_type,
        "unsandhied": args.unsandhied,
        "metrics": args.metrics,
        "timeout": args.timeout,
        "binary_path": args.binary_path
    }

    # --- 4. Initialize Local Segmenter (Conditional) ---
    try:
        logger.debug("Initializing Heritage Segmenter...")
        sh_segmenter = HeritageSegmenter(**config_dict)
    except Exception as e:
        logger.critical(f"Initialization Error: {e}")
        if args.debug:
            logger.exception("Stack trace.")
        sys.exit(1)

    # --- 5. Execution Logic ---

    # Indent if printing to screen, Compact if writing to file
    should_indent = 2 if not args.output_file else None

    # A. Single Text Mode
    if args.input_text:
        logger.info("Processing single text input...")
        try:
            result = sh_segmenter.process_text(
                args.input_text,
                process_mode=args.process,
                output_format=args.output_format,
            )

            output_str = HeritageSegmenter.serialize_result(
                result, args.output_format, should_indent
            )

            if args.output_file:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    f.write(output_str)
                logger.info(f"Output written to {args.output_file}")
            else:
                print(output_str)
        except Exception as e:
            logger.error(f"Processing Error: {e}")
            sys.exit(1)

    # B. Bulk File Mode
    elif args.input_file:
        logger.info(f"Preparing batch processing for {args.input_file}...")

        # 1. Determine Workers
        # If user passes 1, we pass 1. If 0 or > 1, we pass that.
        # process_file handles the optimization logic.
        workers_arg = args.jobs if args.jobs != 1 else 1

        # 3. Call the Engine
        # We catch keyboard interrupt (Ctrl+C) gracefully here
        try:
            sh_segmenter.process_file(
                input_path=args.input_file,
                output_path=args.output_file,
                workers=workers_arg,
                process_mode=args.process,
                output_format=args.output_format,
            )
            logger.info(f"Completed. Results written to {args.output_file}")

        except KeyboardInterrupt:
            logger.warning("\nBatch processing interrupted by user.")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Critical Batch Error: {e}")
            if args.debug:
                logger.exception("Traceback:")
            sys.exit(1)


if __name__ == "__main__":
    # For Windows compatibility when freezing logic or spawning processes
    multiprocessing.freeze_support()
    main()
