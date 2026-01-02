# Sanskrit Heritage (Python Interface)

[![PyPI Version](https://img.shields.io/pypi/v/sanskrit-heritage.svg)](https://pypi.org/project/sanskrit-heritage/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Versions](https://img.shields.io/pypi/pyversions/sanskrit-heritage.svg)](https://pypi.org/project/sanskrit-heritage/)

A Python wrapper for the **Sanskrit Heritage Platform** (developed by Prof. Gérard Huet). This package provides a bridge to the [Heritage Engine](https://sanskrit.inria.fr/), allowing you to process Sanskrit text directly in Python scripts or via the command line.

It bundles pre-compiled binaries for **Linux**, so you can get started immediately without compiling OCaml source code (system libraries required, see below).

> **⚠️ Note on Continuous Development:**
> This wrapper is an active project under continuous development. The underlying Sanskrit Heritage Engine (binaries and data) is regularly updated to stay in sync with the upstream [INRIA repository](https://gitlab.inria.fr/huet/Heritage_Resources).
> While the Python API aims for stability, the linguistic results may improve as the dictionary and the core engines of the platform are updated.

---

## 🚀 Features

* **Versatile Processing Modes:** Run the engine at different levels:
    * **Segmentation:** Splits continuous Sanskrit text (Sandhied) into individual words.
    * **Morphological Analysis:** Analyze a single word to get the root, stem, derivational analysis, and inflection analysis.
    * **Combined Processing:** Perform segmentation and morphological analysis of a given sentence.
    * **Segmented Mode:** Analyze already segmented sentences to get the morphological analysis for each of the words.
* **Flexible Solution Depth:** Choose between the **First Solution** or retrieve the **Top 10 Solutions**.
* **Ranking Metrics:**
    * **Word Metrics:** Shallow ranking based on word frequency. Preferred for retrieving only the segmentation.
    * **Morph Metrics:** Deep ranking that considers the specific morphological analysis of each word. Preferred for retrieving both segmentation and morphological analysis.
* **Auto-Detection and Web Fallback:** Automatically detects if you have a local installation of the Heritage Platform and uses it. If not, it checks for the bundled binaries included in the package. If both fail (e.g., on Windows), it seamlessly switches to the **INRIA Web Server**.
* **Dual Interface:** Works as an importable **Python Library** and a standalone **Command Line Tool**.

---

## 🛠 Installation

### 1. Install via pip

```bash
pip install sanskrit-heritage
```

### System Requirements

This package comes with pre-compiled OCaml binaries that work out-of-the-box on most standard systems (Ubuntu, Debian, Fedora, macOS, etc.). No manual installation of OCaml or system libraries is usually required.

**Troubleshooting:** In the rare event that you see an error like `libgdbm.so.6: cannot open shared object file`, you can install the missing libraries:

* **Linux:** `sudo apt-get install ocaml libgdbm6`
* **macOS:** `brew install ocaml gdbm` (Binaries coming soon; currently uses the local installation of the Heritage Platform if available, otherwise uses Web Fallback).
* **Windows:** The package will automatically use **Web Fallback mode** (fetching results from the INRIA server). For local execution, please use **WSL (Windows Subsystem for Linux)** and follow the Linux instructions above. If you see an `externally-managed-environment` error, please install this package in a virtual environment (`python3 -m venv .venv`).

---

## 🐍 Python Usage

The core of the package is the `HeritageSegmenter` class.

### Simple Segmentation

Use `.segment()` to get a clean list of segmentation strings.

```python
from sanskrit_heritage import HeritageSegmenter

# Initialize the engine
# Defaults:
# lexicon=MW, input_encoding=DN, output_encoding=DN, mode=first,
# text_type=sent, unsandhied=False, metrics=word, timeout=30
segmenter = HeritageSegmenter()

text = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय"

# Returns a list of strings
result = segmenter.segment(text)
print(result)
```

#### Output

```
["धर्म-क्षेत्रे कुरु-क्षेत्रे समवेताः युयुत्सवः मामकाः पाण्डवाः च एव किम् अकुर्वत सञ्जय"]
```


### Morphological Analysis

Use `.analyze_word()` to get the json output containing the morphological analysis of the given word

```python
from sanskrit_heritage import HeritageSegmenter
import json

sh_segmenter = HeritageSegmenter(input_encoding="WX", output_encoding="DN", metrics="morph")

word_analysis = sh_segmenter.analyze_word("gacCawi")
print(json.dumps(word_analysis, ensure_ascii=False, indent=2))
```

#### Output

```json
{
  "input": "गच्छति",
  "status": "Success",
  "segmentation": [
    "गच्छति"
  ],
  "morph": [
    {
      "word": "गच्छति",
      "stem": "",
      "root": "गम्",
      "derivational_morph": "",
      "inflectional_morphs": [
        "pr. [1] ac. sg. 3"
      ]
    }
  ],
  "source": "SH-Local"
}
```

Compound words are also analyzed using analyze_word():

```python
word_analysis = sh_segmenter.analyze_word("rAmAlayaH")
print(json.dumps(word_analysis, ensure_ascii=False, indent=2))
```

#### Output

```json
{
  "input": "रामालयः",
  "status": "Success",
  "segmentation": [
    "राम-आलयः"
  ],
  "morph": [
    {
      "word": "राम-",
      "stem": "राम",
      "root": "",
      "derivational_morph": "",
      "inflectional_morphs": [
        "iic."
      ]
    },
    {
      "word": "आलयः",
      "stem": "आलय",
      "root": "",
      "derivational_morph": "",
      "inflectional_morphs": [
        "m. sg. nom."
      ]
    },
...
    }
  ],
  "source": "SH-Local"
}
```

### Joint Segmentation and Morphological Analysis

Use `.analyze()` to get json output with both segmentation and morphological analysis of the given sentence.

```python
analysis = segmenter.analyze("rAmovanafgacCawi")
print(json.dumps(analysis, ensure_ascii=False, indent=2))
```

#### Output

```json
{
  "input": "रामोवनङ्गच्छति",
  "status": "Success",
  "segmentation": [
    "रामः वनम् गच्छति"
  ],
  "morph": [
    {
      "word": "रामः",
      "stem": "राम",
      "root": "",
      "derivational_morph": "",
      "inflectional_morphs": [
        "m. sg. nom."
      ]
    },
    {
      "word": "वनम्",
      "stem": "वन",
      "root": "",
      "derivational_morph": "",
      "inflectional_morphs": [
        "n. sg. acc.",
        "n. sg. nom."
      ]
    },
    {
      "word": "गच्छति",
      "stem": "",
      "root": "गम्",
      "derivational_morph": "",
      "inflectional_morphs": [
        "pr. [1] ac. sg. 3"
      ]
    }
  ],
  "source": "SH-Local"
}
```

*(Note: `source` will be `SH-Web` if local binary fails)*

### 3. Advanced Usage (The Engine)

For fine-grained control over the output format (JSON vs Text) or processing mode, use the unified `process_text` method.

```python
segmenter = HeritageSegmenter(input_encoding="WX")

# process_mode: 'seg', 'morph', or 'seg-morph'
# output_format: 'text' (string), 'list' (array), or 'json' (full object)
output = segmenter.process_text(
    "rAmovanafgacCawi",
    process_mode="seg-morph",
    output_format="json"
)
```

The processing modes and the output formats are:

| Argument | Value | Description |
| :--- | :--- | :--- |
| process_mode | seg | Segmentation |
|  | morph | Morphological Analysis |
|  | seg-morph | Segmentation and Morphological Analysis |
| output_format | text | Returns a string (applicable only for Segmentation) |
|  | list | Returns a list of strings (applicable only for Segmentation) |
|  | json | Returns a JSON with values for keys: `input`, `status`, `segmentation`, `source` and `morph` 

### 4. Custom Configuration

You can also customize the engine's behavior during initialization:

```python
segmenter = HeritageSegmenter(
    lex="SH",                # Dictionary: 'MW' (Monier Williams) or 'SH' (Heritage)
    input_encoding="WX",     # DN, RN, WX, SLP, VH
    output_encoding="RN",    # DN, RN, WX
    mode="best",             # 'first' (1 solution) or 'best' (top 10 solutions)
    text_type="word",        # 'word' or 'sent'
    metrics="morph",         # Scoring metric: 'word' or 'morph' probability
    unsandhied=False,        # Input is unsandhied (segmented) 'True' or 'False'
    timeout=60               # Increase timeout for long sentences
)
```

### 5. Batch Processing

There is also an option to run a large number of sentences using parallel processing by directly calling the method `batch_process`. Given an `input_file.tsv` with sentences separated by newline:

```python
HeritageSegmenter.batch_process(
    input_path="input_file.tsv",
    output_path="output_file.tsv",
    process_mode="seg",
    output_format="text",
    # Additional arguments from the previous configurations 
    # can also be passed here like:
    # input_encoding="WX",
    # metrics="morph",
)
```

The `output_format` is automatically adjusted according to the `process_mode`. For example, when `process_mode="morph"`, `output_format` cannot be `text` and even if the user is provides `output_format="text"`, it is changed to `json`, a warning is thrown, and a JSON output is produced with the `morph` key containing the morphological analysis.

---

## 💻 Command Line Interface (CLI)

The package installs a command-line tool `sh-segment`.

### Interactive Mode

```bash
# Segment a simple sentence
sh-segment -t "रामोवनङ्गच्छति"

# Get morphological analysis (--process morph) with Roman output
sh-segment -t "गच्छति" --process morph --output_encoding RN

# Get segmentation and morphological analysis (--process seg-morph) with Roman output
sh-segment -t "रामोवनङ्गच्छति" --process seg-morph --output_encoding RN
```

### Bulk File Processing (Parallel)

Process large files efficiently using multiple CPU cores. The input file should contain newline-delimited sentences.

```bash
# Process file using 4 parallel workers
sh-segment -i input.txt -o output.txt --jobs 4

# Auto-detect max workers (jobs=0)
sh-segment -i input.txt -o output.txt --jobs 0 --input_encoding WX

# Process file sequentially
sh-segment -i input.txt -o output.txt --jobs 1 --input_encoding WX
```

### CLI Arguments

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--lexicon` | MW | Dictionary: `MW` (Monier Williams) or `SH` (Heritage) |
| `--input_encoding` | DN | Input encoding: `DN` (Devanagari), `WX`, `SL`, `RN` (IAST), `VH` |
| `--output_encoding` | DN | Output encoding: `DN`, `RN` (IAST), `WX` |
| `--mode` | first | `first` (Single solution) or `top10` (Top 10 solutions) |
| `--text_type` | sent | Input type: `sent` (Sentence) or `word` |
| `--unsandhied` | False | Input sandhi: `True` or `False` |
| `--metrics` | word | Ranking metrics: `word` or `morph` |
| `--process` | seg | `seg` (Segmentation only), `morph` (Morphological analysis), or `seg-morph` (Full) |
| `--timeout` | 30 | Execution timeout in seconds |
| `--jobs` | 1 | Parallel workers. `1`=Sequential, `0`=Auto-detect (Max Cores) |
| `--output_format` | text | `text` (clean string), `list` (json array), or `json` (full object) |

---

## ⚙️ Advanced Configuration

### Using a Local Platform Installation

If you already have the full Sanskrit Heritage Platform installed on your machine (e.g., typically at `/usr/lib/cgi-bin/SKT`), this package detects and uses it automatically instead of the bundled binaries.

You can also force the package to use a specific binary location using two methods:

### Method 1: Environment Variable (Recommended)

```bash
export SANSKRIT_HERITAGE_BIN="/path/to/your/compiled/interface2.cgi"
```

### Method 2: Python Argument

```python
engine = HeritageSegmenter(binary_path="/custom/path/to/interface2.cgi")
```

---

## ⚠️ Troubleshooting

**1. Encoding Errors**
Make sure the input does not deviate from the encoding specified as the engine does not detect encoding automatically, but will raise an error when the input and the encoding do not match. Also make sure the input does not contain special characters except `.` (Roman full stop), `।`, `॥` (Devanagari full stops), and `!`.

**2. "Unrecognized words" / "?" in Output**
If the output status is `Unrecognized` or contains words or chunks prefixed with a single `?`, it means the Sanskrit Heritage engine could not identify the word (it might be a proper noun or an OOV (out-of-vocabulary) instance). When the result is prefixed with a `??`, then the engine has failed due to timeout or crash.

**3. Segmentation (and/or Morphological Analysis) Errors**
It is possible that sometimes the expected results are not produced. In such cases, try changing the `metrics`. Alternatively, try the `top10` mode to capture more possible results.

**4. Debugging**
If you are using the Python API and encountering issues, you can enable debug logging to see the internal execution details:

```python
import logging
from sanskrit_heritage import HeritageSegmenter

# Enable logging to see what's happening under the hood
logging.basicConfig(level=logging.DEBUG)  # or logging.INFO

segmenter = HeritageSegmenter()
segmenter.get_segmentation("...")
```

---

## ⚖️ License & Acknowledgements

This package is a Python interface developed to facilitate access to the **Sanskrit Heritage Platform**.

* **Original Platform:** Developed by Prof. Gérard Huet at INRIA, Paris. [Official Website](https://sanskrit.inria.fr/)
* **Python Wrapper:** Developed by Sriram Krishnan.
* **License:** The Python source code in this package is licensed under the GNU GPLv3 License. This ensures the project remains open and free for the community.
* **Data License:** The bundled binary and dictionary data (`.rem` files) are derived from the Sanskrit Heritage Platform. They are typically distributed under the [CeCILL-C License](http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html) (compatible with GNU GPL). Please refer to the INRIA website for strict commercial usage terms regarding the engine data.

**Acknowledgements:** We gratefully acknowledge the work of Prof. Gérard Huet, INRIA, Paris for creating the underlying engine. For more details, visit the [Sanskrit Heritage Site](https://sanskrit.inria.fr/). We also thank Prof. Huet and Prof. Amba Kulkarni, University of Hyderabad for guiding the research work that led to the development of this package.

We would also like to acknowledge Dr. Oliver Hellwig for the [Digital Corpus of Sanskrit](https://github.com/OliverHellwig/sanskrit), a re-analysed version of which is used in this package as the base dataset for the ranking mechanism.

For more details regarding the research work behind this package, visit: [Normalized dataset for Sanskrit word segmentation and morphological parsing](https://link.springer.com/article/10.1007/s10579-024-09724-0).