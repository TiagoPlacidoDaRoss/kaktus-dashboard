import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

DB_NAME = "kaktus_analytics.db"

# =========================================================
# CONFIGURAZIONE FLOTTA IMPIANTI (FLEET MANAGEMENT)
# =========================================================
CONFIG_IMPIANTI = {
    "🌵 GW012 Kaktus (Capo Verde)": {
        "tab_ro": "storico_ro", "tab_uf": "storico_uf", "tab_nas": "storico_nastec",
        "has_uf": True,
        "has_sec": True,
        "has_bag_filters": False,
        "fit_labels": {
            "fit001": "Flusso Permeato",
            "fit002": "Flusso Concentrato",
        },
        "inverters": {
            'NAS1': 'Pompa HP 1 (RO)', 'NAS2': 'Pompa HP 2 (RO)', 'NAS3': 'Pompa HP 3 (RO)', 'NAS4': 'Pompa HP 4 (RO)', 
            'NAS5': 'Pompa Pozzo Kaktus', 'NAS6': 'Pompa Alimento (RO)', 'NAS11': 'Pompa Travaso TK10-3', 
            'NAS12': 'Pompa Pozzo Toninho', 'NAS13': 'Pompa Travaso TK11-3'
        }
    },
    "🌴 Pingwe (Zanzibar)": {
        "tab_ro": "pingwe_ro", "tab_uf": None, "tab_nas": "pingwe_nastec",
        "has_uf": False,
        "has_sec": False,
        "has_bag_filters": True,
        "fit_labels": {
            "fit005": "Flusso Potabile (Uscita)",
        },
        "inverters": {
            'NAS1': 'Pompa Pozzo 1 (P01)', 
            'NAS2': 'Pompa Pozzo 2 (P05)', 
            'NAS3': 'Pompa ATM Standard', 
            'NAS4': 'Pompa ATM Premium',
            'NAS5': 'Pompa Ausiliaria (NAS5)'
        }
    }
}

PUMP_INSTALL_DATES = {
    "🌵 GW012 Kaktus (Capo Verde)": {
        "NAS5": "2026-06-12"
    },
    "🌴 Pingwe (Zanzibar)": {}
}

# =========================================================
# HELPER: ELABORAZIONE DATI E CACHING
# =========================================================
def render_produzione_pdf(impianto_scelto):
    st.header("📄 Analisi Produzione da PDF")
    
    # Mappatura per filtrare il nome impianto nel database
    # (assumendo che nella colonna 'impianto' ci sia "Kaktus" o "Pingwe")
    nome_db = "Kaktus" if "Kaktus" in impianto_scelto else "Pingwe"
    
    try:
        from supabase import create_client
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # Recupero dati per l'impianto selezionato
        res = supabase.table("produzione_pdf").select("*").eq("impianto", nome_db).order("data_rif", desc=False).execute()
        df_pdf = pd.DataFrame(res.data)
        
        if df_pdf.empty:
            st.info(f"Nessun dato PDF trovato per {nome_db}.")
            return

        # Conversione date e grafici
        df_pdf['data_rif'] = pd.to_datetime(df_pdf['data_rif'])
        
        col1, col2 = st.columns(2)
        col1.metric("Totale Permeato", f"{df_pdf['permeato'].sum():,.2f} m³")
        col2.metric("Media Insolazione", f"{df_pdf['insolation'].mean():,.2f} kWh/m²")
        
        # Grafico Trend Produzione
        fig = px.line(df_pdf, x="data_rif", y=["permeato", "concentrato"], title=f"Trend Produzione - {nome_db}")
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_pdf[['data_rif', 'permeato', 'concentrato', 'insolation', 'file_origine']], use_container_width=True)
        
    except Exception as e:
        st.error(f"Errore caricamento dati PDF: {e}")

def normalizza_dataframe(df):
    if df is None or df.empty: return pd.DataFrame() if df is None else df.copy()
    out = df.copy()
    out = out.loc[:, ~out.columns.duplicated()].copy()

    if 'timestamp' in out.columns:
        out['timestamp'] = pd.to_numeric(out['timestamp'], errors='coerce')

    if 'date_str' in out.columns:
        out['date_str'] = pd.to_datetime(out['date_str'], errors='coerce')
    elif 'timestamp' in out.columns:
        out['date_str'] = pd.to_datetime(out['timestamp'], unit='s', errors='coerce')

    colonne_testo = {'date_str', 'nas_id'}
    for col in out.columns:
        if col not in colonne_testo:
            converted = pd.to_numeric(out[col], errors='coerce')
            if converted.notna().sum() >= out[col].notna().sum() * 0.8:
                out[col] = converted

    if 'date_str' in out.columns:
        out = out.dropna(subset=['date_str']).sort_values('date_str').reset_index(drop=True)
    elif 'timestamp' in out.columns:
        out = out.sort_values('timestamp').reset_index(drop=True)
    return out

@st.cache_data(ttl=300) 
def load_data(impianto_selezionato):
    config = CONFIG_IMPIANTI[impianto_selezionato]
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        def fetch_all(table_name):
            if not table_name: return []
            all_data, offset, limit = [], 0, 1000
            while True:
                res = supabase.table(table_name).select("*").order("timestamp").range(offset, offset + limit - 1).execute()
                if not res.data: break 
                all_data.extend(res.data)
                if len(res.data) < limit: break 
                offset += limit
            return all_data

        df_ro = normalizza_dataframe(pd.DataFrame(fetch_all(config["tab_ro"])))
        df_uf = normalizza_dataframe(pd.DataFrame(fetch_all(config["tab_uf"]))) if config["has_uf"] else pd.DataFrame()
        df_nas = normalizza_dataframe(pd.DataFrame(fetch_all(config["tab_nas"])))
        return df_ro, df_uf, df_nas, "☁️ Cloud Supabase"
    except Exception as e:
        conn = sqlite3.connect(DB_NAME)
        try:
            df_ro = normalizza_dataframe(pd.read_sql_query(f"SELECT * FROM {config['tab_ro']} ORDER BY timestamp ASC", conn))
            df_uf = normalizza_dataframe(pd.read_sql_query(f"SELECT * FROM {config['tab_uf']} ORDER BY timestamp ASC", conn)) if config["has_uf"] else pd.DataFrame()
            df_nas = normalizza_dataframe(pd.read_sql_query(f"SELECT * FROM {config['tab_nas']} ORDER BY timestamp ASC", conn))
        except Exception: 
            df_ro, df_uf, df_nas = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        conn.close()
        return df_ro, df_uf, df_nas, "🖥️ Locale SQLite"

