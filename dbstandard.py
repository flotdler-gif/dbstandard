import streamlit as st
import pandas as pd
import pyodbc

st.set_page_config(page_title="Databáze standardů", layout="wide")
st.title("Databáze standardů")

# ------------------------------
# 1️⃣ Připojení k databázi
# ------------------------------
mdb_file = r"dbtrial.accdb"  # uprav cestu
conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    fr'DBQ={mdb_file};'
)

@st.cache_data
def load_data():

    conn = pyodbc.connect(conn_str)
    df = pd.read_sql("SELECT * FROM slozeni", conn)
    conn.close()
    return df

df = load_data()

df = df.rename(columns={"klic_Standard": "Klíč"})

#kosik
if "cart" not in st.session_state:
    st.session_state.cart = pd.DataFrame()

st.sidebar.header("Filtry")

# ------------------------------
# 2️⃣ Základní filtry
# ------------------------------
nazev_filter = st.sidebar.text_input("Hledej podle názvu standardu:")
puvod_options = ["Vše"] + sorted(df["Group"].dropna().unique().tolist())
puvod_filter = st.sidebar.multiselect(
    "Vyber původ standardu:",
    puvod_options[1:],  # bez "Vše"
    default=[]
)

instituce_options = sorted(df["instituce"].dropna().unique())
selected_instituce = st.sidebar.multiselect(
    "Vyber instituci:",
    instituce_options,
    default=[]  # můžeš např. [] nebo první n institucí
)

# ------------------------------
# 3️⃣ Filtry podle prvků (číselné)
# ------------------------------
# Detekce sloupců prvků: všechno kromě názvu, původu, atd.
non_element_cols = ["Klíč", "klic_Group", "Standard", "Group", "Instituce"]  # případně přidej další sloupce

# numerická data
df_numeric = df.copy()
for col in df_numeric.columns:
    if col not in non_element_cols:
        df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce')

# dostupné prvky (jen ty, co mají čísla)
element_cols = [
    col for col in df_numeric.columns
    if col not in non_element_cols and df_numeric[col].notna().sum() > 0
]

st.sidebar.subheader("Výběr prvků")
only_nonzero = st.sidebar.checkbox("Pouze nenulové hodnoty pro vybrané prvky", value=True)

selected_elements = st.sidebar.multiselect(
    "Vyber prvky pro filtraci:",
    element_cols,
    default=[]  # můžeš dát třeba ["Zn", "Fe"]
)

st.sidebar.subheader("Rozsahy prvků")

element_filters = {}

for col in selected_elements:
    series = df_numeric[col].dropna()

    if len(series) == 0:
        continue

    min_val = float(series.min())
    max_val = float(series.max())

    # ochrana proti konstantním hodnotám
    if min_val == max_val:
        continue

    selected_range = st.sidebar.slider(
        f"{col}",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val)
    )

    element_filters[col] = selected_range

# ------------------------------
# 4️⃣ Aplikace filtrů
# -----------------------------
df_filtered = df_numeric.copy()

# textové filtry
if nazev_filter:
    df_filtered = df_filtered[df_filtered["Standard"].str.contains(nazev_filter, case=False, na=False)]

if puvod_filter:
    df_filtered = df_filtered[df_filtered["Group"].isin(puvod_filter)]

if selected_instituce:
    df_filtered = df_filtered[df_filtered["instituce"].isin(selected_instituce)]

# filtry prvků
for col, (min_val, max_val) in element_filters.items():
    
    # rozsah
    df_filtered = df_filtered[df_filtered[col].between(min_val, max_val)]
    
    # klíčová část – odstranění nul
    if only_nonzero:
        df_filtered = df_filtered[df_filtered[col] > 0]


# ------------------------------
# 5️⃣ Výstup
# ------------------------------
st.write(f"Zobrazuji {len(df_filtered)} standardů z celkem {len(df)}")

selected_idx = st.dataframe(
    df_filtered.drop(columns=["klic_Group"], errors="ignore"),
    width="stretch",
    on_select="rerun",
    selection_mode="multi-row"
)

if selected_idx.selection.rows:
    selected_rows = df_filtered.iloc[selected_idx.selection.rows]

    if st.button("➕ Přidat vybrané"):
     st.session_state.cart = pd.concat(
        [st.session_state.cart, selected_rows],
        ignore_index=True
    )
   
#Kosik

st.subheader("Vybrané standardy")

if not st.session_state.cart.empty:
    selected_cart = st.dataframe(
        st.session_state.cart.drop(columns=["klic_Group"], errors="ignore"),
        width="stretch",
        on_select="rerun",
        selection_mode="multi-row"
    )

    st.download_button(
    "💾 Export výběru",
    st.session_state.cart.to_csv(index=False),
    file_name="vybrane_standardy.csv"
)

    if selected_cart.selection.rows:
        idx = selected_cart.selection.rows[0]

        if st.button("❌ Odebrat vybrané"):
            st.session_state.cart = (
            st.session_state.cart
            .drop(selected_cart.selection.rows)
            .reset_index(drop=True)
        )

    if st.button("🗑 Vymazat vše"):
        st.session_state.cart = pd.DataFrame()
else:
    st.info("Zatím nic nevybráno")

