# CSV Type Inferrer

Scans CSV text and reports a per-column inferred type (`boolean`, `int`, `float`, `date`, or `string`).

## Usage

```python
from csv_type_inferrer import infer_types, infer_row_type, ColumnTypes

csv_text = "id,active,price\n1,true,1.5\n2,false,2.5\n"
print(infer_types(csv_text))
# {'id': 'int', 'active': 'boolean', 'price': 'float'}

print(infer_row_type(["1", "2", "3"]))      # 'int'
print(infer_row_type(["true", "false"]))     # 'boolean'
```

## Why

The standard library has no type-inference helper, and the ones you reach for (`pandas.read_csv`'s dtype inference) bring a large dependency graph. This library gives you a single function, `infer_types(csv_text) -> dict[str, str]`, that returns the type name for each column. It is intentionally narrow: it reports one type per column, not per cell, and it is strict — a single stray value demotes the whole column to `string`.

## Edge cases you will hit

- **`0` and `1` are treated as `boolean`, not `int`.** This is the one ambiguous shape in real CSVs. If a column mixes explicit ints (`2`, `3`) with `0`/`1`, the ints win and the column reports `int`.
- **Empty cells are skipped**, so `1,,2` still infers as `int`. An all-empty column reports `string`.
- **`inf`, `-inf`, and `nan` are `float`**, following Python's `float()`.
- **Dates are `YYYY-MM-DD` only**, and only month/day ranges are checked — `2020-02-30` is accepted, `2020-13-01` is not.

Standard library only. No third-party dependencies.