@st.cache_data(ttl=300)
def calcola_metriche_derivate(df_ro):
    if df_ro is None or df_ro.empty: return df_ro
    out = df_ro.copy()
    out['tcf'] = np.where(out['tit001'] > 0, np.exp(2640 * (1 / 298.15 - 1 / (out['tit001'] + 273.15))), 1.0)
    Y = np.clip(out['recovery'] / 100.0, 0.01, 0.95) 
    FCS = -np.log(1 - Y) / Y
    pi_feed = out['ait001'] * 0.35
    pi_avg = pi_feed * FCS
    pi_perm = (out['ait002'] / 1000.0) * 0.35 
    delta_pi = pi_avg - pi_perm
    
    if 'pit004' not in out.columns: out['pit004'] = 0.0
    p_out = np.where(out['pit004'] > 0, out['pit004'], out['pit003'] - 1.5)
    
    out['p_media'] = (out['pit003'] + p_out) / 2.0
    out['ndp'] = np.where(out['p_media'] - delta_pi <= 0.1, 0.1, out['p_media'] - delta_pi) 
    out['perm_norm'] = out['fit001'] / (out['ndp'] * out['tcf'])
    out['perm_norm_smooth'] = out['perm_norm'].rolling(window=24, min_periods=1).mean()
    
    out['nsp'] = (100 - out['salt_rejection']) / out['tcf']
    out['sr_norm'] = 100 - out['nsp']
    
    if 'dp_cf01' not in out.columns: out['dp_cf01'] = out['pit001'] - out['pit002']
    if 'dp_ro' not in out.columns: out['dp_ro'] = out['pit003'] - out['pit004']
    out['dp_ro_smooth'] = out['dp_ro'].rolling(window=24, min_periods=1).mean()
    return out

def converti_df_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# =========================================================
# HELPER: FUNZIONI GRAFICHE E CALCOLI PREDITTIVI
# =========================================================
def colonne_fit_disponibili(df):
    if df is None or df.empty: return []
    fit_cols = [col for col in df.columns if str(col).lower().startswith("fit") and str(col)[3:].isdigit()]
    return sorted(fit_cols, key=lambda c: int(str(c).lower()[3:]))

def render_metriche_fit(df, config, max_colonne=5):
    fit_cols = colonne_fit_disponibili(df)
    if not fit_cols: return st.info("Nessun misuratore di portata FIT disponibile nei dati.")
    labels = config.get("fit_labels", {})
    for inizio in range(0, len(fit_cols), max_colonne):
        gruppo = fit_cols[inizio:inizio + max_colonne]
        colonne = st.columns(len(gruppo))
        for contenitore, fit_col in zip(colonne, gruppo):
            valori = pd.to_numeric(df[fit_col], errors="coerce").dropna()
            if valori.empty: continue
            valore_attuale = float(valori.iloc[-1])
            baseline = float(valori.iloc[0])
            titolo = labels.get(str(fit_col).lower())
            etichetta = f"{titolo} ({str(fit_col).upper()})" if titolo else str(fit_col).upper()
            contenitore.metric(etichetta, f"{valore_attuale:.2f} m³/h", f"{valore_attuale - baseline:+.2f} m³/h", delta_color="off")

def crea_grafico_linee(df, x_col, y_cols, title=None, markers=False):
    if isinstance(y_cols, str): y_cols = [y_cols]
    y_cols = [col for col in y_cols if col in df.columns]
    if x_col not in df.columns or not y_cols: return None

    dati = df[[x_col] + y_cols].copy()
    dati = dati.loc[:, ~dati.columns.duplicated()]
    if x_col in {'date_str', 'DataOra'}: dati[x_col] = pd.to_datetime(dati[x_col], errors='coerce')
    for col in y_cols: dati[col] = pd.to_numeric(dati[col], errors='coerce')
    dati = dati.dropna(subset=[x_col]).dropna(subset=y_cols, how='all')
    
    if dati.empty: return None
    fig = go.Figure()
    for col in y_cols:
        fig.add_trace(go.Scatter(x=dati[x_col], y=dati[col], mode='lines+markers' if markers else 'lines', name=col))
    fig.update_layout(title=title, hovermode='x unified', margin=dict(l=20, r=20, t=55 if title else 20, b=20))
    return fig

def crea_grafico_previsione(df, col_y, title, real_name, prediction_name, giorni_futuri, limite=None, limite_label=None, baseline=None, baseline_label=None, yaxis_title=None, direzione_previsione=None):
    if df is None or df.empty or col_y not in df.columns: return None
    date = pd.to_datetime(df['date_str'] if 'date_str' in df.columns else pd.to_numeric(df['timestamp']), unit='s', errors='coerce')
    y = pd.to_numeric(df[col_y], errors='coerce')
    validi = date.notna() & y.notna() & np.isfinite(y)
    date, y = date[validi].reset_index(drop=True), y[validi].reset_index(drop=True)
    if date.empty: return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date, y=y, mode='lines', name=real_name))

    if len(y) >= 3 and date.nunique() >= 2:
        x_giorni = (date - date.iloc[0]).dt.total_seconds().to_numpy(dtype=float) / 86400.0
        try:
            slope, intercept = np.polyfit(x_giorni, y.to_numpy(dtype=float), 1)
            mostra_previsione = np.isfinite(slope) and np.isfinite(intercept)
            if direzione_previsione == 'up': mostra_previsione = mostra_previsione and slope > 0
            elif direzione_previsione == 'down': mostra_previsione = mostra_previsione and slope < 0

            if mostra_previsione:
                x_futuro = np.linspace(x_giorni[0], x_giorni[-1] + giorni_futuri, 120)
                fig.add_trace(go.Scatter(x=date.iloc[0] + pd.to_timedelta(x_futuro, unit='D'), y=slope * x_futuro + intercept, mode='lines', line=dict(dash='dash'), name=prediction_name))
        except (TypeError, ValueError, np.linalg.LinAlgError): pass

    if limite is not None and np.isfinite(float(limite)): fig.add_hline(y=float(limite), line_color='red', annotation_text=limite_label or 'Limite')
    if baseline is not None and np.isfinite(float(baseline)): fig.add_hline(y=float(baseline), line_color='green', line_dash='dot', annotation_text=baseline_label or 'Baseline')
    fig.update_layout(title=title, yaxis_title=yaxis_title, hovermode='x unified', margin=dict(l=20, r=20, t=55, b=20))
    return fig

