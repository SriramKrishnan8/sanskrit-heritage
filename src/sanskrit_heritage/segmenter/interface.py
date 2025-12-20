#!/usr/bin/env python3
# src/sanskrit_heritage/segmenter/interface.py
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

import os
import subprocess as sp
import psutil
import json
import re
import logging
from itertools import product, islice
import requests
import devtrans as dt

# Safer import to prevent circular dependency issues
try:
    from sanskrit_heritage import config
except ImportError:
    # Fallback for local testing without package install
    import config  # type: ignore

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
INRIA_URL = "https://sanskrit.inria.fr/cgi-bin/SKT/interface2.cgi"

# These act as both validation sets and conversion maps
MAP_TEXT_MODE = {"word": "f", "sent": "t"}
MAP_SEG_MODE = {"first": "s", "top10": "l"}
MAP_METRICS = {"word": "w", "morph": "n"}
MAP_UNSANDHIED = {
    "sandhied": "f", "unsandhied": "t",
    "f": "f", "t": "t",
    # Since the Heritage Platform has the key 'unsandhied',
    # we have to align the assignments with it as below
    False: "f", True: "t"
}
MAP_OUT_ENC = {"DN": "deva", "RN": "roma", "WX": "WX"}

VALID_LEX = {"MW", "SH"}
VALID_IN_ENC = {"DN", "KH", "RN", "SL", "VH", "WX"}
VALID_OUT_ENC = {"DN", "RN", "WX"}


