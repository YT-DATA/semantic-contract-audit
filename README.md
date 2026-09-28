# Semantic Contract Audit

A small Python 3 standard-library CLI that compares **declared metric semantics**
before a change reaches a report or application. It flags changes for human review;
it does not decide whether the new definition is correct.

This is an original demonstration prepared with AI assistance. All example names,
formulas, and contracts are synthetic. It has no customer deployments, measured
business impact, or contest compliance claim. No data or code from an existing
workspace project was used. Released under the MIT license; see [LICENSE](LICENSE).

## Run locally

From this directory, with Python 3:

```sh
python3 -m unittest -v
python3 audit.py examples/before.json examples/after.json
python3 audit.py examples/before.json examples/before.json
```

Exit codes: `0` means no declared changes; `1` means review required; `2` means
invalid input, unreadable file, or CLI usage error. A code of `1` is an expected
result for the sample comparison. JSON reports go to stdout; input errors go to
stderr as JSON (argument-parser usage errors are plain text).

To save a report in a shell that stops on nonzero exit codes:

```sh
python3 audit.py examples/before.json examples/after.json > sample-report.json || test "$?" -eq 1
```

The included sample report has five findings: changed grain, currency, filter,
timezone, and join cardinality. Each finding includes the before and after values.

## Contract format and implemented behavior

The root contains `schema_version: 1` and a `metrics` object keyed by metric name.
Every metric requires these fields:

| Field | Meaning |
| --- | --- |
| `grain` | Nonempty, unique list of dimension names; order is insignificant |
| `unit` / `currency` | Declared measurement unit and currency; null currency is allowed except for unit `currency` |
| `aggregation` | One of sum, count, count_distinct, min, max, avg, custom |
| `expression` | Nonempty expression text |
| `filter` | Filter text; empty string means no declared filter |
| `timezone` | Nonempty timezone label |
| `joins` | Join names mapped to a cardinality and condition; may be empty |

Valid join cardinalities: `one_to_one`, `many_to_one`, `one_to_many`, `many_to_many`.
Metric additions/removals are reported separately. Unknown fields, missing fields,
duplicate JSON keys, duplicate grain dimensions, and invalid types are rejected.
Output keys and metric ordering are stable; there are no timestamps or network calls.

## Limits and potential next work

Expressions and filters are compared as exact text. Equivalent SQL with different
formatting is therefore flagged. This tool does not parse SQL, inspect database
data, validate timezone/currency catalogs, verify join cardinality, calculate
financial effects, or infer changes hidden outside the supplied contracts. Join
differences are reported as the full before/after join map. An unchanged report
does not prove that query results or business meaning are unchanged.

A future engagement could add adapters for a named semantic-layer format and
review rules grounded in actual customer requirements. Those adapters and any
commercial deliverables are not implemented here.

## Feedback

Open a GitHub issue with a small synthetic example to discuss a missing check or
adapter. Do not include credentials, personal information, or confidential business
data. The tool runs locally and does not send contract files anywhere.