def stima_giorni_rimanenti(df, col_y, limite, is_max_limit=True):
    if df is None or len(df) < 3 or col_y not in df.columns: return None
    dati = df.copy()
    x = pd.to_numeric(dati['timestamp'] if 'timestamp' in dati.columns else pd.to_datetime(dati['date_str']).astype('int64') / 1e9, errors='coerce')
    y = pd.to_numeric(dati[col_y], errors='coerce')
    validi = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    x, y = x[validi].to_numpy(dtype=float), y[validi].to_numpy(dtype=float)

    if len(x) < 3 or np.allclose(x, x[0]) or np.allclose(y, y[0]): return 999
    try: slope, intercept = np.polyfit((x - x[0]) / 86400.0, y, 1)
    except: return None

    if not np.isfinite(slope) or abs(slope) < 1e-12: return 999
    if (is_max_limit and slope <= 0) or (not is_max_limit and slope >= 0): return 999
    return max(0, int(np.ceil(((float(limite) - intercept) / slope) - ((x[-1] - x[0]) / 86400.0))))

def get_health_score(valore_attuale, baseline, limite, is_max_limit=True):
    try:
        denominatore = (float(limite) - float(baseline)) if is_max_limit else (float(baseline) - float(limite))
        if not np.isfinite(denominatore) or abs(denominatore) < 1e-12: return 100.0
        score = 100 - ((float(valore_attuale) - float(baseline)) / denominatore * 100) if is_max_limit else 100 - ((float(baseline) - float(valore_attuale)) / denominatore * 100)
        return max(0.0, min(100.0, score if np.isfinite(score) else 0.0))
    except (TypeError, ValueError): return 0.0

# =========================================================
# VISTE: MODULI UI
# =========================================================
def render_osmosi(df_ro, baseline_ro, latest_ro, config_attuale, impianto_scelto):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Recovery", f"{latest_ro['recovery']:.1f} %", f"{latest_ro['recovery'] - baseline_ro['recovery']:+.1f}%")
    c2.metric("Reiezione (Norm)", f"{latest_ro['sr_norm']:.2f} %", f"{latest_ro['sr_norm'] - baseline_ro['sr_norm']:+.2f}%")
    
    if config_attuale["has_bag_filters"]:
        c3.metric("ΔP Filtri a Calza", f"{latest_ro['pit007']:.2f} bar", f"{latest_ro['pit007'] - baseline_ro['pit007']:+.2f}", delta_color="inverse")
    else:
        c3.metric("Consumo SEC", f"{latest_ro['sec']:.2f} kWh/m³", f"{latest_ro['sec'] - baseline_ro['sec']:+.2f}", delta_color="inverse")
        
    c4.metric("ΔP Cartuccia CF01", f"{latest_ro['dp_cf01']:.2f} bar", f"{latest_ro['dp_cf01'] - baseline_ro['dp_cf01']:+.2f}", delta_color="inverse")
    c5.metric("ΔP Membrane", f"{latest_ro['dp_ro']:.2f} bar", f"{latest_ro['dp_ro'] - baseline_ro['dp_ro']:+.2f}", delta_color="inverse")
    
    st.markdown("---")
    st.subheader("Parametri Acqua (Extra)")
    col_ph, col_cond_feed, col_cond_perm = st.columns(3)
    col_ph.metric("pH Permeato", f"{latest_ro.get('ait005', np.nan):.2f}" if pd.notna(latest_ro.get('ait005')) and latest_ro.get('ait005') > 0 else "N/D")
    col_cond_feed.metric("Conducibilità Alimento", f"{latest_ro.get('ait001', np.nan):.2f} mS/cm" if pd.notna(latest_ro.get('ait001')) and latest_ro.get('ait001') > 0 else "N/D")
    col_cond_perm.metric("Conducibilità Permeato", f"{latest_ro.get('ait002', np.nan):.1f} µS/cm" if pd.notna(latest_ro.get('ait002')) and latest_ro.get('ait002') > 0 else "N/D")

    st.markdown("#### Portate istantanee — tutti i FIT")
    render_metriche_fit(df_ro, config_attuale)

    tab1, tab2 = st.tabs(["Grafici di Tendenza", "Dati Tabellari ed Esportazione"])
    with tab1:
        fig_perm = go.Figure()
        fig_perm.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['perm_norm'], mode='markers+lines', name='Dato Orario', line=dict(color='lightblue', width=1)))
        fig_perm.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['perm_norm_smooth'], mode='lines', name='Trend (Media 24h)', line=dict(color='darkblue', width=4)))
        fig_perm.update_layout(title='Fouling: Indice di Permeabilità ASTM (Media Mobile)', yaxis_title='Permeabilità (m³/h/bar)', hovermode='x unified')
        st.plotly_chart(fig_perm, use_container_width=True)

        fig_press = go.Figure()
        if 'fit001' in df_ro.columns: fig_press.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['fit001'], name='Permeato (m³/h)', mode='lines+markers'))
        if 'pit003' in df_ro.columns: fig_press.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['pit003'], name='P. Ingresso (bar)', yaxis='y2'))
        if 'pit004' in df_ro.columns: fig_press.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['pit004'], name='P. Uscita (bar)', yaxis='y2', line=dict(dash='dot')))
        fig_press.update_layout(title='Dinamica Pressioni Idrauliche', yaxis=dict(title='Portata (m³/h)'), yaxis2=dict(title='Pressione (bar)', overlaying='y', side='right'), hovermode='x unified')
        st.plotly_chart(fig_press, use_container_width=True)
    with tab2:
        st.download_button(label="📥 Esporta Storico in formato CSV", data=converti_df_csv(df_ro), file_name=f'storico_ro_{impianto_scelto}.csv', mime='text/csv')
        st.dataframe(df_ro, use_container_width=True)
        
    st.info("""💡 **Guida alla Lettura - Osmosi Inversa (RO):**
    - **Recovery (Recupero):** La percentuale di acqua di alimento trasformata in permeato (acqua dolce).
    - **Reiezione Salina (Normalizzata):** Indica l'efficienza chimica della membrana nel bloccare i sali, depurata matematicamente dalle fluttuazioni di temperatura. Per calcolarla si usa il fattore $TCF = \\exp\\left[2640 \\cdot \\left(\\frac{1}{298.15} - \\frac{1}{T_{acqua} + 273.15}\\right)\\right]$. Valori ottimali: > 98%.
    - **Consumo SEC:** Energia Specifica Consumata (kWh/m³). Rappresenta quanta energia è necessaria per produrre un singolo metro cubo di acqua dolce.
    - **ΔP (Salto di Pressione):** Misura la perdita di carico idraulica tra l'ingresso e l'uscita dei vessel. Un aumento continuo segnala un'ostruzione fisica (fouling, bio-fouling o scaling inorganico).""")

