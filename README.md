<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo.dark.png" width="300">
  <source media="(prefers-color-scheme: light)" srcset="docs/images/logo.light.png" width="300">
  <img alt="logo" src="https://github.com/n-splv/pandas-text-comparer/raw/main/docs/images/logo.light.png" width="300">
</picture>

A library designed to compare texts within a pandas DataFrame, highlighting 
changes and computing similarity ratios. It utilizes [difflib.SequenceMatcher](https://docs.python.org/3/library/difflib.html) to 
perform detailed comparisons and generate results that can be easily interpreted
and displayed in HTML format.

# Features
- HTML Output: Generate an HTML representation of the comparison results, which highlights `additions`, `deletions`, and `modifications` in the text.
- Similarity Assessment: Compute a similarity ratio for each pair of compared texts, allowing quick assessment of text changes.
- Flexible Integration: Designed to work directly with pandas DataFrames, making it easy to integrate into existing data processing pipelines.

# Usage
Installation:
```
pip install pandas-text-comparer
```
Necessary imports:
```python
from IPython import display
import pandas as pd
from pandas_text_comparer import TextComparer
```
Nice-to-haves (not required). Read more [here](https://github.com/nalepae/pandarallel) and [here](https://github.com/tqdm/tqdm)
```python
from pandarallel import pandarallel  # multi-core processing
from tqdm.auto import tqdm  # progress bar

tqdm.pandas()
pandarallel.initialize(progress_bar=True)
```
## 1. Running the comparison
Specify the names of your columns and run the computation.
```python
# A toy dataset. Replace with your data
df = pd.read_csv("https://github.com/n-splv/pandas-text-comparer/raw/main/data/demo/review-responses.csv.gz")

comparer = TextComparer(df, column_a="llm_response", column_b="human_response")
comparer.run()
```

## 2. Exploring the differences
Generate an HTML table. It can be viewed with `IPython.display` in Jupyter. 
Alternatively, you can write it to a file and open in any web browser.  
```python
html = comparer.get_html()
display.HTML(html)
```

## 3. Sorting by the severity of edits
Sort the result by `ratio` - difflib.SequenceMatcher's metric of similarity between two texts, on the scale from 0 to 1. Higher values mean
that the texts are more similar.
```python
html = comparer.get_html(sort_by_ratio="desc")  # or "asc"
```

## 4. Adding columns to the view
Add any columns from the original data to the HTML by simply passing a slice of
the DataFrame to `get_html` method.
```python
columns = ["review_id", "company_name"]
html = comparer.get_html(df[columns])
```
## 5. Filtering rows to display
When you provide a DataFrame as an argument to `get_html`, its index is also used to 
filter the rows for the result. 
```python
filt = df.company_name == "FitFusion"
html = comparer.get_html(df[filt])
```

## 6. Saving and loading the results