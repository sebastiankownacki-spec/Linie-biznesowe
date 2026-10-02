import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfiguracja strony
st.set_page_config(
    page_title="Dashboard Produkcyjny",
    page_icon="📊",
    layout="wide"
)

# 2. Pobieranie danych z Google Sheets
SHEET_ID = "1H4ul1i1LlHDW-ody6x3RKHRIJkLXn1sfNPeQZhbPLrY"
GID = "2051498847"
DATA_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=600)  # Odświeżanie danych co 10 minut
def load_data():
    df = pd.read_csv(DATA_URL)
    
    # Standaryzacja nazw kolumn
    df.columns = df.columns.str.strip()
    
    # Konwersja dat
    if 'Data produkcji' in df.columns:
        df['Data produkcji'] = pd.to_datetime(df['Data produkcji']).dt.date
    if 'Data menu' in df.columns:
        df['Data menu'] = pd.to_datetime(df['Data menu']).dt.date
        
    # Czyszczenie i konwersja ilości do wartości numerycznych
    if 'Ilość' in df.columns:
        df['Ilość'] = df['Ilość'].astype(str).str.replace(',', '.').str.replace(' ', '')
        df['Ilość'] = pd.to_numeric(df['Ilość'], errors='coerce').fillna(0)
        
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Błąd podczas pobierania danych z Google Sheets: {e}")
    st.stop()

# 3. Pasek boczny – Filtry (Sidebar)
st.sidebar.header("🔍 Filtry danych")

# Filtry dat rozbite na dwa osobne pola
min_date = df_raw['Data produkcji'].min() if 'Data produkcji' in df_raw.columns else None
max_date = df_raw['Data produkcji'].max() if 'Data produkcji' in df_raw.columns else None

