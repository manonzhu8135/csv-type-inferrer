"""Tests for csv_type_inferrer.core."""

import unittest

from csv_type_inferrer import infer_types, infer_row_type, ColumnTypes


class TestColumnTypes(unittest.TestCase):
    def test_constants_are_strings(self):
        self.assertEqual(ColumnTypes.BOOLEAN, "boolean")
        self.assertEqual(ColumnTypes.INT, "int")
        self.assertEqual(ColumnTypes.FLOAT, "float")
        self.assertEqual(ColumnTypes.DATE, "date")
        self.assertEqual(ColumnTypes.STRING, "string")


class TestInferRowType(unittest.TestCase):
    def test_all_int(self):
        self.assertEqual(infer_row_type(["2", "3", "4"]), ColumnTypes.INT)

    def test_all_boolean_words(self):
        self.assertEqual(infer_row_type(["true", "false"]), ColumnTypes.BOOLEAN)

    def test_mixed_int_and_float_is_string(self):
        # 1 is boolean-shaped, 2.5 is float-shaped: they don't agree
        self.assertEqual(infer_row_type(["1", "2.5"]), ColumnTypes.STRING)

    def test_all_floats(self):
        self.assertEqual(infer_row_type(["1.5", "2.5"]), ColumnTypes.FLOAT)

    def test_empty_row_is_string(self):
        self.assertEqual(infer_row_type(["", "", ""]), ColumnTypes.STRING)

    def test_row_with_dates(self):
        self.assertEqual(
            infer_row_type(["2020-01-01", "2021-12-31"]),
            ColumnTypes.DATE,
        )


class TestInferTypes(unittest.TestCase):
    def test_mixed_columns(self):
        csv_text = (
            "id,active,price,name,when\n"
            "1,true,1.5,alice,2020-01-01\n"
            "2,false,2.5,bob,2021-12-31\n"
        )
        result = infer_types(csv_text)
        self.assertEqual(result["id"], ColumnTypes.INT)
        self.assertEqual(result["active"], ColumnTypes.BOOLEAN)
        self.assertEqual(result["price"], ColumnTypes.FLOAT)
        self.assertEqual(result["name"], ColumnTypes.STRING)
        self.assertEqual(result["when"], ColumnTypes.DATE)

    def test_one_bad_value_demotes_column(self):
        csv_text = (
            "col\n"
            "1\n"
            "2\n"
            "oops\n"
            "3\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.STRING)

    def test_empty_values_skipped(self):
        csv_text = (
            "col\n"
            "2\n"
            "\n"
            "3\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.INT)

    def test_all_empty_column_is_string(self):
        csv_text = (
            "col\n"
            "\n"
            "\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.STRING)

    def test_no_header(self):
        csv_text = (
            "2,true\n"
            "3,false\n"
        )
        result = infer_types(csv_text, has_header=False)
        self.assertEqual(result["col_0"], ColumnTypes.INT)
        self.assertEqual(result["col_1"], ColumnTypes.BOOLEAN)

    def test_custom_delimiter(self):
        csv_text = (
            "a;b\n"
            "2;3\n"
            "4;5\n"
        )
        result = infer_types(csv_text, delimiter=";")
        self.assertEqual(result["a"], ColumnTypes.INT)
        self.assertEqual(result["b"], ColumnTypes.INT)

    def test_header_only_returns_empty(self):
        self.assertEqual(infer_types("a,b,c\n"), {})

    def test_empty_input_returns_empty(self):
        self.assertEqual(infer_types(""), {})

    def test_zero_and_one_are_boolean(self):
        csv_text = (
            "flag\n"
            "0\n"
            "1\n"
        )
        self.assertEqual(infer_types(csv_text)["flag"], ColumnTypes.BOOLEAN)

    def test_int_then_zero_keeps_int(self):
        # Column has explicit ints 2 and 3 plus a 0/1-shaped value: int context wins.
        csv_text = (
            "col\n"
            "2\n"
            "3\n"
            "0\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.INT)

    def test_signed_integers(self):
        csv_text = (
            "col\n"
            "+10\n"
            "-20\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.INT)

    def test_scientific_notation_is_float(self):
        csv_text = (
            "col\n"
            "1e3\n"
            "2.5e-2\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.FLOAT)

    def test_inf_and_nan_are_float(self):
        csv_text = (
            "col\n"
            "inf\n"
            "-inf\n"
            "nan\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.FLOAT)

    def test_yes_no_booleans(self):
        csv_text = (
            "col\n"
            "yes\n"
            "no\n"
            "YES\n"
            "NO\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.BOOLEAN)

    def test_whitespace_is_stripped(self):
        csv_text = (
            "col\n"
            "  2  \n"
            " 3 \n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.INT)

    def test_date_column(self):
        csv_text = (
            "col\n"
            "2020-01-01\n"
            "1999-12-31\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.DATE)

    def test_bad_date_is_string(self):
        csv_text = (
            "col\n"
            "2020-13-01\n"
        )
        self.assertEqual(infer_types(csv_text)["col"], ColumnTypes.STRING)

    def test_ragged_rows(self):
        # Row 2 is short; the missing cell is treated as empty and skipped.
        csv_text = (
            "a,b\n"
            "2,3\n"
            "4\n"
        )
        result = infer_types(csv_text)
        self.assertEqual(result["a"], ColumnTypes.INT)
        self.assertEqual(result["b"], ColumnTypes.INT)


if __name__ == "__main__":
    unittest.main()
