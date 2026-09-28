#!/usr/bin/env python3
"""Compare declared metric semantics; no database access or SQL execution."""
import argparse
import json
import sys
from pathlib import Path

FIELDS = ("grain", "unit", "currency", "aggregation", "expression", "filter", "timezone", "joins")
AGGREGATIONS = {"sum", "count", "count_distinct", "min", "max", "avg", "custom"}
CARDINALITIES = {"one_to_one", "many_to_one", "one_to_many", "many_to_many"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(contract):
    """Reject unknown/missing fields so unsupported semantics cannot disappear silently."""
    require(isinstance(contract, dict), "contract must be an object")
    require(set(contract) == {"schema_version", "metrics"}, "expected schema_version and metrics only")
    require(type(contract["schema_version"]) is int and contract["schema_version"] == 1,
            "schema_version must be integer 1")
    metrics = contract["metrics"]
    require(isinstance(metrics, dict), "metrics must be an object keyed by metric name")
    for name, metric in metrics.items():
        require(nonempty(name), "metric names must be nonempty strings")
        require(isinstance(metric, dict) and set(metric) == set(FIELDS),
                f"{name}: expected fields {', '.join(FIELDS)}")
        grain = metric["grain"]
        require(isinstance(grain, list) and grain and all(nonempty(x) for x in grain),
                f"{name}.grain must be a nonempty list of strings")
        require(len(set(grain)) == len(grain), f"{name}.grain must not contain duplicates")
        for field in ("unit", "aggregation", "expression", "timezone"):
            require(nonempty(metric[field]), f"{name}.{field} must be a nonempty string")
        require(metric["aggregation"] in AGGREGATIONS, f"{name}.aggregation is unsupported")
        require(isinstance(metric["filter"], str), f"{name}.filter must be a string")
        require(metric["currency"] is None or nonempty(metric["currency"]),
                f"{name}.currency must be a nonempty string or null")
        require(metric["unit"] != "currency" or nonempty(metric["currency"]),
                f"{name}.currency is required when unit is currency")
        require(isinstance(metric["joins"], dict), f"{name}.joins must be an object")
        for join_name, join in metric["joins"].items():
            require(nonempty(join_name), f"{name}: join names must be nonempty strings")
            require(isinstance(join, dict) and set(join) == {"cardinality", "condition"},
                    f"{name}.{join_name}: expected cardinality and condition")
            require(nonempty(join["cardinality"]) and join["cardinality"] in CARDINALITIES,
                    f"{name}.{join_name}: unsupported cardinality")
            require(nonempty(join["condition"]), f"{name}.{join_name}: condition is required")
    return contract


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def load(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8"),
                               object_pairs_hook=reject_duplicates,
                               parse_constant=reject_constant))


def compare(before, after):
    left, right = validate(before)["metrics"], validate(after)["metrics"]
    changes = []
    for name in sorted(left.keys() | right.keys()):
        if name not in left or name not in right:
            changes.append({"metric": name, "field": "$metric",
                            "kind": "added" if name in right else "removed",
                            "before": left.get(name), "after": right.get(name)})
            continue
        for field in FIELDS:
            old, new = left[name][field], right[name][field]
            # Grain is a set of dimensions; expression/filter text remains exact.
            old, new = (sorted(old), sorted(new)) if field == "grain" else (old, new)
            if old != new:
                changes.append({"metric": name, "field": field, "kind": "changed",
                                "before": old, "after": new})
    return {"schema_version": 1, "status": "review_required" if changes else "unchanged",
            "change_count": len(changes), "changes": changes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", help="baseline contract JSON")
    parser.add_argument("after", help="candidate contract JSON")
    args = parser.parse_args()
    try:
        result = compare(load(args.before), load(args.after))
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 1 if result["changes"] else 0


if __name__ == "__main__":
    sys.exit(main())
