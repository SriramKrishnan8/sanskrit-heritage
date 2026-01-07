# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-01-08

### Changed
- **Data Update:** Updated bundled binary and dictionary resources (`.rem` files) to sync with the latest upstream INRIA repository.
- **CLI:** Changed default logging level from `INFO` to `WARNING` to keep standard output clean for piping.

### Fixed
- **Bug:** Removed `\u0942` (Devanagari Vowel Sign UU) from the ignored characters list, correcting issues where long 'u' was being stripped from input.
- **Internal:** Added detailed Unicode documentation/comments for special character handling.

## [1.0.0] - 2026-01-07

### 🎉 Milestone: Production Ready
This release marks the transition to stable version 1.0.0. It introduces a robust, unified processing engine and parallel batch capabilities.

### Added
- **Unified API:** Introduced `process_text()` as the central entry point for all processing modes.
- **New User-Friendly Wrappers:**
    - `segment()`: Returns a clean String (e.g., "word1 word2").
    - `analyze_word()`: Returns JSON for word analysis.
    - `analyze()`: Returns JSON for full sentence segmentation and morphology.
- **Batch Processing:**
    - `process_file()`: High-performance disk-to-disk processing with multiprocessing support.
    - `process_list()`: In-memory list processing with parallel execution.
- **CLI Enhancements:**
    - Added `--jobs` argument for parallel execution.
    - Added `--output_format` argument to control JSON/Text/List output.
- **Progress Bars:** Integrated `tqdm` for better visibility during batch operations.
- **Serialization:** Created static `serialize_result` to standardize output formatting (JSON/Text/List) across CLI and Batch modes.

### Changed
- **Breaking (CLI Only):** The default output for segmentation in the CLI is now a **raw string** instead of a JSON list. 
    - *Old:* `['result']` 
    - *New:* `result`
    - *Migration:* Use `--output_format list` to restore old behavior.
- **Architecture:** Refactored core logic out of the CLI and into `interface.py`.
- **Performance:** Optimized logging strategies to prevent UI interference during batch processing.

### Fixed
- Fixed CLI initialization issues when running in parallel mode.
- Improved error handling for empty inputs in batch mode (returns `??` prefixed in the output when there is a timeout issue or a crash).

## [0.1.1] - 2025-12-20

### Fixed
- Updated PyPI package metadata to point to the correct GitHub repository URLs.

## [0.1.0] - 2025-12-20

### Added
- **Core Library:**
    - `HeritageSegmenter` class for programmatic access to the Sanskrit Heritage engine.
    - Automatic detection of local binaries with a Web Fallback mode.
    - Support for Segmentation, Morphological Analysis, and Combined processing.
- **CLI:**
    - `sh-segment` command line tool for quick processing.
    - Streaming support for processing large text files (NDJSON output).