def render_uf(df_uf, baseline_uf, latest_uf, impianto_scelto):
    if df_uf.empty: return st.warning("Nessun dato UF.")
    
    col_dati, col_export = st.columns([8, 2])
    with col_export:
        st.download_button(label="📥 Esporta CSV", data=converti_df_csv(df_uf), file_name=f'storico_uf_{impianto_scelto}.csv', mime='text/csv')
        
    c1, c2, c3 = st.columns(3)
    c1.metric("Flusso UF", f"{latest_uf['fit001']:.2f} m³/h", f"{latest_uf['fit001'] - baseline_uf['fit001']:+.2f}")
    c2.metric("TMP UF", f"{latest_uf['uftmp']:.2f} bar", f"{latest_uf['uftmp'] - baseline_uf['uftmp']:+.2f}", delta_color="inverse")
    c3.metric("ΔP Filtro", f"{latest_uf['dpscf']:.2f} bar", f"{latest_uf['dpscf'] - baseline_uf['dpscf']:+.2f}", delta_color="inverse")
    
    fig = crea_grafico_linee(df_uf, 'date_str', ['uftmp', 'dpscf'], title="Trend Pressioni UF", markers=True)
    if fig is not None: st.plotly_chart(fig, use_container_width=True)
    
    st.info("""💡 **Guida alla Lettura - Ultrafiltrazione (UF):**
    - **TMP (Pressione Trans-Membrana):** È la pressione netta necessaria per forzare l'acqua ad attraversare i pori microscopici (fibre cave) della membrana di pre-trattamento. 
    - **Salute dell'Asset:** Un rapido e continuo aumento della TMP (verso la soglia di guardia di 1.5 bar) indica un intasamento dei pori (fouling irreversibile) o la necessità di rendere i cicli di controlavaggio (Backwash / CEB) più frequenti o aggressivi.""")

def render_inverter(df_nas, config_attuale, impianto_scelto):
    if df_nas.empty: return st.warning("Nessun dato inverter.")
    df_nas_latest = df_nas[df_nas['timestamp'] == df_nas['timestamp'].max()].copy()
    df_nas_latest['Nome Pompa'] = df_nas_latest['nas_id'].map(config_attuale["inverters"]).fillna("Pompa Sconosciuta")
    
    col1, col2 = st.columns([8, 2])
    with col1: st.dataframe(df_nas_latest[['Nome Pompa', 'status', 'freq', 'current', 'power', 'cosphi']], use_container_width=True)
    with col2: st.download_button(label="📥 Esporta CSV", data=converti_df_csv(df_nas), file_name=f'storico_inverter_{impianto_scelto}.csv', mime='text/csv')
    
    st.subheader("Analisi Salute Statore")
    pompa_sel = st.selectbox("Seleziona pompa per trend Cosφ:", options=list(config_attuale["inverters"].keys()), format_func=lambda x: f"{x} - {config_attuale['inverters'][x]}")
    df_p_plot = df_nas[(df_nas['nas_id'] == pompa_sel) & (df_nas['freq'] > 1.0)].copy()
    
    if not df_p_plot.empty and 'cosphi' in df_p_plot.columns and df_p_plot['cosphi'].notnull().any():
        fig = crea_grafico_linee(df_p_plot, 'date_str', 'cosphi', title=f"Trend Cosφ - {pompa_sel}")
        if fig is not None: st.plotly_chart(fig, use_container_width=True)
    else: st.info(f"Dati Cosφ non disponibili o insufficienti per {pompa_sel}.")
    
    st.info("""💡 **Guida alla Lettura - Elettromeccanica Inverter:**
    - **Cosφ (Fattore di Potenza):** Indica l'efficienza magnetica dello statore del motore elettrico. Un calo progressivo o brusco del Cosφ rispetto alla linea di base indica degrado dell'isolamento o possibili cortocircuiti tra le spire avvolte (situazione critica).
    - **Sforzo Meccanico (A/Hz):** L'indice calcolato dal rapporto tra Corrente assorbita e Frequenza di rete. Un aumento di questo valore indica che la pompa sta chiedendo più Ampere a parità di giri di rotazione: è un forte campanello d'allarme per usura dei cuscinetti, attriti anomali o blocco della girante idraulica.""")

