import csv
import hashlib
import json
import os
import random
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Tuple

from .models import Action
from .tasks import get_task

try:
    from datasets import load_dataset  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dataset = None

ALLOWED_REGIONS = ["North", "South", "East", "West"]
COLUMN_ALIASES = {
    "sales": "amount",
    "revenue": "amount",
    "sale_amount": "amount",
    "amount_usd": "amount",
    "date": "timestamp",
    "time": "timestamp",
    "sale_date": "timestamp",
    "id": "order_id",
}


def _fixture_rows(task_id: str) -> int:
    fixture_file = Path(__file__).resolve().parent / "fixtures" / f"{task_id}.json"
    if not fixture_file.exists():
        return 120
    data = json.loads(fixture_file.read_text(encoding="utf-8"))
    return int(data.get("rows", 120))


def _fixture_csv_file(task_id: str) -> Path:
    return Path(__file__).resolve().parent / "fixtures" / f"{task_id}.csv"


def _parse_amount(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        return text


def _load_dataset_from_csv(task_id: str) -> List[Dict[str, Any]] | None:
    csv_path = _fixture_csv_file(task_id)
    if not csv_path.exists():
        return None

    dataset: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            dataset.append(
                {
                    "order_id": (row.get("order_id") or "").strip() or None,
                    "amount": _parse_amount(row.get("amount")),
                    "region": (row.get("region") or "").strip() or None,
                    "timestamp": (row.get("timestamp") or "").strip() or None,
                }
            )
    return dataset


def _load_dataset_from_hf(name: str, split: str, limit: int, config: str | None = None) -> List[Dict[str, Any]] | None:
    if load_dataset is None:
        return None

    try:
        if config:
            dataset = load_dataset(name, config, split=split)
        else:
            dataset = load_dataset(name, split=split)
    except Exception:
        return None

    rows = []
    for idx, row in enumerate(dataset):
        if idx >= limit:
            break
        rows.append(dict(row))
    return rows or None


def _synthetic_order_id(row: Dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, default=str, ensure_ascii=True).encode("utf-8")
    digest = hashlib.sha1(payload).hexdigest()[:12]
    return f"HF-{digest}"


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text.replace(",", ""))
        except ValueError:
            return text
    return str(value)


def _canonicalize_hf_row(row: Dict[str, Any], index: int, column_map: Dict[str, tuple[str, ...]] | None = None) -> Dict[str, Any]:
    column_map = column_map or {}
    keys = list(row.keys())
    lowered = {key.lower(): key for key in keys}

    def pick_value(field_name: str, preferred_names: List[str], fallback_predicate) -> Any:
        for candidate_name in preferred_names:
            if candidate_name in lowered:
                value = row.get(lowered[candidate_name])
                if value not in (None, ""):
                    return value
        for key in keys:
            value = row.get(key)
            if fallback_predicate(key, value):
                return value
        return None

    order_id = pick_value(
        "order_id",
        list(column_map.get("order_id", ())) + ["order_id", "id", "passengerid", "customer_id", "customerid", "row_id", "index"],
        lambda key, value: key.lower().endswith("id") or key.lower() == "id",
    )
    amount = pick_value(
        "amount",
        list(column_map.get("amount", ())) + ["amount", "fare", "price", "income", "sales", "revenue", "salary", "balance", "capital-gain", "capital-loss", "hours-per-week"],
        lambda key, value: isinstance(value, (int, float)) or str(value).replace(".", "", 1).isdigit(),
    )
    region = pick_value(
        "region",
        list(column_map.get("region", ())) + ["region", "country", "state", "city", "embarked", "class", "workclass", "occupation", "category", "native-country", "job", "education"],
        lambda key, value: isinstance(value, str) and len(str(value)) <= 24,
    )
    timestamp = None
    for candidate_name in list(column_map.get("timestamp", ())) + ["timestamp", "date", "datetime", "order_date", "created_at", "time", "day", "month"]:
        if candidate_name not in lowered:
            continue
        value = row.get(lowered[candidate_name])
        if isinstance(value, datetime):
            timestamp = value.replace(microsecond=0).isoformat()
            break
        if isinstance(value, str) and len(value.strip()) >= 8:
            parsed = _parse_timestamp(value)
            if parsed is not None:
                timestamp = parsed
                break

    order_id = order_id if order_id not in (None, "") else _synthetic_order_id(row)
    amount = _coerce_scalar(amount)

    if timestamp in (None, ""):
        day = row.get("day")
        month = row.get("month")
        try:
            if day not in (None, "") and month not in (None, ""):
                month_text = str(month).strip()[:3].title()
                month_lookup = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
                }
                month_num = month_lookup.get(month_text)
                if month_num is not None:
                    timestamp = f"2024-{month_num:02d}-{int(day):02d}T12:00:00"
        except Exception:
            timestamp = None
    if timestamp in (None, ""):
        timestamp = f"2024-01-{(index % 28) + 1:02d}T12:00:00"

    if region in (None, ""):
        region = "North"

    return {
        "order_id": str(order_id),
        "amount": amount,
        "region": str(region),
        "timestamp": str(timestamp),
    }


