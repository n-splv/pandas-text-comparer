<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo.dark.png" width="400">
  <source media="(prefers-color-scheme: light)" srcset="docs/images/logo.light.png" width="400">
  <img alt="logo" src="https://github.com/n-splv/pandas-text-comparer/raw/main/docs/images/logo.light.png" width="400">
</picture>

A library designed to compare texts within a pandas DataFrame, highlighting 
changes and computing similarity ratios. It utilizes [difflib.SequenceMatcher](https://docs.python.org/3/library/difflib.html) to 
perform detailed comparisons and generate results that can be easily interpreted
and displayed in HTML format.

# Features
[Medium.com - How to compare texts in Pandas](https://medium.com/@n_splv/6ee832629145?source=readme)
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
## 1. Run the comparison
Specify the names of your columns and run the computation.
```python
# A toy GPT-4 generated dataset. Replace with your data
df = pd.read_csv("https://github.com/n-splv/pandas-text-comparer/raw/main/data/demo/review-responses.csv.gz")

comparer = TextComparer(df, column_a="llm_response", column_b="human_response")
comparer.run()
```

## 2. Explore the difference
Generate an HTML table. It can be viewed with `IPython.display` in Jupyter. 
Alternatively, you can write it to a file and open in any web browser.  
```python
html = comparer.get_html()
display.HTML(html)
```
<img alt="html-table-example" src="https://github.com/n-splv/pandas-text-comparer/raw/main/docs/images/html-table-example.png">

## 3. Sort by the severity of edits
Sort the result by `ratio` - difflib.SequenceMatcher's metric of similarity between two texts, on the scale from 0 to 1. Higher values mean
that the texts are more similar.
```python
html = comparer.get_html(sort_by_ratio="desc")  # or "asc"
```

## 4. Add columns to the view
Add any columns from the original data to the HTML by simply passing a slice of
the DataFrame to `get_html` method.
```python
columns = ["review_id", "company_name"]
html = comparer.get_html(df[columns])
```
## 5. Filter rows to display
When you provide any pandas object with an index (i.e. pd.DataFrame, pd.Series or pd.Indes) as an argument to `get_html`, 
it is also used to filter the rows. 
```python
filt = df.company_name == "FitFusion"

# Filter rows & add columns
html = comparer.get_html(df[filt])

# Just filter rows
html = comparer.get_html(df[filt].index)
```

## 6. Save and load the results
A comparer stores its results in a DataFrame - `comparer.result`. This data can be persisted and used later on to create
a new comparer. This way, you avoid the re-computation:
```python
result_filepath = "data/comparer_result.csv"
comparer.result.to_csv(result_filepath)

# Don't forget to specify the index column
loaded_result = pd.read_csv(result_filepath, index_col=0)
new_comparer = TextComparer.from_result(loaded_result)
```
Also, if you need to further process your data based on the computed similarities of texts, just grab this column from the result:
```python
df["similarity_ratio"] = comparer.result.ratio
```
