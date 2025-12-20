# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-20

### Added
- **Core Library:**
    - `HeritageSegmenter` class for programmatic access to the Sanskrit Heritage engine.
    - Automatic detection of local binaries with a Web Fallback mode.
    - Support for Segmentation, Morphological Analysis, and Combined processing.
- **CLI:**
    - `sh-segment` command line tool for quick processing.
    - Streaming support for processing large text files (NDJSON output).