def _load_real_dataset_rows(task_id: str, row_limit: int) -> List[Dict[str, Any]] | None:
    task = get_task(task_id)
    dataset_name = os.getenv("REAL_DATASET_NAME") or task.hf_dataset_name
    if not dataset_name:
        return None

    split = os.getenv("REAL_DATASET_SPLIT") or task.hf_dataset_split or "train"
    config = os.getenv("REAL_DATASET_CONFIG") or task.hf_dataset_config
    limit_raw = os.getenv("REAL_DATASET_LIMIT")
    limit = row_limit
    if limit_raw:
        try:
            limit = max(1, int(limit_raw))
        except ValueError:
            limit = row_limit

    raw_rows = _load_dataset_from_hf(dataset_name, split, limit, config)
    if raw_rows is None:
        return None

    return [_canonicalize_hf_row(row, idx, task.hf_column_map) for idx, row in enumerate(raw_rows)]


def _row_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        row.get("order_id"),
        row.get("amount"),
        row.get("region"),
        row.get("timestamp"),
    )


def _canonical_region(value: Any) -> str:
    if value is None:
        return "North"
    text = str(value).strip().lower()
    mapping = {
        "n": "North",
        "north": "North",
        "north-east": "North",
        "c": "East",
        "e": "East",
        "east": "East",
        "s": "South",
        "south": "South",
        "w": "West",
        "west": "West",
        "q": "West",
    }
    if text in mapping:
        return mapping[text]
    buckets = ["North", "South", "East", "West"]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return buckets[int(digest[:8], 16) % len(buckets)]


def build_task_dataset(task_id: str, initial_quality_report: Dict[str, int]) -> List[Dict[str, Any]]:
    real_rows = _load_real_dataset_rows(task_id, max(200, _fixture_rows(task_id)))
    if real_rows is not None:
        return real_rows

    file_dataset = _load_dataset_from_csv(task_id)
    if file_dataset is not None:
        return file_dataset

    rng = random.Random(f"dq::{task_id}")
    rows = _fixture_rows(task_id)

    dataset: List[Dict[str, Any]] = []
    for i in range(rows):
        dataset.append(
            {
                "order_id": f"ORD-{i:06d}",
                "amount": round(75 + ((i * 17) % 400) + rng.uniform(-4.0, 4.0), 2),
                "region": ALLOWED_REGIONS[i % len(ALLOWED_REGIONS)],
                "timestamp": f"2024-01-{(i % 28) + 1:02d}T12:00:00",
            }
        )

    indexes = list(range(rows))
    rng.shuffle(indexes)
    cursor = 0

    duplicate_count = int(initial_quality_report.get("duplicates", 0))
    for i in range(duplicate_count):
        if cursor + 1 >= len(indexes):
            break
        source_idx = indexes[cursor]
        target_idx = indexes[cursor + 1]
        dataset[target_idx] = deepcopy(dataset[source_idx])
        cursor += 2

    missing_count = int(initial_quality_report.get("missing_values", 0))
    missing_columns = ["amount", "region", "timestamp", "order_id"]
    for i in range(missing_count):
        row_idx = indexes[(cursor + i) % len(indexes)]
        col = missing_columns[i % len(missing_columns)]
        dataset[row_idx][col] = None
    cursor += missing_count

    invalid_count = int(initial_quality_report.get("invalid_types", 0))
    for i in range(invalid_count):
        row_idx = indexes[(cursor + i) % len(indexes)]
        if i % 2 == 0:
            dataset[row_idx]["amount"] = "bad-number"
        else:
            dataset[row_idx]["timestamp"] = "not-a-timestamp"
    cursor += invalid_count

    category_count = int(initial_quality_report.get("category_inconsistency", 0))
    bad_categories = ["NORTHH", "south-zone", "unknown", "EAST_1"]
    for i in range(category_count):
        row_idx = indexes[(cursor + i) % len(indexes)]
        dataset[row_idx]["region"] = bad_categories[i % len(bad_categories)]
    cursor += category_count

    outlier_count = int(initial_quality_report.get("outliers", 0))
    for i in range(outlier_count):
        row_idx = indexes[(cursor + i) % len(indexes)]
        dataset[row_idx]["amount"] = 50000.0 + float(i)

    return dataset


def _parse_timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(microsecond=0).isoformat()
    except ValueError:
        return None


