import streamlit as st


def apply_custom_styles():
    """Aplica estilos de ESIC: fondo blanco y azul institucional."""
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        .stApp {
            background-color: #ffffff;
            color: #000000;
        }
        p, span, label, .stMarkdown, .stText, .stInfo, .stWarning, .stError, .stSuccess {
            color: #000000;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #0044DD;
        }
        .stButton>button {
            background-color: #0044DD;
            color: #ffffff;
            border-radius: 6px;
            border: none;
        }
        .stButton>button:hover {
            background-color: #0033AA;
            color: #ffffff;
        }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            color: #0044DD;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
