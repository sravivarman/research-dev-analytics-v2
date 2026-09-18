# Faculty Publication Analytics Dashboard

A local, offline-capable Streamlit dashboard for engineering-college publication workbooks. It reads the original `.xlsx` file from the web interface, including rich-text bold author formatting, and never modifies the source workbook.

## First-time setup (Windows)

1. Install **Python 3.11 or newer** from [python.org](https://www.python.org/downloads/). During installation, enable **Add Python to PATH**.
2. Double-click `run_dashboard.bat` in this folder.
3. The first run creates a private `.venv` folder and installs the required packages. Internet access is needed only for this installation step.
4. The dashboard opens in your default browser.

If Windows SmartScreen asks for confirmation, choose **More info → Run anyway** only if you obtained this folder from a trusted source.

## Daily usage

1. Double-click `run_dashboard.bat`.
2. Wait for the browser to open.
3. Click **Browse files** under **Upload Publication Workbook** and choose `Publications.xlsx` (or a newer workbook).
4. Use the navigation and global filters in the left sidebar.
5. Use **Replace Workbook** to load a newer file without changing code.
6. When finished, close the browser tab, return to the black command window, and press **Ctrl+C**. Confirm with `Y` if Windows asks.

## Workbook behavior

- Recognized publication sheets are `Journal`, `Conf`/`Conference`, `Chapter`, and `Books`; missing sheets generate warnings but do not stop processing. An optional `Patents` sheet is detected separately.
- Journal and conference records are credited to the **first bold author in reading order**. Later bold authors in the same cell receive no credit for that row.
- Patent records use a different rule: **every bold faculty applicant receives a faculty patent credit**. A joint patent still counts once in institutional patent totals.
- A cell with no bold text is accepted only when it clearly contains one author. Other cases are labeled `UNMAPPED / REVIEW REQUIRED`.
- SCI/SCIE, ESCI, and Scopus are independent flags. Explicit `Non Scopus` is never counted as Scopus.
- Duplicate candidates distinguish strong matches from rows requiring review. Incomplete DOI prefixes and common document URLs are not sufficient duplicate evidence.
- Rows are never removed automatically. Duplicate include/exclude decisions are stored in `config/duplicate_review.json` and take effect only when the corresponding dashboard filter is selected.
- User-approved author mappings are stored in `config/author_mapping.json`; manual row-level resolutions are stored in `config/unmapped_resolutions.json`. All survive restarts without altering the workbook.
- Manual multi-faculty patent resolutions are stored in `config/patent_attribution_resolutions.json`; patent duplicate decisions are stored separately in `config/patent_duplicate_review.json`.

## Dashboard pages

- **Overview** — row-based KPIs, year/type output, faculty contribution, quartile distribution, and independent indexing trends.
- **Patents** — distinct institutional patent totals, publication/grant trends, faculty credits, patent types, filters, details, and exports.
- **Faculty Profile** — faculty KPIs, year trends, journal quality, complete publication records, and CSV/Excel exports.
- **Journal Quality** — quartile, indexing, Q1+Q2 ranking, and impact-factor analysis.
- **Year Analysis** — selected-year KPIs, faculty ranking, cross-year comparison, and a Faculty × Year matrix.
- **Publication Details** — searchable normalized records with CSV/Excel exports and source traceability.
- **Data Quality** — unmapped authors, no-bold fallbacks, classified duplicate candidates, explicit duplicate decisions, missing/invalid dates, and indexing issues.
- **Author Mapping** — editable canonical-name mappings, quick variant merging, and explicit resolution of unmapped source rows.

## Patent worksheet

The optional `Patents` sheet may contain `Sl. No`, `Name of the Faculty`, `Title of the Patent`, `Patent Number`, `Type of Patent`, `Publication Date`, and `Granted Date`. Common spacing, punctuation, and capitalization variants of these headers are accepted.

Publication and patent attribution must not be confused:

- **Publications:** when multiple faculty names are bold, only the first bold faculty receives publication credit.
- **Patents:** when multiple faculty applicants are bold, every bold faculty receives patent credit.

A joint patent counts once institutionally but once for each credited faculty member in faculty-wise contribution analytics. Publication Year and Granted Year are stored and analyzed separately. A missing Granted Date means the patent has no recorded grant date; it is not treated as an invalid date.

## Developer commands

From PowerShell in this folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

The source code is split between `core/` for workbook processing and `ui_pages/` for dashboard rendering. No database or cloud service is used.
