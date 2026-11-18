import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Konfiguracja strony
st.set_page_config(
    page_title="Kryptomonitor — Indeks Sentymentu Rynku BTC",
    page_icon="📊",
    layout="wide"
)

# --- WPISZ PONIŻEJ SWOJE ID ARKUSZA GOOGLE ---
SHEET_ID = "15VmI-fQTLrgoU3kpWr1zE-vD2qwO5Ir-7sVigVDgZnA"
SHEET_NAME = "Live_Feed"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

@st.cache_data(ttl=60)
def load_data(url):
    df = pd.read_csv(url)
    # Konwersja kolumn numerycznych (obsługa ewentualnych przecinków z Google Sheets)
    num_cols = [
        "btc_price_usd", "fear_and_greed", "funding_rate_daily",
        "usdt_btc_ratio_pct", "active_addresses", "s_kryptomonitor"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")
    return df

# Nagłówek aplikacji
st.title("📊 Kryptomonitor — System Monitorowania Sentymentu Inwestorów Detalicznych")
st.caption("Dane pobierane automatycznie co 4 godziny z rynków spot, futures oraz sieci on-chain.")

if st.button("🔄 Odśwież dane teraz"):
    st.cache_data.clear()

try:
    df = load_data(CSV_URL)
except Exception as e:
    st.error(f"Nie udało się połączyć z Google Sheets. Sprawdź ID arkusza i uprawnienia udostępniania. Szczegóły: {e}")
    st.stop()

if df.empty:
    st.warning("Zakładka Live_Feed jest na razie pusta. Uruchom najpierw przepływ w n8n.")
    st.stop()

latest = df.iloc[-1]
s_val = float(latest["s_kryptomonitor"])
status = str(latest["status"])

# 2. Główny panel: Licznik emocji + Komunikat decyzyjny
col_gauge, col_info = st.columns([1.2, 1.8])

with col_gauge:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=s_val,
        number={"valueformat": ".4f", "font": {"size": 42}},
        title={"text": "Syntetyczny Indeks S (0 - 1)", "font": {"size": 18}},
        gauge={
            "axis": {"range": [0, 1], "tickwidth": 1},
            "bar": {"color": "#1f2937"},
            "steps": [
                {"range": [0, 0.4083], "color": "#22c55e"},      # Strefa Paniki (zielona - potencjalna akumulacja)
                {"range": [0.4083, 0.7059], "color": "#e5e7eb"}, # Strefa Neutralna
                {"range": [0.7059, 1.0], "color": "#ef4444"}     # Strefa FOMO (czerwona - przegrzanie)
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": s_val
            }
        }
    ))
    fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_info:
    st.subheader("Aktualny stan rynku")
    if "PANIKA" in status:
        st.success(f"🟢 **{status}** (Odczyt: {s_val:.4f} < próg 0.4083)")
    elif "FOMO" in status:
        st.error(f"🔴 **{status}** (Odczyt: {s_val:.4f} > próg 0.7059)")
    else:
        st.info(f"⚪ **{status}** (Odczyt w przedziale neutralnym 0.4083 – 0.7059)")

    st.write(f"**Interpretacja systemu:** {latest['komunikat']}")
    st.caption(f"Ostatnia aktualizacja (UTC): {latest['timestamp']}")

    st.markdown("""
    **Jak czytać wskaźnik?**
    * **Poniżej 0.4083 (Panika):** Skrajny strach i kapitulacja tłumu. Historycznie momenty silnego wyprzedania.
    * **0.4083 – 0.7059 (Neutralny):** Brak skrajnych emocji, rynek w równowadze.
    * **Powyżej 0.7059 (FOMO):** Skrajna euforia i przegrzanie dźwigni finansowej. Podwyższone ryzyko korekty.
    """)

st.divider()

# 3. Karty składowych wskaźnika (4 źródła danych)
st.subheader("Składowe modelu w czasie rzeczywistym")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Cena Bitcoina", f"${latest['btc_price_usd']:,.2f}")
m2.metric("Fear & Greed Index", f"{int(latest['fear_and_greed'])} / 100")
m3.metric("Funding Rate (24h)", f"{latest['funding_rate_daily']:.6f}")
m4.metric("USDT / BTC Ratio", f"{latest['usdt_btc_ratio_pct']:.2f}%")
m5.metric("Aktywne adresy BTC", f"{int(latest['active_addresses']):,}")

st.divider()

# 4. Wykres historyczny odczytów na żywo + Tabela logów
st.subheader("Historia odczytów na żywo (Live Feed)")

if len(df) > 1:
    fig_hist = make_subplots(specs=[[{"secondary_y": True}]])
    fig_hist.add_trace(
        go.Scatter(x=df["timestamp"], y=df["s_kryptomonitor"], name="Indeks S", line=dict(color="#2563eb", width=3)),
        secondary_y=False
    )
    fig_hist.add_trace(
        go.Scatter(x=df["timestamp"], y=df["btc_price_usd"], name="Cena BTC ($)", line=dict(color="#f59e0b", width=2, dash="dot")),
        secondary_y=True
    )
    fig_hist.add_hline(y=0.7059, line_dash="dash", line_color="red", annotation_text="Próg FOMO (0.7059)", secondary_y=False)
    fig_hist.add_hline(y=0.4083, line_dash="dash", line_color="green", annotation_text="Próg Paniki (0.4083)", secondary_y=False)
    fig_hist.update_layout(height=400, hovermode="x unified")
    fig_hist.update_yaxes(title_text="Indeks S (0-1)", range=[0, 1], secondary_y=False)
    fig_hist.update_yaxes(title_text="Cena BTC ($)", secondary_y=True)
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("Wykres liniowy pojawi się automatycznie po zebraniu co najmniej 2 odczytów w zakładce Live_Feed (kolejny za max 4 godziny).")

with st.expander("📋 Podgląd surowych danych z bazy (ostatnie 20 wpisów)"):
    st.dataframe(df.sort_values("timestamp", ascending=False).head(20), use_container_width=True)
