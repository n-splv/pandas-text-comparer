from difflib import SequenceMatcher
from typing import get_args, Literal, TypeAlias

import pandas as pd
import pandera as pa
from pandera.typing import DataFrame


DiffTag: TypeAlias = Literal["replace", "delete", "insert", "equal"]
OpCode: TypeAlias = tuple[DiffTag, int, int, int, int]
OpCodes: TypeAlias = list[OpCode]
SortOrder = Literal["asc", "desc"]


class ComparerResult(pa.DataFrameModel):
    ratio: float
    row_html: str


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

        assert isinstance(df, pd.DataFrame)

        self._df = df
        self._column_names = df.columns.tolist()
        self._column_a = column_a
        self._column_b = column_b
        self._min_ratio = min_ratio_for_highlight

        self.result: DataFrame[ComparerResult] | None = None

    def run(self) -> None:
        if self._df is None:
            err_message = "The comparer has already been run"
            raise ValueError(err_message)

        self.result = self._process_rows()
        self._df = None

    def get_html(self,
                 df: pd.DataFrame | None = None,
                 max_rows: int | None = 1000,
                 sort_by_ratio: SortOrder | None = None) -> str:
        """
        If a dataframe is passed, its index is used to select the
        rows to display
        """
        rows_html = self._get_rows_html(df, max_rows, sort_by_ratio)
        return self._get_full_html(rows_html)

    def _process_rows(self) -> DataFrame[ComparerResult]:

        # Try to use pandarallel or tqdm with fall back to the regular apply
        enhanced_apply_methods = ["parallel_apply", "progress_apply"]
        apply_method = self._df.apply
        for method in enhanced_apply_methods:
            if hasattr(self._df, method):
                apply_method = getattr(self._df, method)
                break

        result = apply_method(self._process_row, axis=1, result_type="expand")
        result.columns = ["ratio", "row_html"]
        return result

    def _process_row(self, row: pd.Series) -> tuple[float, str]:
        """
        Returns a similarity ratio and an HTML text
        """
        row_html = ["<tr>"]
        text_a = row[self._column_a]
        text_b = row[self._column_b]
        opcodes, ratio = self._compare_strings(text_a, text_b)
        if ratio >= self._min_ratio:
            text_a, text_b = self._highlight_changes(text_a, text_b, opcodes)

        for column in self._column_names:
            if column == self._column_a:
                text = text_a
            elif column == self._column_b:
                text = text_b
            else:
                text = row[column]
            row_html.append(f"<td> {text} </td>")

        # Add column with ratio values
        row_html.append(f"<td> {ratio:.2f} </td>")

        row_html.append("</tr>")

        return ratio, "".join(row_html)

    def _get_full_html(self, rows_html: str) -> str:

        columns = self._column_names + ["ratio"]
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

    def _get_rows_html(self,
                       df: pd.DataFrame | None,
                       max_rows: int | None,
                       sort_by_ratio: SortOrder | None) -> str:

        html_df = self.result.copy()

        if df is not None:
            html_df = html_df.loc[df.index.tolist()]

        if sort_by_ratio in get_args(SortOrder):
            ascending = sort_by_ratio == "asc"
            html_df = html_df.sort_values(by="ratio", ascending=ascending)

        row_htmls = html_df["row_html"].tolist()[slice(max_rows)]
        return "".join(row_htmls)

    @staticmethod
    def _compare_strings(text_a: str,
                         text_b: str) -> tuple[OpCodes, float]:
        if text_a == text_b:
            return [], 1.0

        seq = SequenceMatcher(a=text_a, b=text_b, autojunk=False)
        # noinspection PyTypeChecker
        return seq.get_opcodes(), seq.ratio()

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
