"""Storage module for persisting ADsP exam question datasets to disk.

Provides:
- save_round_json(round_no, questions, output_dir="data"): writes individual exam round JSON files.
- save_consolidated_json(all_questions, output_dir="data"): writes consolidated dataset JSON file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from .validator import validate_consolidated_dataset, validate_round_dataset

logger = logging.getLogger(__name__)


def save_round_json(
    round_no: int,
    questions: List[Dict[str, Any]],
    output_dir: Union[str, Path] = "data",
) -> Path:
    """Persist an individual exam round's questions to disk as JSON.

    Validates schema and count before saving. Writes with UTF-8 encoding,
    2-space indentation, and ensure_ascii=False.

    Args:
        round_no: Exam round number (e.g. 50).
        questions: List of question dictionaries for this round.
        output_dir: Destination folder path (defaults to "data").

    Returns:
        Path: Path to the saved JSON file.

    Raises:
        ValidationError: If the questions fail round dataset validation.
        OSError: If file writing fails.
    """
    validate_round_dataset(round_no, questions)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    target_file = out_path / f"adsp_round_{round_no}.json"
    logger.info("Saving Round %d dataset to %s (%d questions)", round_no, target_file, len(questions))

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    return target_file


def save_consolidated_json(
    all_questions: Union[Dict[int, List[Dict[str, Any]]], List[Dict[str, Any]]],
    output_dir: Union[str, Path] = "data",
) -> Path:
    """Persist the consolidated 15-round dataset to disk as JSON.

    Validates schema, census counts (748 total), and negative integrity before saving.
    If a dictionary of rounds is provided, it is flattened into an ordered list with
    an added 'round' attribute per question. Writes with UTF-8 encoding,
    2-space indentation, and ensure_ascii=False.

    Args:
        all_questions: Dictionary mapping round_no -> list of questions,
                       or flat list of all 748 question dictionaries.
        output_dir: Destination folder path (defaults to "data").

    Returns:
        Path: Path to the saved adsp_all.json file.

    Raises:
        ValidationError: If the dataset fails consolidated validation.
        OSError: If file writing fails.
    """
    validate_consolidated_dataset(all_questions)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    target_file = out_path / "adsp_all.json"

    if isinstance(all_questions, dict):
        flattened: List[Dict[str, Any]] = []
        for r_no in sorted(all_questions.keys()):
            for q in all_questions[r_no]:
                q_item = dict(q)
                q_item["round"] = r_no
                flattened.append(q_item)
        data_to_write = flattened
    else:
        data_to_write = all_questions

    logger.info("Saving consolidated dataset to %s (%d questions)", target_file, len(data_to_write))

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data_to_write, f, ensure_ascii=False, indent=2)

    return target_file
