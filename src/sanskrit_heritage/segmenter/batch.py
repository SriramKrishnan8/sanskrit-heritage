# src/sanskrit_heritage/segmenter/batch.py

import os
import multiprocessing
import math
import logging
from tqdm import tqdm
from .interface import HeritageSegmenter

# Create a logger for this specific file
logger = logging.getLogger(__name__)

# --- CONFIGURATION CONSTANTS ---
# Reserve at least 1 core so the OS/UI doesn't freeze
CORES_RESERVED_FOR_OS = 1

# Max workers for WSL to prevent 'vmmem' RAM exhaustion crashes
MAX_WORKERS_WSL = 4

# Max workers for standard Linux/Mac to prevent general RAM exhaustion
# (Can be overridden by user input)
MAX_WORKERS_DEFAULT = 6

# Batch Size Limits
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 100


def _worker_process(payload):
    """
    This function runs on a separate CPU core.
    payload: (list_of_lines, segmenter_config, output_format, process_mode)
    """
    lines, config, process_mode, output_format = payload

    # Instantiate a fresh segmenter for this CPU core
    segmenter = HeritageSegmenter(**config)

    results = []
    for text in lines:
        text = text.strip()
        if not text:
            continue

        res = segmenter.process_text(
            text,
            process_mode=process_mode,
            output_format=output_format
        )
        results.append(res)

    return results


def run_parallel_batch(
    input_file, output_file, config,
    process_mode="seg",
    output_format="text",
    num_workers=None
):
    """Orchestrates the parallel processing."""
    # 1. Read all lines
    logger.info(f"Reading input from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    total_lines = len(lines)
    if total_lines == 0:
        logger.warning(f"Input file {input_file} is empty.")
        return

    # 2. Determine Workers
    if num_workers is None or num_workers < 1:
        max_physical_cores = multiprocessing.cpu_count()

        # Check if running on WSL
        is_wsl = "microsoft-standard" in os.uname().release \
                 if hasattr(os, 'uname') else False

        # Reserve 1 core Windows OS
        safe_cores = max(1, max_physical_cores - CORES_RESERVED_FOR_OS)

        if is_wsl:
            num_workers = min(safe_cores, MAX_WORKERS_WSL)
        else:
            num_workers = min(safe_cores, MAX_WORKERS_DEFAULT)

    # Cap workers if we have fewer lines than workers
    num_workers = min(num_workers, total_lines)

    logger.info(
        f"Starting parallel processing on {total_lines} sentences"
        f" using {num_workers} workers."
    )

    # --- DYNAMIC BATCH SIZING ---
    # Target roughly 4 tasks per worker to ensure everyone stays busy
    # but cap it at 100 to prevent long stalls on difficult batches.
    target_batches_per_worker = 4
    if num_workers > 0:
        raw_batch_size = math.ceil(
            total_lines / (num_workers * target_batches_per_worker)
        )
    else:
        raw_batch_size = total_lines

    # Clamb between 1 and 100
    batch_size = max(MIN_BATCH_SIZE, min(raw_batch_size, MAX_BATCH_SIZE))

    current_mode = config.get("mode", "first")

    # --- WARNING LOGIC ---

    # Warning for morph output
    if "morph" in process_mode and output_format in ["list", "text"]:
        logger.warning(
            f"WARNING: process_mode='{process_mode}' contains rich data."
            f" output_format='list' is incompatible."
            " Automatically forcing 'json' format."
        )
        output_format = "json"

    # Warning for text output
    elif current_mode == "top10" and output_format == "text":
        logger.warning(
            "WARNING: mode='top10' returns multiple solutions." +
            " output_format='text' (single string) is incompatible." +
            " Automatically forcing 'list' format."
        )
        output_format = "list"

    logger.info(
        f"Config: {total_lines} sentences | {num_workers} workers | "
        f"Mode: {process_mode} | Batch size {batch_size} | "
        f"Format: {output_format}"
    )

    # Chunk creation
    chunks = []
    for i in range(0, total_lines, batch_size):
        chunk_lines = lines[i: i + batch_size]
        # Pack the config so the worker knows how to behave
        chunks.append((chunk_lines, config, process_mode, output_format))

    # 4. Run Parallel Pool
    results_flat = []
    with multiprocessing.Pool(processes=num_workers) as pool:
        # We use imap to get results as they finish and show a progress bar
        # Note: We are iterating over chunks, not individual lines
        iterator = pool.imap(_worker_process, chunks)

        # tqdm progress bar counts completed CHUNKS,
        # not lines (simplifies overhead)
        for chunk_result in tqdm(
            iterator, total=len(chunks), desc="Processing Batches"
        ):
            results_flat.extend(chunk_result)

    # 5. Write Output
    logger.info(f"Writing results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for res in results_flat:
            line_out = HeritageSegmenter.serialize_result(
                res, output_format, indent=None
            )
            f.write(line_out + "\n")

    logger.info("Done.")
