import io
from typing import Dict
import pandas as pd


def to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    """
    Build an in-memory Excel workbook with one sheet per DataFrame.

    Args:
        sheets: Mapping of sheet_name -> DataFrame

    Returns:
        Bytes of the XLSX file suitable for st.download_button.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            safe_name = (name or "Sheet").strip()[:31]
            df.to_excel(writer, index=False, sheet_name=safe_name)
            # Basic formatting
            ws = writer.sheets[safe_name]
            for i, col in enumerate(df.columns):
                width = max(10, min(40, int(df[col].astype(str).map(len).max() or 10)))
                ws.set_column(i, i, width)
    return output.getvalue()