def compute_quality_report(dataset: List[Dict[str, Any]]) -> Dict[str, int]:
    missing_values = 0
    invalid_types = 0
    category_inconsistency = 0
    outliers = 0

    seen = set()
    duplicates = 0
    for row in dataset:
        for col in ("order_id", "amount", "region", "timestamp"):
            if row.get(col) in (None, ""):
                missing_values += 1

        amount = row.get("amount")
        if amount not in (None, ""):
            if not isinstance(amount, (int, float)):
                invalid_types += 1
            elif float(amount) > 5000.0:
                outliers += 1

        ts = row.get("timestamp")
        if ts not in (None, "") and _parse_timestamp(ts) is None:
            invalid_types += 1

        region = row.get("region")
        if region not in (None, "") and str(region) not in ALLOWED_REGIONS:
            category_inconsistency += 1

        key = _row_key(row)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)

    return {
        "missing_values": missing_values,
        "duplicates": duplicates,
        "invalid_types": invalid_types,
        "category_inconsistency": category_inconsistency,
        "outliers": outliers,
    }


def _resolve_columns(target_columns: List[str]) -> List[str]:
    if not target_columns or "*" in target_columns:
        return ["order_id", "amount", "region", "timestamp"]
    resolved: List[str] = []
    for col in target_columns:
        normalized = COLUMN_ALIASES.get(col, col)
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def apply_action(dataset: List[Dict[str, Any]], action: Action) -> List[Dict[str, Any]]:
    updated = deepcopy(dataset)
    columns = _resolve_columns(list(action.target_columns))

    if action.operation == "clean_missing":
        numeric_values = [float(row["amount"]) for row in updated if isinstance(row.get("amount"), (int, float))]
        fill_amount = round(float(median(numeric_values)), 2) if numeric_values else 0.0
        fill_region = "North"
        fill_timestamp = "2024-01-01T12:00:00"
        for idx, row in enumerate(updated):
            if "order_id" in columns and row.get("order_id") in (None, ""):
                row["order_id"] = f"FILL-{idx:06d}"
            if "amount" in columns and row.get("amount") in (None, ""):
                row["amount"] = fill_amount
            if "region" in columns and row.get("region") in (None, ""):
                row["region"] = fill_region
            if "timestamp" in columns and row.get("timestamp") in (None, ""):
                row["timestamp"] = fill_timestamp

    elif action.operation == "deduplicate":
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for row in updated:
            key = _row_key(row)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        updated = deduped

    elif action.operation == "cast_type":
        for row in updated:
            if "amount" in columns and not isinstance(row.get("amount"), (int, float)):
                try:
                    row["amount"] = float(str(row.get("amount")).replace(",", "").strip())
                except (TypeError, ValueError):
                    row["amount"] = 0.0
            if "timestamp" in columns:
                parsed = _parse_timestamp(row.get("timestamp"))
                if parsed is not None:
                    row["timestamp"] = parsed

    elif action.operation == "normalize_categories":
        if "region" in columns:
            for row in updated:
                row["region"] = _canonical_region(row.get("region"))

    elif action.operation == "cap_outliers":
        if "amount" in columns:
            for row in updated:
                amount = row.get("amount")
                if isinstance(amount, (int, float)) and float(amount) > 5000.0:
                    row["amount"] = 5000.0

    return updated


def quality_score(quality_report: Dict[str, int]) -> float:
    total_issues = sum(max(0, v) for v in quality_report.values())
    # Keep the quality score strictly inside (0, 1) for validator compatibility.
    raw_score = 1.0 / (1.0 + float(total_issues))
    epsilon = 0.001
    return max(epsilon, min(1.0 - epsilon, raw_score))


def validate_task_constraints(dataset: List[Dict[str, Any]], constraints: Dict[str, Any]) -> bool:
    required_columns = list(constraints.get("required_columns", []))
    allowed_regions = set(constraints.get("allowed_regions", ALLOWED_REGIONS))
    amount_min = float(constraints.get("amount_min", 0.0))
    amount_max = float(constraints.get("amount_max", 5000.0))
    require_unique_order_id = bool(constraints.get("require_unique_order_id", False))
    require_valid_timestamps = bool(constraints.get("require_valid_timestamps", True))

    for row in dataset:
        for column in required_columns:
            if row.get(column) in (None, ""):
                return False

        amount = row.get("amount")
        if amount is not None:
            if not isinstance(amount, (int, float)):
                return False
            if float(amount) < amount_min or float(amount) > amount_max:
                return False

        region = row.get("region")
        if region not in (None, "") and str(region) not in allowed_regions:
            return False

        timestamp = row.get("timestamp")
        if require_valid_timestamps and timestamp not in (None, "") and _parse_timestamp(timestamp) is None:
            return False

    if require_unique_order_id:
        seen = set()
        for row in dataset:
            order_id = row.get("order_id")
            if order_id in seen:
                return False
            seen.add(order_id)

    return True
