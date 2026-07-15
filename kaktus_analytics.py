import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import plotly.graph_objects as go

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
        "inverters": {
            'NAS1': 'Pompa Pozzo 1 (P01)', 
            'NAS2': 'Pompa Pozzo 2 (P05)', 
            'NAS3': 'Pompa ATM Standard', 
            'NAS4': 'Pompa ATM Premium',
            'NAS5': 'Pompa Ausiliaria (NAS5)'
        }
    }
}

PUMP_INSTALL_DATES = {}


def normalizza_dataframe(df):
    """Rende coerenti colonne, date e tipi numerici provenienti da Supabase/SQLite."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    out = df.copy()
    # Plotly/Narwhals non gestisce bene DataFrame con nomi colonna duplicati.
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
            # Conserva le colonne realmente testuali; converte quelle numeriche o quasi numeriche.
            if converted.notna().sum() >= out[col].notna().sum() * 0.8:
                out[col] = converted

    if 'date_str' in out.columns:
        out = out.dropna(subset=['date_str']).sort_values('date_str').reset_index(drop=True)
    elif 'timestamp' in out.columns:
        out = out.sort_values('timestamp').reset_index(drop=True)

    return out


def crea_grafico_linee(df, x_col, y_cols, title=None, markers=False):
    """Crea un grafico lineare senza Plotly Express, evitando l'errore Narwhals/native_namespace."""
    if isinstance(y_cols, str):
        y_cols = [y_cols]

    y_cols = [col for col in y_cols if col in df.columns]
    if x_col not in df.columns or not y_cols:
        return None

    dati = df[[x_col] + y_cols].copy()
    dati = dati.loc[:, ~dati.columns.duplicated()]

    if x_col in {'date_str', 'DataOra'}:
        dati[x_col] = pd.to_datetime(dati[x_col], errors='coerce')

    for col in y_cols:
        dati[col] = pd.to_numeric(dati[col], errors='coerce')

    dati = dati.dropna(subset=[x_col])
    dati = dati.dropna(subset=y_cols, how='all')
    if dati.empty:
        return None

    fig = go.Figure()
    mode = 'lines+markers' if markers else 'lines'
    for col in y_cols:
        fig.add_trace(go.Scatter(
            x=dati[x_col],
            y=dati[col],
            mode=mode,
            name=col,
            connectgaps=False
        ))

    fig.update_layout(
        title=title,
        xaxis_title=None,
        yaxis_title=None,
        legend_title_text='',
        hovermode='x unified',
        margin=dict(l=20, r=20, t=55 if title else 20, b=20)
    )
    return fig


def stima_giorni_rimanenti(df, col_y, limite, is_max_limit=True):
    if df is None or len(df) < 3 or col_y not in df.columns:
        return None

    dati = df.copy()
    if 'timestamp' in dati.columns:
        x = pd.to_numeric(dati['timestamp'], errors='coerce')
    elif 'date_str' in dati.columns:
        date = pd.to_datetime(dati['date_str'], errors='coerce')
        x = date.astype('int64') / 1_000_000_000
    else:
        return None

    y = pd.to_numeric(dati[col_y], errors='coerce')
    validi = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    x = x[validi].to_numpy(dtype=float)
    y = y[validi].to_numpy(dtype=float)

    if len(x) < 3 or np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return 999

    # Lavora in giorni dal primo campione: è più stabile dei timestamp Unix molto grandi.
    x_giorni = (x - x[0]) / 86400.0
    try:
        slope, intercept = np.polyfit(x_giorni, y, 1)
    except (TypeError, ValueError, np.linalg.LinAlgError):
        return None

    if not np.isfinite(slope) or abs(slope) < 1e-12:
        return 999
    if (is_max_limit and slope <= 0) or (not is_max_limit and slope >= 0):
        return 999

    giorno_limite = (float(limite) - intercept) / slope
    giorni = int(np.ceil(giorno_limite - x_giorni[-1]))
    return max(0, giorni)

