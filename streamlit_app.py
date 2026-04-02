from __future__ import annotations

import streamlit as st


st.set_page_config(page_title="GeniOS", page_icon="✦", layout="wide")

st.warning(
    "This file is kept only for compatibility. Run the true multipage frontend instead:"
)
st.code("streamlit run frontend/app.py", language="bash")