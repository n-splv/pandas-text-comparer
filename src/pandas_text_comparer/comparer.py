from __future__ import annotations

from difflib import SequenceMatcher
from itertools import islice
from typing import get_args, Literal, TypeAlias

import pandas as pd
import pandera as pa
from pandera.typing import DataFrame


DiffTag: TypeAlias = Literal["replace", "delete", "insert", "equal"]
OpCode: TypeAlias = tuple[DiffTag, int, int, int, int]
OpCodes: TypeAlias = list[OpCode]
SortOrder = Literal["asc", "desc"]


class ComparerResult(pa.DataFrameModel):
    """
    The result of comparison between two text columns.

    `ratio` - difflib.SequenceMatcher's metric of similarity between two texts;

    `column_a`, `column_b` - columns, containing the original and modified
    texts with some HTML code inserted into them. The names of these columns
    are not known in advance - they're set to be equal to the source dataset.
    """
    ratio: float
    column_a: str = pa.Field(alias="(?!ratio).+", regex=True)
    column_b: str = pa.Field(alias="(?!ratio).+", regex=True)

    @pa.dataframe_check
    def check_exactly_three_columns(cls, df: pd.DataFrame) -> bool:
        return df.shape[1] == 3

    class Config:
        ordered = True


class TextComparer:
    css_styles = """
    .add {background-color:#aaffaa}
    .chg {background-color:#ffff77}
    .sub {background-color:#ffaaaa}
    """

    def __init__(self,
                 df: pd.DataFrame,
                 column_a: str,
                 column_b: str,
                 min_ratio_for_highlight: float = 0.0):
        """
        Creates a comparer operating on the texts of the provided DataFrame.
        The next step should be running the comparison with `comparer.run()`

        :param df: A DataFrame containing the columns with texts to compare
        :param column_a: Name of the column with the 'original' texts
        :param column_b: Name of the column with the 'modified' texts
        :param min_ratio_for_highlight: Highlight edits in the texts that are
        at least `min_ratio` similar. For the definition of `ratio` see
        difflib.py
        """

        assert isinstance(df, pd.DataFrame)

        self._result_columns = ["ratio", column_a, column_b]
        self._df = df[[column_a, column_b]]
        self._min_ratio = min_ratio_for_highlight

        self.result: DataFrame[ComparerResult] | None = None

    def run(self) -> None:
        """
        Run the comparison, then save the edit ratios and the texts with
        inserted HTML code to `self.result`
        """
        if self.result is not None:
            return

        self.result = self._process_rows()
        self._df = None

    def get_html(self,
                 df: pd.DataFrame | pd.Series | None = None,
                 show_index: bool = True,
                 max_rows: int | None = 1000,
                 sort_by_ratio: SortOrder | None = None) -> str:
        """
        If a dataframe is passed, it gets merged with the comparer
        result. This allows for filtering rows and adding columns in
        the final HTML.
        """
        if df is not None:
            # Exclude original text cloumns from result
            df = df.to_frame() if isinstance(df, pd.Series) else df
            df = df.drop(
                columns=self._result_columns[1:],
                errors="ignore"
            )

        rows_html = self._get_rows_html(df, show_index, max_rows, sort_by_ratio)
        return self._get_full_html(df, rows_html, show_index)

    @classmethod
    @pa.check_input(ComparerResult.to_schema())
    def from_result(cls,
                    result: DataFrame[ComparerResult]) -> TextComparer:
        """
        Get a new redy-to-use comparer from the results of another one,
        which has already been run
        """
        comparer = cls.__new__(cls)
        comparer.result = result
        comparer._result_columns = result.columns.tolist()
        return comparer

    def _process_rows(self) -> DataFrame[ComparerResult]:

        # Try to use pandarallel or tqdm with fall back to the regular apply
        enhanced_apply_methods = ["parallel_apply", "progress_apply"]
        apply_method = self._df.apply
        for method in enhanced_apply_methods:
            if hasattr(self._df, method):
                apply_method = getattr(self._df, method)
                break

        result = apply_method(self._process_row, axis=1, result_type="expand")
        result.columns = self._result_columns
        return result

    def _process_row(self, row: pd.Series) -> tuple[float, str, str]:
        """
        Returns a similarity ratio and two HTML texts
        """
        text_a, text_b = row.tolist()
        opcodes, ratio = self._compare_strings(text_a, text_b)
        if ratio >= self._min_ratio:
            text_a, text_b = self._highlight_changes(text_a, text_b, opcodes)
        return ratio, text_a, text_b

    def _get_rows_html(self,
                       df: pd.DataFrame | None,
                       show_index: bool,
                       max_rows: int | None,
                       sort_by_ratio: SortOrder | None) -> str:

        html_df = self.result.copy()

        if df is not None:
            html_df = pd.merge(df, html_df, left_index=True, right_index=True)

        if sort_by_ratio in get_args(SortOrder):
            ascending = sort_by_ratio == "asc"
            html_df = html_df.sort_values(by="ratio", ascending=ascending)

        row_iterator = islice(html_df.itertuples(index=show_index), max_rows)
        rows_html = [self._row_to_html(row) for row in row_iterator]

        return "".join(rows_html)

    def _get_full_html(self,
                       df: pd.DataFrame | None,
                       rows_html: str,
                       show_index: bool) -> str:

        columns = ["#"] if show_index else []
        if df is not None:
            columns += df.columns.tolist()
        columns += self._result_columns

        table_header_row = "".join([f"<th> {col} </th>" for col in columns])
        table_head = "<thead>" + table_header_row + "</thead>"
        table_body = "<tbody>" + rows_html + "</tbody>"
        style_element = f"<style type='text/css'>{self.css_styles}</style>"

        html = f"""
        {style_element}
        <table>
            {table_head}
            {table_body}
        </table>
        """
        return html

    @staticmethod
    def _row_to_html(row: tuple) -> str:
        return "".join([
            "<tr>",
            *[f"<td> {text} </td>" for text in row],
            "</tr>",
        ])

    @staticmethod
    def _compare_strings(text_a: str,
                         text_b: str) -> tuple[OpCodes, float]:
        if text_a == text_b:
            return [], 1.0

        seq = SequenceMatcher(a=text_a, b=text_b, autojunk=False)
        # noinspection PyTypeChecker
        return seq.get_opcodes(), round(seq.ratio(), 2)

    @staticmethod
    def _highlight_changes(text_a: str,
                           text_b: str,
                           opcodes: OpCodes) -> tuple[str, str]:

        difftag_styles = {
            "replace": "<span class='chg'>",
            "delete": "<span class='sub'>",
            "insert": "<span class='add'>",
        }

        text_a, text_b = list(text_a), list(text_b)
        for opcode in reversed(opcodes):
            diff_tag, a1, a2, b1, b2 = opcode
            html_style = difftag_styles.get(diff_tag)
            if html_style is None:
                continue

            text_a = text_a[:a2] + ["</span>"] + text_a[a2:]
            text_a = text_a[:a1] + [html_style] + text_a[a1:]

            text_b = text_b[:b2] + ["</span>"] + text_b[b2:]
            text_b = text_b[:b1] + [html_style] + text_b[b1:]

        return "".join(text_a), "".join(text_b)
