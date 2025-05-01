import streamlit as st
from st_pages import add_page_title, get_nav_from_toml

st.set_page_config(page_title=None, page_icon=None, layout="centered", initial_sidebar_state="auto", menu_items=None)

nav = get_nav_from_toml(".streamlit/pages_sections.toml")
# Get navigation configuration from TOML file


# Add logo (comment out if logo.png doesn't exist)
# st.logo("logo.png")

# Set up navigation
pg = st.navigation(nav)

# Add page title based on current page
add_page_title(pg)

# Initialize session state for BMI calculator
if "weight" not in st.session_state:
    st.session_state.weight = 0.0
if "height" not in st.session_state:
    st.session_state.height = 0.0

# Run the selected page
pg.run()