class HeritageSegmenter:
    def __init__(self,
                 lex="MW",
                 input_encoding="DN",
                 output_encoding="DN",
                 mode="first",
                 text_type="sent",
                 unsandhied=False,
                 metrics="word",
                 timeout=30,
                 binary_path=None):

        # 1. Initialize Configuration (Using setters for validation)
        self.lex = lex
        self.input_encoding = input_encoding
        self.output_encoding = output_encoding
        self.mode = mode
        self.text_type = text_type
        self.unsandhied = unsandhied
        self.metrics = metrics
        self.timeout = timeout

        # 2. Binary Resolution & Fallback Logic
        self.cgi_path = config.resolve_binary_path(binary_path)
        self.use_web_fallback = False

        if not self.cgi_path:
            logger.warning(
                "Local binary not found. Switching to INRIA Web Server mode."
            )
            self.use_web_fallback = True
            self.execution_cwd = None
        else:
            self.execution_cwd = config.get_data_path(self.cgi_path)
            # Set permissions if bundled
            if config.ASSETS_DIR in self.cgi_path.parents:
                try:
                    os.chmod(str(self.cgi_path), 0o755)
                except OSError:
                    pass

        # 3. Internal Constants
        self.svaras = [
            '\uA8E1', '\uA8E2', '\uA8E3', '\uA8E4', '\uA8E5', '\uA8E6',
            '\uA8E7', '\uA8E8', '\uA8E9', '\uA8E0', '\uA8EA', '\uA8EB',
            '\uA8EC', '\uA8EE', '\uA8EF', '\u030D', '\u0951', '\u0952',
            '\u0953', '\u0954', '\u0945'
        ]
        self.special_characters = [
            '\uf15c', '\uf193', '\uf130', '\uf1a3', '\uf1a2', '\uf195',
            '\uf185', '\u200d', '\u200c', '\u1CD6', '\u1CD5', '\u1CE1',
            '\u030E', '\u035B', '\u0324', '\u1CB5', '\u0331', '\u1CB6',
            '\u032B', '\u0308', '\u030D', '\u0942', '\uF512', '\uF693',
            '\uF576', '\uF11E', '\u1CD1', '\u093C', '\uF697', '\uF6AA',
            '\uF692', '\u200b',
        ]

    # ==========================
    # Getters & Setters (Validation)
    # ==========================

    @property
    def lex(self):
        return self._lex

    @lex.setter
    def lex(self, val):
        if val not in VALID_LEX:
            raise ValueError(f"Invalid lex: {val}")
        self._lex = val

    @property
    def input_encoding(self):
        return self._input_encoding

    @input_encoding.setter
    def input_encoding(self, value):
        if value not in VALID_IN_ENC:
            raise ValueError(
                f"Invalid input encoding '{value}'. "
                "Choices: {VALID_IN_ENC}"
            )
        self._input_encoding = value

    @property
    def output_encoding(self):
        return self._output_encoding

    @output_encoding.setter
    def output_encoding(self, value):
        # We allow 'DN', 'RN' broadly, mapping internally if needed
        if value not in MAP_OUT_ENC:
            raise ValueError(
                f"Invalid output encoding '{value}'. "
                "Use: {list(MAP_OUT_ENC.keys())}"
            )
        self._output_encoding = value

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, val):
        if val not in MAP_SEG_MODE:
            raise ValueError(
                f"Invalid mode: {val}. Use {list(MAP_SEG_MODE.keys())}"
            )
        self._mode = val

    @property
    def text_type(self):
        return self._text_type

    @text_type.setter
    def text_type(self, val):
        if val not in MAP_TEXT_MODE:
            raise ValueError(
                f"Invalid text_type: {val}. "
                "Use {list(MAP_TEXT_MODE.keys())}"
            )
        self._text_type = val

    @property
    def unsandhied(self):
        return self._unsandhied

    @unsandhied.setter
    def unsandhied(self, val):
        # 1. Handle actual Booleans
        if isinstance(val, bool):
            self._unsandhied = val
            return

        # 2. Handle Strings (case-insensitive)
        if isinstance(val, str):
            clean_val = val.strip().lower()
            if clean_val == "true":
                self._unsandhied = True
                return
            if clean_val == "false":
                self._unsandhied = False
                return

    @property
    def metrics(self):
        return self._metrics

    @metrics.setter
    def metrics(self, val):
        if val not in MAP_METRICS:
            raise ValueError(
                f"Invalid metrics: {val}. "
                "Use {list(MAP_METRICS.keys())}"
            )
        self._metrics = val

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, val):
        if not isinstance(val, int) or val <= 0:
            raise ValueError("Timeout must be a positive integer")
        if val > 300:
            raise ValueError("Max timeout is 300s")
        self._timeout = val

    # ==========================
    # Public API
    # ==========================

    def get_segmentation(self, input_text):
        """Wrapper for simple segmentation."""
        return self._run_pipeline(
            input_text, process="seg"
        )

    def get_morphological_analysis(self, input_text):
        """Wrapper for morphological analysis."""
        return self._run_pipeline(
            input_text, process="seg-morph"
        )

    def get_analysis(self, input_text):
        """Wrapper for segmentation and morphological analysis."""
        return self.get_morphological_analysis(input_text)

    # ==========================
    # Core Pipeline Logic
    # ==========================

    def _run_pipeline(self, input_text, process):
        """Orchestrates input cleaning, execution, and response parsing."""

        logger.debug(
            json.dumps(f"Orig text: {input_text}", ensure_ascii=False)
        )

        # 1. Clean and normalize input
        cleaned_text = self._handle_input(input_text.strip())

        logger.debug(
            json.dumps(f"Cleaned text: {cleaned_text}", ensure_ascii=False)
        )

        # 2. Transliterate to WX for the segmenter
        trans_input, trans_enc = self._input_transliteration(cleaned_text)

        # 3. Handle multiple sentences (split by .)
        # Note: Depending on input encoding,
        # splitting by "." might be risky if not WX/SLP.
        # Assuming trans_input is now WX or similar safe encoding.
        sub_sent_list = [
            item.strip()
            for item in trans_input.split(".")
            if item.strip()
        ]

        results = []

        source_label = "SH-Web" if self.use_web_fallback else "SH-Local"

        for sub_sent in sub_sent_list:
            # 4. Execution (Local or Web)
            if self.use_web_fallback:
                raw_result, status, error = self._execute_web_request(
                    sub_sent, trans_enc, process
                )
            else:
                raw_result, status, error = self._execute_cgi(
                    sub_sent, trans_enc, process
                )

            logger.debug(f"Raw Result: {raw_result}")

            # 5. Parse the specific sentence result
            processed = self._handle_result(
                sub_sent, raw_result, status, self.output_encoding,
                self.text_type, error, process, source_label
            )

            logger.debug(f"Processed Result: {processed}")

            results.append(processed)

        # 6. Merge results if multiple sentences
        if len(results) == 1:
            return results[0]
        else:
            return self._merge_sent_analyses(results, source_label)

    # -------------------------------------------------------------------------
    # Execution Method 1: Local Binary
    # -------------------------------------------------------------------------
    def _execute_cgi(self, text, current_enc, process):
        """Executes the binary using subprocess with the correct CWD."""

        env_vars, args = self._prepare_cgi_args(
            text, current_enc, process
        )

        logger.debug(f"Running Local Binary: {self.cgi_path}")
        logger.debug(f"CWD: {self.execution_cwd}")
        logger.debug(f"Query: {env_vars['QUERY_STRING']}")

        try:
            p = sp.Popen(
                [str(self.cgi_path)],
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                env=env_vars,
                cwd=str(self.execution_cwd)
            )

            outs, errs = p.communicate(timeout=self.timeout)

            if p.returncode != 0 and not outs:
                return "", "Failure", errs.decode('utf-8', errors='ignore')

            return outs.decode('utf-8', errors='replace'), "Success", ""

        except sp.TimeoutExpired:
            self._kill_process_tree(p.pid)
            return "", "Timeout", ""
        except Exception as e:
            return "", "Failure", str(e)

    def _kill_process_tree(self, pid):
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
        except psutil.NoSuchProcess:
            pass

    # -------------------------------------------------------------------------
    # Execution Method 2: Web Server Fallback (Requests)
    # -------------------------------------------------------------------------
    def _execute_web_request(self, text, current_enc, process):
        """Fetches results from the official INRIA server."""
        _, query_params = self._prepare_cgi_args(
            text, current_enc, process, as_dict=True
        )

        logger.debug(f"Requesting INRIA URL: {INRIA_URL}")
        try:
            response = requests.get(
                INRIA_URL, params=query_params, timeout=self.timeout
            )
            response.raise_for_status()

            # Passing 'pipeline=t' or 'stemmer=t' to INRIA's interface2.cgi
            # produces results in JSON, behaving similar to the binary
            return response.text, "Success", ""

        except requests.Timeout:
            return "", "Timeout", "Network request timed out"
        except requests.ConnectionError:
            return "", "Failure", "Network Connection Error (No Internet?)"
        except requests.HTTPError as e:
            return "", "Failure", f"HTTP Error: {e}"
        except Exception as e:
            return "", "Failure", str(e)

    def _prepare_cgi_args(self, text, current_enc, process, as_dict=False):
        """Shared logic to build query parameters."""

        if process == "seg":  # Segmentation
            cgi_process_key = "pipeline"
        else:  # Segmentation and Morphological Analysis
            cgi_process_key = "stemmer"

        # Font logic
        if self.output_encoding in ["DN", "RN"]:
            out_enc = self.output_encoding
        else:  # Falling back to Roman (IAST) in all other cases
            out_enc = "RN"

        params = {
            "lex": self.lex,
            "st": MAP_TEXT_MODE[self.text_type],
            "us": MAP_UNSANDHIED[self.unsandhied],
            "font": MAP_OUT_ENC[out_enc],
            "t": current_enc,
            "text": text,
            "mode": MAP_SEG_MODE[self.mode],
            "fmode": MAP_METRICS[self.metrics],
            cgi_process_key: "t"
        }

        if as_dict:
            return None, params

        # For Local CGI, we need a query string in ENV
        qs_parts = [f"{k}={v}" for k, v in params.items()]
        env_vars = os.environ.copy()
        env_vars["QUERY_STRING"] = "&".join(qs_parts)
        return env_vars, None

    # ==========================
    # Text Processing Helpers
    # ==========================

    def _handle_input(self, input_text):
        """Removes svaras and normalizes special characters."""

        new_text = [
            c for c in input_text
            if c not in self.svaras + self.special_characters
        ]
        modified_input = "".join(new_text)

        # Regex replacements
        modified_input = re.sub(
            r'[$@#%&*()\[\]=+:;"}{?/,\\]', ' ', modified_input
        )

        if self.input_encoding != "RN":
            modified_input = modified_input.replace("'", " ")

        # Chandrabindu logic
        if self.input_encoding == "DN":
            chandrabindu = "ꣳ"
            if modified_input.endswith(chandrabindu):
                modified_input = modified_input.replace(chandrabindu, "म्")
            else:
                modified_input = modified_input.replace(chandrabindu, "ं")

        modified_input = re.sub(r'M$', 'm', modified_input)
        modified_input = re.sub(r'\.m$', '.m', modified_input)
        return modified_input

    def _input_transliteration(self, input_text):
        """Converts input to WX."""
        trans_input = ""
        trans_enc = ""

        if self.input_encoding == "DN":
            trans_input = dt.slp2wx(dt.dev2slp(input_text))
            trans_input = trans_input.replace("ळ्", "d").replace("ळ", "d") \
                .replace("kdp", "kLp")
            trans_enc = "WX"
        elif self.input_encoding == "RN":
            trans_input = dt.slp2wx(dt.iast2slp(input_text))
            trans_enc = "WX"
        elif self.input_encoding == "SL":
            trans_input = dt.slp2wx(input_text)
            trans_enc = "WX"
        elif self.input_encoding == "VH":
            trans_input = dt.slp2wx(dt.vel2slp(input_text))
            trans_enc = "WX"
        else:
            trans_input = input_text
            trans_enc = self.input_encoding

        # Chandrabindu WX fix
        if "z" in trans_input:
            if trans_input.endswith("z"):
                trans_input = trans_input.replace("z", "m")
            else:
                trans_input = trans_input.replace("z", "M")

        return trans_input, trans_enc

    def _output_normalization(self, output_text, output_enc):
        output_text = output_text.replace("#", "?")
        return self._output_transliteration(output_text, output_enc)

    def _output_transliteration(self, output_text, output_enc):
        if output_enc == "DN":
            t = dt.slp2dev(dt.wx2slp(output_text))
            num_map = str.maketrans('०१२३४५६७८९', '0123456789')
            return t.translate(num_map), "DN"
        elif output_enc == "RN":
            return dt.slp2iast(dt.wx2slp(output_text)), "RN"
        else:
            return output_text, output_enc

    # ==========================
    # JSON Parsing & Logic
    # ==========================

    def _handle_result(self, input_str, result_raw, status, out_enc,
                       text_type, error, process, source_label):
        """Parses raw CGI output into structured dict."""

        final_status = "Failure"
        message = ""

        # Extract JSON from the raw output (usually the last line)
        result_json = {}
        if result_raw:
            try:
                lines = result_raw.strip().split("\n")
                if lines:
                    result_json = json.loads(lines[-1])
            except Exception:
                pass

        # Determine Segmentation status
        seg = list(dict.fromkeys(result_json.get("segmentation", [])))

        if status == "Success" and seg:
            first_seg = seg[0]
            if "error" in first_seg:
                final_status = "Error"
                message = first_seg

                # Check for wrong input cases
                INPUT_ERROR = [
                    "Wrong input",
                    "wrong input",
                    "Wrong character in input",
                    "Phantom preverb",
                    "Non consonant arg to homonasal"
                ]
                for err in INPUT_ERROR:
                    if err in message:
                        message = f"Please check Input: {message}"
            # Check for SHP unrecognized marker (?) or Failure (#)
            elif ("#" in seg[0] or "?" in seg[0]) and (
                text_type == "word" or " " not in seg[0]
            ):
                final_status = "Unrecognized"
                message = "SH could not recognize word"
            else:
                final_status = "Success"
        elif status == "Timeout":
            final_status = "Timeout"
            message = f"Response timeout ({self.timeout}s)"
        elif status == "Failure":
            final_status = "Error"
            message = error
        else:
            final_status = "Unknown Anomaly"
            message = f"Error: {error}"

        trans_input_display = self._output_normalization(input_str, out_enc)[0]

        logger.debug(f"Result JSON: {result_json}")
        logger.debug(f"Final status: {final_status}")

        if final_status == "Success":
            data = self._extract_final_result(
                trans_input_display, result_json, out_enc, process
            )
            # Inject source info
            data["source"] = source_label
            return data
        else:
            return {
                "input": trans_input_display,
                "status": final_status,
                "error": message,
                "source": source_label,
                "segmentation": [], "morph": []
            }

    def _extract_final_result(self, input_out_enc, result_json,
                              out_enc, process):
        """Constructs analayis json from the result json handling
           various scenarios
        """
        analysis_json = {
            "input": input_out_enc,
            "status": "Success"
        }

        seg = list(dict.fromkeys(result_json.get("segmentation", [])))
        segmentations = [
            self._output_normalization(s, out_enc)[0]
            for s in seg
        ]

        analysis_json["segmentation"] = segmentations

        if process == "seg-morph":
            morphs = result_json.get("morph", [])
            if morphs:
                new_morphs = []
                for m in morphs:
                    # Identify stems/roots
                    d_stem = m.get("derived_stem", "")
                    base = m.get("base", "")
                    d_morph = m.get("derivational_morph", "")
                    i_morphs = m.get("inflectional_morphs", [])

                    root, stem = self._identify_stem_root(
                        d_stem, base, d_morph, i_morphs
                    )

                    new_item = {
                        "word": self._output_normalization(
                            m.get("word", ""), out_enc
                        )[0],
                        "stem": self._output_transliteration(stem, out_enc)[0],
                        "root": self._output_transliteration(root, out_enc)[0],
                        "derivational_morph": d_morph,
                        "inflectional_morphs": i_morphs
                    }
                    new_morphs.append(new_item)
                analysis_json["morph"] = new_morphs
            else:
                analysis_json["status"] = "Failure"
                analysis_json["error"] = "Morph Unavailable"
        else:
            analysis_json["morph"] = []

        logger.debug(f"Analysis_json: {analysis_json}")

        return analysis_json

    def _identify_stem_root(self, d_stem, base, d_morph, i_morphs):
        """Heuristic to separate Root from Stem."""
        root = ""
        stem = ""

        verb_identifiers = [
            "pr.", "imp.", "opt.", "impft.", "inj.", "subj.", "pft.",
            "plp.", "fut.", "cond.", "aor.", "ben.", "abs.", "inf."
        ]
        noun_identifiers = [
            "nom.", "acc.", "i.", "dat.", "abl.", "g.", "loc.", "voc.",
            "iic.", "iiv.", "part.", "prep.", "conj.", "adv.", "tasil",
            "ind."
        ]

        if d_morph:
            root = base
            stem = d_stem
        else:
            # Simple heuristic since 'roots' module is currently unavailable
            morph_keys = " ".join(i_morphs).split(" ")
            for m in morph_keys:
                if m in verb_identifiers:
                    root = d_stem
                    break
                if m in noun_identifiers:
                    stem = d_stem
                    break
        return root, stem

    def _merge_sent_analyses(self, sub_sent_analysis_lst, source_label):
        """Combines multiple sentence results into one response."""
        full_stop = " । " if self.output_encoding == "DN" else " . "

        input_sent = []
        status_list = []
        all_segmentations = []
        morph = []
        errors = []

        for idx, item in enumerate(sub_sent_analysis_lst, 1):
            input_sent.append(item.get("input", ""))
            status_list.append(item.get("status", ""))
            all_segmentations.append(item.get("segmentation", []))
            morph.extend(item.get("morph", []))

            if item.get("error"):
                errors.append(f"Error in {idx}: {item.get('error')}")

        merged = {}
        merged["input"] = full_stop.join(input_sent)
        merged["status"] = (
            "Success" if "Success" in status_list
            else (status_list[0] if status_list else "Failure")
        )

        # Cartesian Product for combined segmentation
        if all_segmentations and all(all_segmentations):
            num_solutions = 1 if self.mode in ["s", "f", "first"] else 10
            merged["segmentation"] = [
                full_stop.join(comb)
                for comb in islice(product(*all_segmentations), num_solutions)
            ]
        else:
            merged["segmentation"] = []

        merged["morph"] = morph
        merged["error"] = "; ".join(errors)
        merged["source"] = source_label

        return merged