def render_grafici_personalizzati(df_ro, df_uf):
    df_merged = pd.merge(df_ro, df_uf, on=['timestamp', 'date_str'], how='outer', suffixes=('_RO', '_UF')) if not df_uf.empty else df_ro.copy()
    df_merged['DataOra'] = pd.to_datetime(df_merged['date_str'])
    date_range = st.date_input("Seleziona Intervallo:", value=[df_merged['DataOra'].min().date(), df_merged['DataOra'].max().date()])
    if len(date_range) == 2:
        df_filtered = df_merged[(df_merged['DataOra'].dt.date >= date_range[0]) & (df_merged['DataOra'].dt.date <= date_range[1])]
        cols = sorted([c for c in df_filtered.select_dtypes(include=[np.number]).columns if c not in ['timestamp']])
        def_col = ['pit003_RO'] if 'pit003_RO' in cols else (['pit003'] if 'pit003' in cols else [])
        selected_cols = st.multiselect("Scegli parametri:", options=cols, default=def_col)
        if selected_cols:
            fig = crea_grafico_linee(df_filtered, 'DataOra', selected_cols, markers=True)
            if fig is not None: st.plotly_chart(fig, use_container_width=True)
            else: st.info("Nessun dato numerico valido nell'intervallo selezionato.")
            
    st.info("""💡 **Guida alla Lettura - Troubleshooting ed Esplorazione Libera:**
    Questa sezione non impone regole predefinite o calcoli automatici. Puoi sovrapporre liberamente qualsiasi parametro (idraulico, chimico o elettrico) memorizzato nel database per identificare correlazioni anomale non ovvie (ad esempio: misurare in quale misura un picco di pressione dell'alimento influenza il consumo elettrico SEC). È lo strumento ideale per la *Root Cause Analysis* in caso di anomalie di sistema.""")