if min_date and max_date:
    st.sidebar.subheader("📅 Zakres daty produkcji")
    col_start, col_end = st.sidebar.columns(2)
    with col_start:
        start_date = st.date_input(
            "Data początkowa",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )
    with col_end:
        end_date = st.date_input(
            "Data końcowa",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
else:
    start_date, end_date = None, None

# Filtry wielokrotnego wyboru
diety = st.sidebar.multiselect("Dieta / Menu", options=df_raw['Dieta/Menu'].unique(), default=df_raw['Dieta/Menu'].unique())
sekcje = st.sidebar.multiselect("Sekcja", options=df_raw['Sekcja'].unique(), default=df_raw['Sekcja'].unique())
rodzaje = st.sidebar.multiselect("Rodzaj", options=df_raw['Rodzaj'].unique(), default=df_raw['Rodzaj'].unique())

# Filtrowanie ramki danych
df_filtered = df_raw.copy()

if start_date and end_date:
    df_filtered = df_filtered[
        (df_filtered['Data produkcji'] >= start_date) & 
        (df_filtered['Data produkcji'] <= end_date)
    ]

df_filtered = df_filtered[
    (df_filtered['Dieta/Menu'].isin(diety)) &
    (df_filtered['Sekcja'].isin(sekcje)) &
    (df_filtered['Rodzaj'].isin(rodzaje))
]

# 4. Tytuł i Kluczowe Wskaźniki (KPI Cards)
st.title("📊 Panel Analizy Produkcyjnej")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Liczba pozycji", len(df_filtered))
with col2:
    st.metric("Liczba unikalnych dań", df_filtered['Nazwa dania'].nunique())
with col3:
    st.metric("Suma wyprodukowanych sztuk", f"{df_filtered[df_filtered['Jednostka'] == 'szt']['Ilość'].sum():,.0f} szt")
with col4:
    st.metric("Suma masy składników", f"{df_filtered[df_filtered['Jednostka'] == 'kg']['Ilość'].sum():,.2f} kg")

st.markdown("---")

# Suwak kontrolujący liczbę wyświetlanych pozycji dla obu sekcji (Dania i Składniki)
top_n = st.slider("Liczba wyświetlanych pozycji na wykresach:", min_value=5, max_value=200, value=10, step=5)

# 5. Wykresy: Najpopularniejsze dania
st.subheader("🔥 Najpopularniejsze dania")

tab_szt, tab_kg = st.tabs([f"📦 Top {top_n} Dań - Sztuki (szt)", f"⚖️ Top {top_n} Dań - Waga (kg)"])

with tab_szt:
    df_szt = df_filtered[df_filtered['Jednostka'] == 'szt']
    top_szt = (
        df_szt.groupby('Nazwa dania')['Ilość']
        .sum()
        .reset_index()
        .sort_values(by='Ilość', ascending=False)
        .head(top_n)
    )

    if not top_szt.empty:
        fig_szt = px.bar(
            top_szt,
            x='Ilość',
            y='Nazwa dania',
            orientation='h',
            title=f"Top {top_n} dań pod względem liczby sztuk",
            color_discrete_sequence=['#2b5c8f']
        )
        fig_szt.update_traces(texttemplate='%{x:,.0f}', textposition='outside')
        fig_szt.update_layout(
            yaxis={'categoryorder': 'total ascending'}, 
            xaxis_title="Łączna ilość (szt)",
            yaxis_title=None,
            height=max(400, len(top_szt) * 28)
        )
        st.plotly_chart(fig_szt, use_container_width=True)
    else:
        st.info("Brak danych dla jednostki 'szt' w wybranym filtrze.")

with tab_kg:
    df_kg = df_filtered[df_filtered['Jednostka'] == 'kg']
    top_kg = (
        df_kg.groupby('Nazwa dania')['Ilość']
        .sum()
        .reset_index()
        .sort_values(by='Ilość', ascending=False)
        .head(top_n)
    )

    if not top_kg.empty:
        fig_kg = px.bar(
            top_kg,
            x='Ilość',
            y='Nazwa dania',
            orientation='h',
            title=f"Top {top_n} dań pod względem wagi (kg)",
            color_discrete_sequence=['#e07a5f']
        )
        fig_kg.update_traces(texttemplate='%{x:,.2f}', textposition='outside')
        fig_kg.update_layout(
            yaxis={'categoryorder': 'total ascending'}, 
            xaxis_title="Łączna waga (kg)",
            yaxis_title=None,
            height=max(400, len(top_kg) * 28)
        )
        st.plotly_chart(fig_kg, use_container_width=True)
    else:
        st.info("Brak danych dla jednostki 'kg' w wybranym filtrze.")

st.markdown("---")

# 6. Wykresy: Najpopularniejsze składniki (Kolumna H)
st.subheader("🥗 Najpopularniejsze składniki")

tab_skladnik_szt, tab_skladnik_kg = st.tabs([f"📦 Top {top_n} Składników - Sztuki (szt)", f"⚖️ Top {top_n} Składników - Waga (kg)"])

with tab_skladnik_szt:
    df_skl_szt = df_filtered[df_filtered['Jednostka'] == 'szt']
    top_skl_szt = (
        df_skl_szt.groupby('Składnik')['Ilość']
        .sum()
        .reset_index()
        .sort_values(by='Ilość', ascending=False)
        .head(top_n)
    )

    if not top_skl_szt.empty:
        fig_skl_szt = px.bar(
            top_skl_szt,
            x='Ilość',
            y='Składnik',
            orientation='h',
            title=f"Top {top_n} składników pod względem liczby sztuk",
            color_discrete_sequence=['#38b000']
        )
        fig_skl_szt.update_traces(texttemplate='%{x:,.0f}', textposition='outside')
        fig_skl_szt.update_layout(
            yaxis={'categoryorder': 'total ascending'}, 
            xaxis_title="Łączna ilość (szt)",
            yaxis_title=None,
            height=max(400, len(top_skl_szt) * 28)
        )
        st.plotly_chart(fig_skl_szt, use_container_width=True)
    else:
        st.info("Brak danych składników dla jednostki 'szt'.")

with tab_skladnik_kg:
    df_skl_kg = df_filtered[df_filtered['Jednostka'] == 'kg']
    top_skl_kg = (
        df_skl_kg.groupby('Składnik')['Ilość']
        .sum()
        .reset_index()
        .sort_values(by='Ilość', ascending=False)
        .head(top_n)
    )

    if not top_skl_kg.empty:
        fig_skl_kg = px.bar(
            top_skl_kg,
            x='Ilość',
            y='Składnik',
            orientation='h',
            title=f"Top {top_n} składników pod względem wagi (kg)",
            color_discrete_sequence=['#9d4edd']
        )
        fig_skl_kg.update_traces(texttemplate='%{x:,.2f}', textposition='outside')
        fig_skl_kg.update_layout(
            yaxis={'categoryorder': 'total ascending'}, 
            xaxis_title="Łączna waga (kg)",
            yaxis_title=None,
            height=max(400, len(top_skl_kg) * 28)
        )
        st.plotly_chart(fig_skl_kg, use_container_width=True)
    else:
        st.info("Brak danych składników dla jednostki 'kg'.")

st.markdown("---")

# 7. Dodatkowe wykresy pomocnicze
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📦 Udział sekcji produkcyjnych")
    sekcja_sum = df_filtered.groupby('Sekcja')['Ilość'].sum().reset_index()
    fig_pie = px.pie(
        sekcja_sum, 
        names='Sekcja', 
        values='Ilość', 
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("📅 Produkcja w czasie")
    daily_prod = df_filtered.groupby(['Data produkcji', 'Jednostka'])['Ilość'].sum().reset_index()
    fig_line = px.line(
        daily_prod, 
        x='Data produkcji', 
        y='Ilość', 
        color='Jednostka',
        markers=True,
        title="Ilość produkcji w podziale na dni"
    )
    st.plotly_chart(fig_line, use_container_width=True)

# 8. Tabela danych ze szczegółami składników
st.markdown("---")
st.subheader("🔍 Szczegółowe zestawienie dań i składników")

selected_dish = st.selectbox(
    "Wybierz konkretne danie, aby zobaczyć jego składniki:", 
    ["Wszystkie"] + list(df_filtered['Nazwa dania'].unique())
)

if selected_dish != "Wszystkie":
    display_df = df_filtered[df_filtered['Nazwa dania'] == selected_dish]
else:
    display_df = df_filtered

st.dataframe(
    display_df[['Data produkcji', 'Data menu', 'Dieta/Menu', 'Sekcja', 'Rodzaj', 'Nazwa dania', 'Składnik', 'Ilość', 'Jednostka']],
    use_container_width=True,
    height=300
)

# Przycisk pobierania przefiltrowanych danych
csv_data = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Pobierz przefiltrowane dane do CSV",
    data=csv_data,
    file_name="przefiltrowana_produkcja.csv",
    mime="text/csv"
)
