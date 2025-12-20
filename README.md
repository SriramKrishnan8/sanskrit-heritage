# Sanskrit Heritage (Python Interface)

[![PyPI version](https://badge.fury.io/py/sanskrit-heritage.svg)](https://badge.fury.io/py/sanskrit-heritage)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A Python wrapper for the **Sanskrit Heritage Platform** (developed by Prof. Gérard Huet). This package provides a bridge to the [Heritage Engine](https://sanskrit.inria.fr/), allowing you to process Sanskrit text directly in Python scripts or via the command line.

It bundles pre-compiled binaries for **Linux**, so you can get started immediately without compiling OCaml source code (system libraries required, see below).

> **⚠️ Note on Continuous Development:**
> This wrapper is an active project under continuous development. The underlying Sanskrit Heritage Engine (binaries and data) is regularly updated to stay in sync with the upstream [INRIA repository](https://gitlab.inria.fr/huet/Heritage_Resources).
> While the Python API aims for stability, the linguistic results may improve as the dictionary and the core engines of the platform are updated.

---

## 🚀 Features

* **Versatile Processing Modes:** Run the engine at different levels:
  * **Segmentation:** Splits continuous Sanskrit text (Sandhied) into individual words
  * **Morphological Analysis:** Analyze a single word to get the root, stem, derivational analysis and inflection analysis.
  * **Combined Processing:** Perform segmentation and morphological analysis of a given sentence.
  * **Segmented Mode:** Analyze already segmented sentences to get the morphological analysis for each of the words.
* **Flexible Solution Depth:** Choose between the **First Solution** or retrieve the **Top 10 Solutions**.
* **Ranking Metrics:**
    * **Word Metrics:** Shallow ranking based on word frequency. Preferred for retrieving only the segmentation.
    * **Morph Metrics:** Deep ranking that considers the specific morphological analysis of each word. Preferred for retrieving both segmentation and morphological analysis.
* **Auto-Detection and Web Fallback:** Automatically detects if you have a local installation of the Heritage Platform and uses it; if not, then checks for the bundled binaries that come along with the package. If both of these fail (e.g., on Windows), then switches to the **INRIA Web Server**.
* **Dual Interface:** Works as an importable **Python Library** and a standalone **Command Line Tool**.

---

## 🛠 Installation

### 1. Install via pip
```bash
pip install sanskrit-heritage
```

### System Requirements
This package comes with pre-compiled Ocaml binaries that work out-of-the-box on most standard systems (Ubuntu, Debian, Fedora, macOS, etc.). No manual installation of OCaml or system libraries is usually required. 

**Troubleshooting:** In the rare event that you see an error like `libgdbm.so.6: cannot open shared object file`, you can install the missing libraries:

* **Linux:** `sudo apt-get install ocaml libgdbm6`
* **macOS:** `brew install ocaml gdbm` (Binaries coming soon; currently uses the local installation of the Heritage Platform if available, otherwise uses Web Fallback).
* **Windows:** The package will automatically use **Web Fallback mode** (fetching results from the INRIA server). For local execution, please use **WSL (Windows Subsystem for Linux)** and follow the Linux instructions above. If you see an `externally-managed-environment` error, please install this package in a virtual environment (`python3 -m venv .venv`).

--

## 🐍 Python Usage

The core of the package is the `HeritageSegmenter` class.

### Basic Segmentation

```Python
from sanskrit_heritage import HeritageSegmenter

# Initialize the engine
# Defaults:
# lexicon=MW, input_encoding=DN, output_encoding=DN, mode=first,
# text_type=sent, unsandhied=False, metrics=word, timeout=30
segmenter = HeritageSegmenter()

text = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय​"
result = segmenter.get_segmentation(text)

print(result)
```

### Output
```JSON
{
  "input": "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय",
  "status": "Success",
  "segmentation": ["धर्म-क्षेत्रे कुरु-क्षेत्रे समवेताः युयुत्सवः मामकाः पाण्डवाः च एव किम् अकुर्वत सञ्जय"],
  "source": "SH-local",
  "morph": []
}
```
*(Note: `source` will be `SH-Web` if local binary fails)*

### Morphological Analysis
```Python
# Initialize with custom encoding (WX)
segmenter = HeritageSegmenter(input_encoding="WX", output_encoding="WX")

text = "gacCawi"
analysis = segmenter.get_morphological_analysis(text)
print(analysis)
```

### Output
```JSON
{
  "input": "gacCawi",
  "status": "Success",
  "segmentation": [
    "gacCawi"
  ],
  "morph": [
    {
      "word": "gacCawi",
      "stem": "",
      "root": "gam",
      "derivational_morph": "",
      "inflectional_morphs": [
        "pr. [1] ac. sg. 3"
      ]
    },
    {
      "word": "gacCawi",
      "stem": "gacCaw",
      "root": "gam",
      "derivational_morph": "ppr. [1] ac.",
      "inflectional_morphs": [
        "n. sg. loc.",
        "m. sg. loc."
      ]
    }
  ],
  "source": "SH-Local"
}
```

### Custom Configuration
You can customize the engine's behavior during initialization:

```Python
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

## 💻 Command Line Interface (CLI)

The package installs a command-line tool sh-segment.

### Interactive Mode
```Bash
# Segment a simple sentence
sh-segment -t "रामोवनङ्गच्छति"

# Get morphological analysis (-p morph) with Roman output
sh-segment -t "गच्छति" --process morph --output_encoding RN

# Get segmentation and morphological analysis (-p seg-morph) with Roman output
sh-segment -t "रामोवनङ्गच्छति" --process seg-morph --output_encoding RN
```

### Bulk File Processing
Process a file containing newline-delimited sentences. The output will be a newline-delimited json strings.
```Bash
sh-segment -i input.txt -o output.txt
```

### CLI Arguments

| Argument | Default | Description |
| :--- | :--- | :--- |
| --lexicon | MW | Dictionary: MW (Monier Williams) or SH (Heritage) |
| --input_encoding | DN | Input encoding: DN (Devanagari), WX, SL, RN (IAST), VH, KH |
| --output_encoding | DN | Output encoding: DN, RN (IAST), WX |
| --mode | first | first (Single solution) or top10 (Top 10 solutions) |
| --text_type | sent | Input type: sent (Sentence) or word |
| --unsandhied | False | Input sandhi: True or False |
| --metrics | word | Ranking metrics: word or morph |
| --process | seg | seg (Segmentation only) or morph (Morphological analysis) or seg-morph (Full analysis) |
| --timeout | 30 | Execution timeout in seconds |

## ⚙️ Advanced Configuration

### Using a Local Platform Installation
If you already have the full Sanskrit Heritage Platform installed on your machine (e.g., typically at `/usr/lib/cgi-bin/SKT`), this package detects and uses it automatically instead of the bundled binaries.

You can also force the package to use a specific binary location using two methods:

### Method 1: Environment Variable (Recommended)
```Bash
export SANSKRIT_HERITAGE_BIN="/path/to/your/compiled/interface2.cgi"
```

### Method 2: Python Argument
```Python
engine = HeritageSegmenter(binary_path="/custom/path/to/interface2.cgi")
```

## ⚠️ Troubleshooting

**1. Encoding Errors**
Make sure the input does not deviate from the encoding specified, and does not contain special characters except '.' (Roman full stop), '।', '॥' (Devanagari full stops), and '!'.

**2. "Unrecognized words" / "?" in Output**
If the output status is `Unrecognized` or contains `?`, it means the Sanskrit Heritage engine could not identify the word (it might be a proper noun or an OOV (out-of-vocabulary) instance).

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