def render_predittiva(df_ro, df_uf, df_nas, baseline_ro, latest_ro, baseline_uf, latest_uf, config_attuale, impianto_scelto):
    st.header("🔮 Analisi Predittiva e Stato di Salute")
    L_PERM_RO, L_DPCF01, L_DPRO, L_DP_CALZE, L_TMP_UF = baseline_ro['perm_norm_smooth'] * 0.85, 1.0, baseline_ro['dp_ro_smooth'] * 1.15, 1.0, 1.5
    
    g_ro = stima_giorni_rimanenti(df_ro, 'perm_norm_smooth', L_PERM_RO, False)
    g_dp = stima_giorni_rimanenti(df_ro, 'dp_ro_smooth', L_DPRO, True)
    g_cf = stima_giorni_rimanenti(df_ro[df_ro['dp_cf01'] > 0.05].copy(), 'dp_cf01', L_DPCF01)
    df_calze = df_ro[df_ro['pit007'] > 0.05].copy() if config_attuale["has_bag_filters"] and 'pit007' in df_ro.columns else pd.DataFrame()
    g_calze = stima_giorni_rimanenti(df_calze, 'pit007', L_DP_CALZE) if not df_calze.empty else None
    g_uf = stima_giorni_rimanenti(df_uf, 'uftmp', L_TMP_UF) if config_attuale["has_uf"] and not df_uf.empty else None

    tab_labels = ["📊 Cruscotto Salute", "💧 Membrane (Perm)", "🧱 Fouling Spaziatori (ΔP)"]
    if config_attuale["has_uf"]: tab_labels.append("🟢 Membrane UF")
    if config_attuale["has_bag_filters"]: tab_labels.append("🧦 Filtri a Calza")
    tab_labels.extend(["🗑️ Cartucce CF01", "⛨ Diagnostica Motori"])

    tab_map = dict(zip(tab_labels, st.tabs(tab_labels)))

    with tab_map["📊 Cruscotto Salute"]:
        cards = [
            ("Membrane RO (ASTM)", get_health_score(latest_ro['perm_norm_smooth'], baseline_ro['perm_norm_smooth'], L_PERM_RO, False), g_ro),
            ("Spaziatori RO (ΔP)", get_health_score(latest_ro['dp_ro_smooth'], baseline_ro['dp_ro_smooth'], L_DPRO, True), g_dp),
            ("Filtro Cartucce CF01", get_health_score(latest_ro['dp_cf01'], baseline_ro['dp_cf01'], L_DPCF01, True), g_cf)
        ]
        if config_attuale["has_uf"]:
            cards.append(("Membrane UF", 100.0 if df_uf.empty or baseline_uf['uftmp'] == 0 else get_health_score(latest_uf['uftmp'], baseline_uf['uftmp'], L_TMP_UF, True), 999 if df_uf.empty or baseline_uf['uftmp'] == 0 else g_uf))
        if config_attuale["has_bag_filters"] and 'pit007' in df_ro.columns:
            cards.append(("Filtri a Calza", get_health_score(latest_ro['pit007'], baseline_ro['pit007'], L_DP_CALZE, True), g_calze))
        
        cols = st.columns(len(cards))
        for col, (titolo, score, giorni) in zip(cols, cards):
            col.markdown(f"**{titolo}**")
            col.markdown(f"<h2 style='color:{'green' if score > 70 else ('orange' if score > 30 else 'red')}; margin:0;'>{score:.0f}%</h2>", unsafe_allow_html=True)
            col.caption("Stabile - Nessun intervento" if giorni == 999 else (f"Stimato in: {giorni} giorni" if giorni is not None else "Dati insufficienti"))
            col.progress(int(max(0, min(100, score))))

    with tab_map["💧 Membrane (Perm)"]:
        if g_ro is None: 
            st.info("Dati insufficienti per la previsione delle membrane RO.")
        else:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.metric("Indice Pulito a 25°C", f"{latest_ro['perm_norm_smooth']:.2f}", f"{latest_ro['perm_norm_smooth'] - baseline_ro['perm_norm_smooth']:+.2f}")
                
                if g_ro == 999:
                    st.success("Situazione Stabile")
                else:
                    st.warning(f"Lavaggio chimico (CIP) tra **{g_ro}** giorni.")
                    
            with col_b:
                fig = crea_grafico_previsione(df_ro, 'perm_norm_smooth', 'Previsione Fouling Membrane RO', 'Trend reale (media 24h)', 'Regressione / previsione', 30, L_PERM_RO, 'Limite CIP (85%)', yaxis_title='Permeabilità normalizzata')
                if fig: st.plotly_chart(fig, use_container_width=True)

    with tab_map["🧱 Fouling Spaziatori (ΔP)"]:
        if g_dp is None: 
            st.info("Dati insufficienti per la previsione degli spaziatori RO.")
        else:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.metric("ΔP Attuale", f"{latest_ro['dp_ro_smooth']:.2f} bar", f"{latest_ro['dp_ro_smooth'] - baseline_ro['dp_ro_smooth']:+.2f} bar", delta_color="inverse")
                
                if g_dp == 999:
                    st.success("Situazione Idraulica Stabile")
                else:
                    st.error(f"Lavaggio (CIP) stimato tra **{g_dp}** giorni.")
                    
            with col_b:
                fig = crea_grafico_previsione(df_ro, 'dp_ro_smooth', 'Previsione Fouling Spaziatori RO', 'ΔP reale (media 24h)', 'Previsione fouling', 30, L_DPRO, 'Limite rischio CIP (+15%)', baseline_ro['dp_ro_smooth'], 'Baseline installazione', 'Salto di pressione (bar)', 'up')
                if fig: st.plotly_chart(fig, use_container_width=True)

    if config_attuale["has_uf"]:
        with tab_map["🟢 Membrane UF"]:
            if df_uf.empty or g_uf is None: 
                st.info("In attesa di dati UF sufficienti...")
            else:
                fig = crea_grafico_previsione(df_uf, 'uftmp', 'Previsione TMP Ultrafiltrazione', 'TMP reale', 'Regressione', 30, L_TMP_UF, 'Limite TMP', baseline_uf['uftmp'], 'Baseline', 'TMP (bar)')
                if fig: st.plotly_chart(fig, use_container_width=True)

    if config_attuale["has_bag_filters"]:
        with tab_map["🧦 Filtri a Calza"]:
            if len(df_calze) < 3: 
                st.info("Dati insufficienti per la previsione dei filtri a calza.")
            else:
                fig = crea_grafico_previsione(df_calze, 'pit007', 'Previsione Intasamento Filtri a Calza', 'ΔP reale', 'Previsione intasamento', 20, L_DP_CALZE, 'Limite sostituzione', baseline_ro['pit007'], 'Baseline', 'ΔP (bar)', 'up')
                if fig: st.plotly_chart(fig, use_container_width=True)

    with tab_map["🗑️ Cartucce CF01"]:
        if len(df_ro[df_ro['dp_cf01'] > 0.05]) < 3: 
            st.info("Dati insufficienti per la previsione delle cartucce CF01.")
        else:
            fig = crea_grafico_previsione(df_ro[df_ro['dp_cf01'] > 0.05], 'dp_cf01', 'Previsione Intasamento Cartucce CF01', 'ΔP reale', 'Previsione', 20, L_DPCF01, 'Limite sostituzione', baseline_ro['dp_cf01'], 'Baseline', 'ΔP (bar)', 'up')
            if fig: st.plotly_chart(fig, use_container_width=True)

    with tab_map["⛨ Diagnostica Motori"]:
        if df_nas.empty: 
            st.info("In attesa di dati inverter sufficienti...")
        else:
            install_dates = PUMP_INSTALL_DATES.get(impianto_scelto, {})
            stats_pompe = []
            for nas_id, nome_pompa in config_attuale["inverters"].items():
                df_p = df_nas[(df_nas['nas_id'] == nas_id) & (pd.to_numeric(df_nas['freq'], errors='coerce') > 10)].copy()
                if nas_id in install_dates and pd.notna(pd.to_datetime(install_dates[nas_id], errors='coerce')):
                    df_p = df_p[pd.to_datetime(df_p['date_str'], errors='coerce') >= pd.to_datetime(install_dates[nas_id], errors='coerce')]
                if len(df_p) < 3 or not {'current', 'freq', 'cosphi'}.issubset(df_p.columns): continue

                indice = pd.to_numeric(df_p['current'], errors='coerce') / pd.to_numeric(df_p['freq'], errors='coerce')
                cosphi_vals = pd.to_numeric(df_p['cosphi'], errors='coerce')
                base_idx, latest_idx = indice.iloc[:3].mean(), indice.iloc[-3:].mean()
                base_cos, latest_cos = cosphi_vals.iloc[:3].mean(), cosphi_vals.iloc[-3:].mean()

                if not all(np.isfinite(v) for v in [base_idx, latest_idx, base_cos, latest_cos]) or base_idx <= 0 or base_cos <= 0: continue
                deg_mecc, deg_ele = ((latest_idx - base_idx) / base_idx) * 100, ((latest_cos - base_cos) / base_cos) * 100

                stats_pompe.append({
                    "Pompa": nome_pompa + (f" (Sostit. {install_dates[nas_id]})" if nas_id in install_dates else ""),
                    "Deriva Cosφ (Elettrica)": f"{deg_ele:+.1f}%",
                    "Stato Elettrico": "🔴 Critico" if deg_ele < -10 else ("🟡 Attenzione" if deg_ele < -5 else "🟢 Ottimale"),
                    "Degrado A/Hz (Meccanica)": f"{deg_mecc:+.1f}%",
                    "Stato Meccanico": "🔴 Critico" if deg_mecc > 15 else ("🟡 Attenzione" if deg_mecc > 8 else "🟢 Ottimale")
                })

            if stats_pompe: 
                st.dataframe(pd.DataFrame(stats_pompe), use_container_width=True)
            else: 
                st.info("Non ci sono abbastanza campioni validi per costruire il cruscotto motori.")

            st.markdown("---")
            pompa_sel = st.selectbox("Seleziona pompa per dettaglio trend storico:", options=list(config_attuale["inverters"].keys()), format_func=lambda x: f"{x} - {config_attuale['inverters'][x]}", key='predictive_motor_select')
            df_p_plot = df_nas[(df_nas['nas_id'] == pompa_sel) & (pd.to_numeric(df_nas['freq'], errors='coerce') > 10)].copy()
            if pompa_sel in install_dates and pd.notna(pd.to_datetime(install_dates[pompa_sel], errors='coerce')):
                df_p_plot = df_p_plot[pd.to_datetime(df_p_plot['date_str'], errors='coerce') >= pd.to_datetime(install_dates[pompa_sel], errors='coerce')]

            if {'current', 'freq', 'cosphi'}.issubset(df_p_plot.columns):
                df_p_plot['indice_coppia'] = pd.to_numeric(df_p_plot['current'], errors='coerce') / pd.to_numeric(df_p_plot['freq'], errors='coerce')
                if not df_p_plot.empty and df_p_plot['indice_coppia'].notna().any():
                    fig_coppia = crea_grafico_linee(df_p_plot, 'date_str', 'indice_coppia', title=f"Sforzo Meccanico Relativo (A/Hz) - {config_attuale['inverters'][pompa_sel]}", markers=True)
                    if fig_coppia:
                        fig_coppia.update_layout(yaxis_title='A/Hz')
                        st.plotly_chart(fig_coppia, use_container_width=True)
                    
                    fig_cosphi = crea_grafico_linee(df_p_plot, 'date_str', 'cosphi', title=f"Salute Magnetica Statore (Cosφ) - {config_attuale['inverters'][pompa_sel]}", markers=True)
                    if fig_cosphi:
                        baseline_c = pd.to_numeric(df_p_plot['cosphi'], errors='coerce').dropna().iloc[:3].mean()
                        if np.isfinite(baseline_c):
                            fig_cosphi.add_hline(y=baseline_c, line_dash="dash", line_color="green", annotation_text="Baseline")
                            fig_cosphi.add_hline(y=baseline_c * 0.9, line_dash="dot", line_color="red", annotation_text="Allarme (-10%)")
                        fig_cosphi.update_layout(yaxis_title='Fattore di potenza')
                        st.plotly_chart(fig_cosphi, use_container_width=True)
                        
    st.info("""💡 **Guida alla Lettura - Modello Predittivo:**
    - **Health Score (%):** Un indicatore compreso tra 0 e 100 che rappresenta la "vita utile residua" dell'asset prima di dover effettuare una manutenzione correttiva.
    - **Come calcoliamo le date:** Il sistema utilizza un algoritmo di **Regressione Lineare** (usando l'equazione $y = mx + q$) che elabora la tendenza dei dati storici. Quando la retta di regressione tracciata dal modello interseca i limiti ingegneristici predefiniti (ad esempio: una perdita del 15% sulla permeabilità iniziale), il sistema stima in modo proattivo i giorni rimanenti al lavaggio (CIP) o alla sostituzione.""")