def get_health_score(valore_attuale, baseline, limite, is_max_limit=True):
    try:
        valore_attuale = float(valore_attuale)
        baseline = float(baseline)
        limite = float(limite)
    except (TypeError, ValueError):
        return 0.0

    denominatore = (limite - baseline) if is_max_limit else (baseline - limite)
    if not np.isfinite(denominatore) or abs(denominatore) < 1e-12:
        return 100.0

    if is_max_limit:
        score = 100 - ((valore_attuale - baseline) / denominatore * 100)
    else:
        score = 100 - ((baseline - valore_attuale) / denominatore * 100)

    if not np.isfinite(score):
        return 0.0
    return max(0.0, min(100.0, score))

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

if __name__ == '__main__':
    st.set_page_config(page_title="Water Partners Fleet Management", layout="wide")

    st.sidebar.image("https://img.icons8.com/color/96/000000/globe.png", width=60)
    st.sidebar.title("Gestione Flotta")
    
    impianto_scelto = st.sidebar.selectbox("🌍 Seleziona Impianto:", list(CONFIG_IMPIANTI.keys()))
    config_attuale = CONFIG_IMPIANTI[impianto_scelto]

    menu_opzioni = ["🔵 Osmosi Inversa (RO)", "⚡ Inverter & Pompe", "📈 Grafici Personalizzati", "🔮 Manutenzione Predittiva", "⚖️ Confronto Periodi"]
    if config_attuale["has_uf"]:
        menu_opzioni.insert(1, "🟢 Ultrafiltrazione (UF)")
        
    sezione_selezionata = st.sidebar.radio("Seleziona Area Analisi:", menu_opzioni)
    
    df_ro, df_uf, df_nas, source_msg = load_data(impianto_scelto)
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Origine Dati: {source_msg}")

    if df_ro.empty:
        st.info(f"Nessun dato registrato per {impianto_scelto}. In attesa dei log...")
    else:
        df_ro['tcf'] = np.where(df_ro['tit001'] > 0, np.exp(2640 * (1 / 298.15 - 1 / (df_ro['tit001'] + 273.15))), 1.0)
        Y = np.clip(df_ro['recovery'] / 100.0, 0.01, 0.95) 
        FCS = -np.log(1 - Y) / Y
        pi_feed = df_ro['ait001'] * 0.35
        pi_avg = pi_feed * FCS
        pi_perm = (df_ro['ait002'] / 1000.0) * 0.35 
        delta_pi = pi_avg - pi_perm
        
        if 'pit004' not in df_ro.columns: df_ro['pit004'] = 0.0
        p_out = np.where(df_ro['pit004'] > 0, df_ro['pit004'], df_ro['pit003'] - 1.5)
        
        df_ro['p_media'] = (df_ro['pit003'] + p_out) / 2.0
        df_ro['ndp'] = np.where(df_ro['p_media'] - delta_pi <= 0.1, 0.1, df_ro['p_media'] - delta_pi) 
        df_ro['perm_norm'] = df_ro['fit001'] / (df_ro['ndp'] * df_ro['tcf'])
        df_ro['perm_norm_smooth'] = df_ro['perm_norm'].rolling(window=24, min_periods=1).mean()
        
        df_ro['nsp'] = (100 - df_ro['salt_rejection']) / df_ro['tcf']
        df_ro['sr_norm'] = 100 - df_ro['nsp']
        
        if 'dp_cf01' not in df_ro.columns: df_ro['dp_cf01'] = df_ro['pit001'] - df_ro['pit002']
        if 'dp_ro' not in df_ro.columns: df_ro['dp_ro'] = df_ro['pit003'] - df_ro['pit004']
        df_ro['dp_ro_smooth'] = df_ro['dp_ro'].rolling(window=24, min_periods=1).mean()

        latest_ro, baseline_ro = df_ro.iloc[-1], df_ro.iloc[0]
        
        if config_attuale["has_uf"] and not df_uf.empty:
            latest_uf, baseline_uf = df_uf.iloc[-1], df_uf.iloc[0]
        else:
            latest_uf, baseline_uf = pd.Series({'fit001': 0.0, 'uftmp': 0.0, 'dpscf': 0.0}), pd.Series({'fit001': 0.0, 'uftmp': 0.0, 'dpscf': 0.0})

        st.title(f"Sistema di Monitoraggio - {impianto_scelto[2:]}")
        
        # ---------------------------------------------------------
        if sezione_selezionata == "🔵 Osmosi Inversa (RO)":
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Recovery", f"{latest_ro['recovery']:.1f} %", f"{latest_ro['recovery'] - baseline_ro['recovery']:+.1f}%")
            c2.metric("Reiezione (Norm)", f"{latest_ro['sr_norm']:.2f} %", f"{latest_ro['sr_norm'] - baseline_ro['sr_norm']:+.2f}%")
            
            # Dinamica: Mostra DP Calze per Pingwe, SEC per Kaktus
            if config_attuale["has_bag_filters"]:
                c3.metric("ΔP Filtri a Calza", f"{latest_ro['pit007']:.2f} bar", f"{latest_ro['pit007'] - baseline_ro['pit007']:+.2f}", delta_color="inverse")
            else:
                c3.metric("Consumo SEC", f"{latest_ro['sec']:.2f} kWh/m³", f"{latest_ro['sec'] - baseline_ro['sec']:+.2f}", delta_color="inverse")
                
            c4.metric("ΔP Cartuccia CF01", f"{latest_ro['dp_cf01']:.2f} bar", f"{latest_ro['dp_cf01'] - baseline_ro['dp_cf01']:+.2f}", delta_color="inverse")
            c5.metric("ΔP Membrane", f"{latest_ro['dp_ro']:.2f} bar", f"{latest_ro['dp_ro'] - baseline_ro['dp_ro']:+.2f}", delta_color="inverse")
            
            st.markdown("---")
            st.subheader("Parametri Acqua (Extra)")
            col_ph, col_cond, col_flow = st.columns(3)
            col_ph.metric("pH Permeato", f"{latest_ro['ait005']:.2f}" if latest_ro['ait005'] > 0 else "N/D")
            col_cond.metric("Conducibilità Permeato", f"{latest_ro['ait002']:.1f} µS/cm")
            if config_attuale["has_bag_filters"]:
                col_flow.metric("Flusso Potabile (Uscita)", f"{latest_ro['fit005']:.2f} m³/h")
            else:
                col_flow.metric("Flusso Concentrato", f"{latest_ro['fit002']:.2f} m³/h")

            tab1, tab2 = st.tabs(["Grafici di Tendenza", "Dati Tabellari"])
            with tab1:
                fig_perm = go.Figure()
                fig_perm.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['perm_norm'], mode='markers+lines', name='Dato Orario', line=dict(color='lightblue', width=1)))
                fig_perm.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['perm_norm_smooth'], mode='lines', name='Trend', line=dict(color='darkblue', width=4)))
                st.plotly_chart(fig_perm, use_container_width=True)
            with tab2: st.dataframe(df_ro, use_container_width=True)

        # ---------------------------------------------------------
        elif sezione_selezionata == "🟢 Ultrafiltrazione (UF)":
            if df_uf.empty: st.warning("Nessun dato UF.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Flusso UF", f"{latest_uf['fit001']:.2f} m³/h", f"{latest_uf['fit001'] - baseline_uf['fit001']:+.2f}")
                c2.metric("TMP UF", f"{latest_uf['uftmp']:.2f} bar", f"{latest_uf['uftmp'] - baseline_uf['uftmp']:+.2f}", delta_color="inverse")
                c3.metric("ΔP Filtro", f"{latest_uf['dpscf']:.2f} bar", f"{latest_uf['dpscf'] - baseline_uf['dpscf']:+.2f}", delta_color="inverse")
                fig = crea_grafico_linee(df_uf, 'date_str', ['uftmp', 'dpscf'], title="Trend Pressioni UF", markers=True)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Dati UF insufficienti per il grafico.")

        # ---------------------------------------------------------
        elif sezione_selezionata == "⚡ Inverter & Pompe":
            if df_nas.empty: 
                st.warning("Nessun dato inverter.")
            else:
                latest_ts = df_nas['timestamp'].max()
                df_nas_latest = df_nas[df_nas['timestamp'] == latest_ts].copy()
                df_nas_latest['Nome Pompa'] = df_nas_latest['nas_id'].map(config_attuale["inverters"]).fillna("Pompa Sconosciuta")
                st.dataframe(df_nas_latest[['Nome Pompa', 'status', 'freq', 'current', 'power', 'cosphi']], use_container_width=True)
                
                st.subheader("Analisi Salute Statore")
                pompa_sel = st.selectbox("Seleziona pompa per trend Cosφ:", options=list(config_attuale["inverters"].keys()), format_func=lambda x: f"{x} - {config_attuale['inverters'][x]}")
                df_p_plot = df_nas[(df_nas['nas_id'] == pompa_sel) & (df_nas['freq'] > 1.0)].copy()
                
                if not df_p_plot.empty and 'cosphi' in df_p_plot.columns and df_p_plot['cosphi'].notnull().any():
                    fig = crea_grafico_linee(df_p_plot, 'date_str', 'cosphi', title=f"Trend Cosφ - {pompa_sel}")
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"Dati Cosφ non validi per {pompa_sel}.")
                else:
                    st.info(f"Dati Cosφ non disponibili o insufficienti per {pompa_sel}.")

        # ---------------------------------------------------------
        elif sezione_selezionata == "📈 Grafici Personalizzati":
            df_merged = pd.merge(df_ro, df_uf, on=['timestamp', 'date_str'], how='outer', suffixes=('_RO', '_UF')) if not df_uf.empty else df_ro.copy()
            df_merged['DataOra'] = pd.to_datetime(df_merged['date_str'])
            date_range = st.date_input("Seleziona Intervallo:", value=[df_merged['DataOra'].min().date(), df_merged['DataOra'].max().date()])
            if len(date_range) == 2:
                df_filtered = df_merged[(df_merged['DataOra'].dt.date >= date_range[0]) & (df_merged['DataOra'].dt.date <= date_range[1])]
                cols = sorted([
                    c for c in df_filtered.select_dtypes(include=[np.number]).columns
                    if c not in ['timestamp']
                ])
                def_col = ['pit003_RO'] if 'pit003_RO' in cols else (['pit003'] if 'pit003' in cols else [])
                selected_cols = st.multiselect("Scegli parametri:", options=cols, default=def_col)
                if selected_cols:
                    fig = crea_grafico_linee(df_filtered, 'DataOra', selected_cols, markers=True)
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Nessun dato numerico valido nell'intervallo selezionato.")

        # ---------------------------------------------------------
        elif sezione_selezionata == "🔮 Manutenzione Predittiva":
            L_PERM_RO = baseline_ro['perm_norm_smooth'] * 0.85 
            L_DPCF01 = 1.0 
            L_DPRO = baseline_ro['dp_ro_smooth'] * 1.15 
            L_DP_CALZE = 1.0
            
            tabs = ["📊 Salute", "💧 Membrane RO", "🧱 Spaziatori (ΔP)", "🗑️ Cartucce CF01", "⛨ Motori"]
            if config_attuale["has_uf"]: tabs.insert(3, "🟢 Membrane UF")
            if config_attuale["has_bag_filters"]: tabs.insert(3, "🧦 Filtri a Calza")
            
            t = st.tabs(tabs)
            
            with t[0]:
                score_ro = get_health_score(latest_ro['perm_norm_smooth'], baseline_ro['perm_norm_smooth'], L_PERM_RO, False)
                score_dp = get_health_score(latest_ro['dp_ro_smooth'], baseline_ro['dp_ro_smooth'], L_DPRO, True)
                score_cf = get_health_score(latest_ro['dp_cf01'], baseline_ro['dp_cf01'], L_DPCF01)
                
                cols = st.columns(5 if (config_attuale["has_uf"] or config_attuale["has_bag_filters"]) else 3)
                def render_card(col, tit, sc, gg):
                    col.markdown(f"**{tit}**")
                    col.markdown(f"<h2 style='color:{'green' if sc>70 else ('orange' if sc>30 else 'red')}; margin:0;'>{sc:.0f}%</h2>", unsafe_allow_html=True)
                    col.caption("Stabile" if gg==999 else (f"Stimato in: {gg} giorni" if gg is not None else ""))
                    col.progress(int(sc))
                
                render_card(cols[0], "Membrane RO", score_ro, stima_giorni_rimanenti(df_ro, 'perm_norm_smooth', L_PERM_RO, False))
                render_card(cols[1], "Spaziatori RO", score_dp, stima_giorni_rimanenti(df_ro, 'dp_ro_smooth', L_DPRO, True))
                render_card(cols[2], "Filtro CF01", score_cf, stima_giorni_rimanenti(df_ro[df_ro['dp_cf01'] > 0.05], 'dp_cf01', L_DPCF01))
                
                if config_attuale["has_bag_filters"]:
                    score_calze = get_health_score(latest_ro['pit007'], baseline_ro['pit007'], L_DP_CALZE)
                    render_card(cols[3], "Filtri a Calza", score_calze, stima_giorni_rimanenti(df_ro[df_ro['pit007'] > 0.05], 'pit007', L_DP_CALZE))
                elif config_attuale["has_uf"]:
                    if df_uf.empty or baseline_uf['uftmp'] == 0:
                        render_card(cols[3], "Membrane UF", 100, 999)
                    else:
                        render_card(cols[3], "Membrane UF", get_health_score(latest_uf['uftmp'], baseline_uf['uftmp'], 1.5), stima_giorni_rimanenti(df_uf, 'uftmp', 1.5))

            with t[1]:
                g_ro = stima_giorni_rimanenti(df_ro, 'perm_norm_smooth', L_PERM_RO, False)
                if g_ro is not None:
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("Indice ASTM", f"{latest_ro['perm_norm_smooth']:.2f}")
                        if g_ro != 999:
                            st.warning(f"CIP tra {g_ro} gg.")
                        else:
                            st.success("Stabile")
                    with col_b:
                        fig = crea_grafico_linee(df_ro, 'date_str', 'perm_norm_smooth')
                        if fig is not None:
                            fig.add_hline(y=L_PERM_RO, line_color='red')
                            st.plotly_chart(fig, use_container_width=True)

            with t[2]:
                g_dp = stima_giorni_rimanenti(df_ro, 'dp_ro_smooth', L_DPRO, True)
                if g_dp is not None:
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("ΔP Attuale", f"{latest_ro['dp_ro_smooth']:.2f} bar")
                        if g_dp != 999:
                            st.error(f"Rischio tra {g_dp} gg.")
                        else:
                            st.success("Stabile")
                    with col_b:
                        fig = crea_grafico_linee(df_ro, 'date_str', 'dp_ro_smooth')
                        if fig is not None:
                            fig.add_hline(y=L_DPRO, line_color='red')
                            st.plotly_chart(fig, use_container_width=True)
            
            idx = 3
            if config_attuale["has_uf"]:
                with t[idx]:
                    if not df_uf.empty:
                        fig = crea_grafico_linee(df_uf, 'date_str', 'uftmp')
                        if fig is not None:
                            fig.add_hline(y=1.5, line_color='red')
                            st.plotly_chart(fig, use_container_width=True)
                idx += 1
                
            if config_attuale["has_bag_filters"]:
                with t[idx]:
                    df_calze = df_ro[df_ro['pit007'] > 0.05]
                    if len(df_calze) > 3:
                        fig = crea_grafico_linee(df_calze, 'date_str', 'pit007', title="Intasamento Filtri a Calza (ΔP)")
                        if fig is not None:
                            fig.add_hline(y=L_DP_CALZE, line_color='red')
                            st.plotly_chart(fig, use_container_width=True)
                idx += 1
                
            with t[idx]:
                df_cf = df_ro[df_ro['dp_cf01'] > 0.05]
                if len(df_cf) > 3:
                    fig = crea_grafico_linee(df_cf, 'date_str', 'dp_cf01', title="Intasamento Cartucce CF01")
                    if fig is not None:
                        fig.add_hline(y=L_DPCF01, line_color='red')
                        st.plotly_chart(fig, use_container_width=True)
            idx += 1
            
            with t[idx]:
                if not df_nas.empty:
                    pompa_sel = st.selectbox("Seleziona pompa:", options=list(config_attuale["inverters"].keys()), format_func=lambda x: f"{x} - {config_attuale['inverters'][x]}")
                    df_p_plot = df_nas[(df_nas['nas_id'] == pompa_sel) & (df_nas['freq'] > 10)].copy()
                    if not df_p_plot.empty:
                        df_p_plot['indice_coppia'] = df_p_plot['current'] / df_p_plot['freq']
                        fig = crea_grafico_linee(df_p_plot, 'date_str', 'cosphi', title="Salute Statore (Cosφ)")
                        if fig is not None:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Dati Cosφ non validi per la pompa selezionata.")

        # ---------------------------------------------------------
        elif sezione_selezionata == "⚖️ Confronto Periodi":
            st.header("⚖️ Analisi Comparativa (A/B Test)")

            if not df_uf.empty:
                df_merged = pd.merge(df_ro, df_uf, on=['timestamp', 'date_str'], how='outer', suffixes=('_RO', '_UF'))
            else:
                df_merged = df_ro.copy()
            
            df_merged['DataOra'] = pd.to_datetime(df_merged['date_str'])

            metriche_disp = {
                "Permeabilità Normalizzata (Fouling RO)": "perm_norm_smooth",
                "Salto di Pressione (ΔP RO)": "dp_ro_smooth",
                "Reiezione Salina (%)": "sr_norm"
            }
            if config_attuale["has_sec"]: metriche_disp["Consumo Specifico (SEC)"] = "sec"
            if config_attuale["has_uf"]: metriche_disp["TMP Ultrafiltrazione"] = "uftmp"
            if config_attuale["has_bag_filters"]: metriche_disp["ΔP Filtri a Calza"] = "pit007"

            kpi_sel = st.selectbox("📊 Seleziona il Parametro da analizzare:", list(metriche_disp.keys()))
            col_kpi = metriche_disp[kpi_sel]

            col1, col2 = st.columns(2)
            with col1:
                date_A = st.date_input("Date Periodo A:", value=[df_merged['DataOra'].min().date(), df_merged['DataOra'].min().date() + datetime.timedelta(days=7)], key='dA')
            with col2:
                date_B = st.date_input("Date Periodo B:", value=[df_merged['DataOra'].max().date() - datetime.timedelta(days=7), df_merged['DataOra'].max().date()], key='dB')

            if len(date_A) == 2 and len(date_B) == 2:
                df_A = df_merged[(df_merged['DataOra'].dt.date >= date_A[0]) & (df_merged['DataOra'].dt.date <= date_A[1])].dropna(subset=[col_kpi])
                df_B = df_merged[(df_merged['DataOra'].dt.date >= date_B[0]) & (df_merged['DataOra'].dt.date <= date_B[1])].dropna(subset=[col_kpi])

                if not df_A.empty and not df_B.empty:
                    media_A = df_A[col_kpi].mean()
                    media_B = df_B[col_kpi].mean()
                    delta_perc = ((media_B - media_A) / media_A) * 100 if media_A != 0 else 0
                    colore_delta = "normal" if "Permeabilità" in kpi_sel or "Reiezione" in kpi_sel else "inverse"

                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"Media Periodo A", f"{media_A:.2f}")
                    c2.metric(f"Media Periodo B", f"{media_B:.2f}", f"{media_B - media_A:+.2f}")
                    c3.metric("Variazione Percentuale", f"{delta_perc:+.1f}%", delta_color=colore_delta)

                    fig = go.Figure()
                    fig.add_trace(go.Box(y=df_A[col_kpi], name=f"Periodo A<br>({date_A[0]} - {date_A[1]})", marker_color='indianred'))
                    fig.add_trace(go.Box(y=df_B[col_kpi], name=f"Periodo B<br>({date_B[0]} - {date_B[1]})", marker_color='lightseagreen'))
                    st.plotly_chart(fig, use_container_width=True)