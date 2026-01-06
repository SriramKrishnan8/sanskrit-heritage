# src/sanskrit_heritage/segmenter/batch.py

import os
import multiprocessing
import math
import logging
import psutil
from functools import partial

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


def _worker_task(text, config, process_mode, output_format):
    """
    Worker function running in a separate process.
    Instantiates the segmenter locally to avoid pickling complex objects.
    """
    from .interface import HeritageSegmenter

    # 1. Handle empty lines or whitespace logic if needed
    if not text or not text.strip():
        return None

    try:
        # 2. Instantiate a fresh segmenter for this CPU core
        segmenter = HeritageSegmenter(**config)

        # 3. Process
        return segmenter.process_text(
            text.strip(),
            process_mode=process_mode,
            output_format=output_format
        )
    except Exception as e:
        logger.error(
            f"Worker process crash processing '{text[:20]}...': {e}",
            exc_info=True
        )

        # Returning the exception object for interface to handle this
        return e


def _get_optimal_execution_params(total_items, requested_workers):
    """
    Centralized logic to determine Worker Count and Chunk Size.
    """
    # 1. Determine Max Available CPU Cores
    max_physical_cores = psutil.cpu_count(logical=False) or \
        multiprocessing.cpu_count()

    # Check for WSL (Windows Subsystem for Linux) constraints
    is_wsl = "microsoft-standard" in os.uname().release \
        if hasattr(os, 'uname') else False

    # Reserve 1 core Windows OS
    safe_cores = max(1, max_physical_cores - CORES_RESERVED_FOR_OS)

    hardware_limit = MAX_WORKERS_WSL if is_wsl else MAX_WORKERS_DEFAULT
    available_workers = min(safe_cores, hardware_limit)

    # 2. Determine Final Worker Count
    if requested_workers is None or requested_workers < 1:
        workers = available_workers
    else:
        workers = requested_workers

    # Cap workers if dataset is tiny (Don't launch 6 workers for 3 items)
    if total_items and total_items > 0:
        workers = min(workers, total_items)

    # 3. Calculate Optimal Chunk Size
    # If total is unknown (streaming without count), use safe default
    if not total_items or total_items <= 0:
        logger.debug(
            "Unknown dataset size (Streaming). Defaulting chunk_size=20."
        )
        chunk_size = 20
    else:
        # Target ~4 batches per worker to balance load and overhead
        target_batches_per_worker = 4
        if workers > 0:
            raw_batch_size = math.ceil(
                total_items / (workers * target_batches_per_worker)
            )
            # Clamp between 1 and 100
            chunk_size = max(
                MIN_BATCH_SIZE,
                min(raw_batch_size, MAX_BATCH_SIZE)
            )
        else:
            chunk_size = 1

    return workers, chunk_size


def process_iterator(input_iterable, config,
                     process_mode="seg", output_format="text",
                     total_items=None, requested_workers=None):
    """
    The Core Engine.
    Handles resource calculation and parallel execution.
    """

    # 1. Calculate Resources (The redundancy is fixed here!)
    num_workers, chunk_size = _get_optimal_execution_params(
        total_items, requested_workers
    )

    logger.debug(
        f"Execution Plan: {num_workers} workers | "
        f"Chunksize: {chunk_size} | "
        f"Total Items: {total_items if total_items else 'Unknown'}"
    )

    # 2. Freeze arguments
    worker_func = partial(
        _worker_task,
        config=config,
        process_mode=process_mode,
        output_format=output_format
    )

    # 3. Execute
    # Optimization: If only 1 worker is needed,
    # avoid Multiprocessing Pool overhead completely
    if num_workers == 1:
        logger.debug("Mode: Sequential (Main Process)")
        for item in input_iterable:
            yield worker_func(item)
    else:
        logger.debug("Mode: Parallel (Multiprocessing Pool)")
        with multiprocessing.Pool(processes=num_workers) as pool:
            result_iterator = pool.imap(
                worker_func, input_iterable, chunksize=chunk_size
            )
            for result in result_iterator:
                yield result