def render_confronto(df_ro, df_uf, config_attuale):
    st.header("⚖️ Analisi Comparativa (A/B Test)")
    df_merged = pd.merge(df_ro, df_uf, on=['timestamp', 'date_str'], how='outer', suffixes=('_RO', '_UF')) if not df_uf.empty else df_ro.copy()
    df_merged['DataOra'] = pd.to_datetime(df_merged['date_str'])

    metriche_disp = {"Permeabilità Normalizzata (Fouling RO)": "perm_norm_smooth", "Salto di Pressione (ΔP RO)": "dp_ro_smooth", "Reiezione Salina (%)": "sr_norm"}
    if config_attuale["has_sec"]: metriche_disp["Consumo Specifico (SEC)"] = "sec"
    if config_attuale["has_uf"]: metriche_disp["TMP Ultrafiltrazione"] = "uftmp"
    if config_attuale["has_bag_filters"]: metriche_disp["ΔP Filtri a Calza"] = "pit007"

    kpi_sel = st.selectbox("📊 Seleziona il Parametro da analizzare:", list(metriche_disp.keys()))
    col_kpi = metriche_disp[kpi_sel]

    col1, col2 = st.columns(2)
    with col1: date_A = st.date_input("Date Periodo A:", value=[df_merged['DataOra'].min().date(), df_merged['DataOra'].min().date() + datetime.timedelta(days=7)], key='dA')
    with col2: date_B = st.date_input("Date Periodo B:", value=[df_merged['DataOra'].max().date() - datetime.timedelta(days=7), df_merged['DataOra'].max().date()], key='dB')

    if len(date_A) == 2 and len(date_B) == 2:
        df_A = df_merged[(df_merged['DataOra'].dt.date >= date_A[0]) & (df_merged['DataOra'].dt.date <= date_A[1])].dropna(subset=[col_kpi])
        df_B = df_merged[(df_merged['DataOra'].dt.date >= date_B[0]) & (df_merged['DataOra'].dt.date <= date_B[1])].dropna(subset=[col_kpi])

        if not df_A.empty and not df_B.empty:
            media_A, media_B = df_A[col_kpi].mean(), df_B[col_kpi].mean()
            delta_perc = ((media_B - media_A) / media_A) * 100 if media_A != 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Media Periodo A", f"{media_A:.2f}")
            c2.metric(f"Media Periodo B", f"{media_B:.2f}", f"{media_B - media_A:+.2f}")
            c3.metric("Variazione Percentuale", f"{delta_perc:+.1f}%", delta_color="normal" if "Permeabilità" in kpi_sel or "Reiezione" in kpi_sel else "inverse")

            fig = go.Figure()
            fig.add_trace(go.Box(y=df_A[col_kpi], name=f"Periodo A<br>({date_A[0]} - {date_A[1]})", marker_color='indianred'))
            fig.add_trace(go.Box(y=df_B[col_kpi], name=f"Periodo B<br>({date_B[0]} - {date_B[1]})", marker_color='lightseagreen'))
            fig.update_layout(title=f"Distribuzione e Stabilità: {kpi_sel}", yaxis_title=kpi_sel, boxmode='group', height=500)
            st.plotly_chart(fig, use_container_width=True)
            
    st.info("""💡 **Guida alla Lettura - Analisi Comparativa (A/B Test e Box Plot):**
    - **La "Scatola" (Box):** Rappresenta visivamente il 50% centrale delle letture di quel periodo (il range di funzionamento "normale"). Se la scatola si "allarga" molto, l'impianto sta soffrendo di instabilità idraulica.
    - **La Mediana (linea centrale):** È il valore medio effettivo di funzionamento. Se la mediana del Periodo B è palesemente disallineata da quella del Periodo A, significa che l'impianto ha subito una deviazione strutturale (es. dopo aver cambiato le cartucce o eseguito un CIP).
    - **I Puntini (Outliers):** Identificano singoli campioni anomali, fuori scala rispetto al normale ciclo produttivo (ad esempio: colpi d'ariete, partenze repentine dell'inverter). Più puntini vedi, più l'infrastruttura ha subito shock termici o idraulici.""")

# =========================================================
# MAIN DASHBOARD ENTRY POINT
# =========================================================

def render_atm(impianto_scelto):
    st.header("🏢 Telemetria ATM (Distribuito)")
    
    # Mappatura per filtrare per impianto (basata sulla logica usata nello scraper)
    nome_impianto = "Kaktus" if "Kaktus" in impianto_scelto else "Pingwe"
    
    try:
        from supabase import create_client
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # Recupero dati per l'impianto specifico
        res = supabase.table("storico_atm").select("*").eq("impianto", nome_impianto).order("data_rif", desc=True).execute()
        df_atm = pd.DataFrame(res.data)
        
        if df_atm.empty:
            st.info("Nessun dato ATM trovato per questo impianto.")
            return

        # Visualizzazione Metriche
        col1, col2 = st.columns(2)
        totale_litri = df_atm['litri_erogati'].sum()
        col1.metric("Totale Litri Erogati", f"{totale_litri:,.0f} L")
        col2.metric("Media Giornaliera", f"{df_atm['litri_erogati'].mean():,.0f} L/giorno")
        
        # Grafico
        fig = px.bar(df_atm, x="data_rif", y="litri_erogati", color="atm_id", title=f"Distribuzione Erogazioni - {nome_impianto}")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabella
        st.dataframe(df_atm[['data_rif', 'atm_id', 'litri_erogati']], use_container_width=True)
        
    except Exception as e:
        st.error(f"Errore caricamento dati ATM: {e}")

# =========================================================
# MAIN DASHBOARD ENTRY POINT
# =========================================================
if __name__ == '__main__':
    st.set_page_config(page_title="Water Partners Fleet Management", layout="wide")

    st.sidebar.image("https://img.icons8.com/color/96/000000/globe.png", width=60)
    st.sidebar.title("Gestione Flotta")
    
    impianto_scelto = st.sidebar.selectbox("🌍 Seleziona Impianto:", list(CONFIG_IMPIANTI.keys()))
    config_attuale = CONFIG_IMPIANTI[impianto_scelto]

    menu_opzioni = ["🔵 Osmosi Inversa (RO)", "⚡ Inverter & Pompe", "📈 Grafici Personalizzati", 
                    "🔮 Manutenzione Predittiva", "⚖️ Confronto Periodi", "🏢 Dati ATM", "📄 Produzione PDF"]
    if config_attuale["has_uf"]: 
        menu_opzioni.insert(1, "🟢 Ultrafiltrazione (UF)")
        
    sezione_selezionata = st.sidebar.radio("Seleziona Area Analisi:", menu_opzioni)
    
    df_ro_raw, df_uf, df_nas, source_msg = load_data(impianto_scelto)
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Origine Dati: {source_msg}")

    if df_ro_raw.empty:
        st.info(f"Nessun dato registrato per {impianto_scelto}. In attesa dei log...")
    else:
        df_ro = calcola_metriche_derivate(df_ro_raw)
        latest_ro, baseline_ro = df_ro.iloc[-1], df_ro.iloc[0]
        latest_uf, baseline_uf = (df_uf.iloc[-1], df_uf.iloc[0]) if config_attuale["has_uf"] and not df_uf.empty else (pd.Series({'fit001': 0.0, 'uftmp': 0.0, 'dpscf': 0.0}), pd.Series({'fit001': 0.0, 'uftmp': 0.0, 'dpscf': 0.0}))

        st.title(f"Sistema di Monitoraggio - {impianto_scelto[2:]}")
        
        if sezione_selezionata == "🔵 Osmosi Inversa (RO)":
            render_osmosi(df_ro, baseline_ro, latest_ro, config_attuale, impianto_scelto)
        elif sezione_selezionata == "🟢 Ultrafiltrazione (UF)":
            render_uf(df_uf, baseline_uf, latest_uf, impianto_scelto)
        elif sezione_selezionata == "⚡ Inverter & Pompe":
            render_inverter(df_nas, config_attuale, impianto_scelto)
        elif sezione_selezionata == "📈 Grafici Personalizzati":
            render_grafici_personalizzati(df_ro, df_uf)
        elif sezione_selezionata == "🔮 Manutenzione Predittiva":
            render_predittiva(df_ro, df_uf, df_nas, baseline_ro, latest_ro, baseline_uf, latest_uf, config_attuale, impianto_scelto)
        elif sezione_selezionata == "⚖️ Confronto Periodi":
            render_confronto(df_ro, df_uf, config_attuale)
        elif sezione_selezionata == "🏢 Dati ATM":
            render_atm(impianto_scelto)
        elif sezione_selezionata == "📄 Produzione PDF":
            render_produzione_pdf(impianto_scelto)