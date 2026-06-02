import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# CONFIGURAZIONI E MAPPE ASSET
# =========================================================
DB_NAME = "kaktus_analytics.db"

INVERTER_MAP = {
    'NAS1': 'Pompa HP 1 (RO)',
    'NAS2': 'Pompa HP 2 (RO)',
    'NAS3': 'Pompa HP 3 (RO)',
    'NAS4': 'Pompa HP 4 (RO)',
    'NAS5': 'Pompa Pozzo Kaktus',
    'NAS6': 'Pompa Alimento (RO)',
    'NAS11': 'Pompa Travaso TK10-3',
    'NAS12': 'Pompa Pozzo Toninho',
    'NAS13': 'Pompa Travaso TK11-3'
}

# --- STORICO SOSTITUZIONI ASSET (RESET BASELINE PREDITTIVA) ---
PUMP_INSTALL_DATES = {
    # 'NAS5': '2026-05-27'
}

# =========================================================
# HELPER PREDITTIVI
# =========================================================
def stima_giorni_rimanenti(df, col_y, limite, is_max_limit=True):
    if len(df) < 3: return None
    x, y = df['timestamp'].values, df[col_y].values
    slope, intercept = np.polyfit(x, y, 1)
    if (is_max_limit and slope <= 0) or (not is_max_limit and slope >= 0): return 999 
    giorni = int(((limite - intercept) / slope - x[-1]) / 86400)
    return max(0, giorni)

def get_health_score(valore_attuale, baseline, limite, is_max_limit=True):
    if is_max_limit:
        score = 100 - ((valore_attuale - baseline) / (limite - baseline) * 100)
    else:
        score = 100 - ((baseline - valore_attuale) / (baseline - limite) * 100)
    return max(0, min(100, score))

# =========================================================
# MOTORE DATI: IBRIDO (CLOUD / EDGE)
# =========================================================
@st.cache_data(ttl=300) 
def load_data():
    try:
        from supabase import create_client, Client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(url, key)
        
        res_ro = supabase.table("storico_ro").select("*").order("timestamp").execute()
        res_uf = supabase.table("storico_uf").select("*").order("timestamp").execute()
        res_nas = supabase.table("storico_nastec").select("*").order("timestamp").execute()
        
        return pd.DataFrame(res_ro.data), pd.DataFrame(res_uf.data), pd.DataFrame(res_nas.data), "☁️ Cloud Supabase"
    
    except Exception as e:
        # Fallback locale (a prova di crash se il file è vuoto)
        print(f"Tentativo Cloud Fallito: {e}")
        conn = sqlite3.connect(DB_NAME)
        try:
            df_ro = pd.read_sql_query("SELECT * FROM storico_ro ORDER BY timestamp ASC", conn)
            df_uf = pd.read_sql_query("SELECT * FROM storico_uf ORDER BY timestamp ASC", conn)
            df_nas = pd.read_sql_query("SELECT * FROM storico_nastec ORDER BY timestamp ASC", conn)
        except Exception: # <-- DEVE ESSERE COSI'
            df_ro, df_uf, df_nas = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        conn.close()
        return df_ro, df_uf, df_nas, "🖥️ Locale SQLite"

# =========================================================
# DASHBOARD STREAMLIT
# =========================================================
if __name__ == '__main__':
    st.set_page_config(page_title="Kaktus GW012 Analytics", layout="wide")

    st.sidebar.image("https://img.icons8.com/color/96/000000/cactus.png", width=60)
    st.sidebar.title("Kaktus GW012")

    impianto_selezionato = st.sidebar.radio("Seleziona Area Impianto:", [
        "🔵 Osmosi Inversa (RO)", 
        "🟢 Ultrafiltrazione (UF)", 
        "⚡ Inverter & Pompe", 
        "📈 Grafici Personalizzati",
        "🔮 Manutenzione Predittiva"
    ])
    
    df_ro, df_uf, df_nas, source_msg = load_data()
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Origine Dati: {source_msg}")

    if df_ro.empty:
        st.info("Nessun dato nel database. Avvia il bot downloader o attendi la ricezione dei log...")
    else:
        # =================================================================
        # NORMALIZZAZIONE AVANZATA ASTM D4516 E MEDIA MOBILE
        # =================================================================
        df_ro['tcf'] = np.where(df_ro['tit001'] > 0, np.exp(2640 * (1 / 298.15 - 1 / (df_ro['tit001'] + 273.15))), 1.0)
        
        Y = df_ro['recovery'] / 100.0
        Y = np.clip(Y, 0.01, 0.95) 
        FCS = -np.log(1 - Y) / Y
        pi_feed = df_ro['ait001'] * 0.35
        pi_avg = pi_feed * FCS
        pi_perm = (df_ro['ait002'] / 1000.0) * 0.35 
        delta_pi = pi_avg - pi_perm
        
        # Gestione retroattiva di vecchi dati mancanti
        if 'pit004' not in df_ro.columns: df_ro['pit004'] = 0.0
        p_out = np.where(df_ro['pit004'] > 0, df_ro['pit004'], df_ro['pit003'] - 1.5)
        
        df_ro['p_media'] = (df_ro['pit003'] + p_out) / 2.0
        df_ro['ndp'] = df_ro['p_media'] - delta_pi
        df_ro['ndp'] = np.where(df_ro['ndp'] <= 0.1, 0.1, df_ro['ndp']) 
        
        df_ro['perm_norm'] = df_ro['fit001'] / (df_ro['ndp'] * df_ro['tcf'])
        # Filtro rumore valvole/PID (Media Mobile a 24 letture)
        df_ro['perm_norm_smooth'] = df_ro['perm_norm'].rolling(window=24, min_periods=1).mean()
        
        df_ro['sp'] = 100 - df_ro['salt_rejection']
        df_ro['nsp'] = df_ro['sp'] / df_ro['tcf']
        df_ro['sr_norm'] = 100 - df_ro['nsp']
        
        if 'dp_cf01' not in df_ro.columns: df_ro['dp_cf01'] = df_ro['pit001'] - df_ro['pit002']
        if 'dp_ro' not in df_ro.columns: df_ro['dp_ro'] = df_ro['pit003'] - df_ro['pit004']

        latest_ro, baseline_ro = df_ro.iloc[-1], df_ro.iloc[0]
        latest_uf, baseline_uf = df_uf.iloc[-1], df_uf.iloc[0]
        
        st.title("Sistema di Monitoraggio & Predizione - Capo Verde")
        
        # ---------------------------------------------------------
        if impianto_selezionato == "🔵 Osmosi Inversa (RO)":
            st.header("Analisi Osmosi Inversa (Dati Normalizzati)")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Recovery", f"{latest_ro['recovery']:.1f} %", f"{latest_ro['recovery'] - baseline_ro['recovery']:+.1f}%")
            c2.metric("Reiezione (Norm. 25°C)", f"{latest_ro['sr_norm']:.2f} %", f"{latest_ro['sr_norm'] - baseline_ro['sr_norm']:+.2f}%")
            c3.metric("Consumo SEC", f"{latest_ro['sec']:.2f} kWh/m³", f"{latest_ro['sec'] - baseline_ro['sec']:+.2f}", delta_color="inverse")
            c4.metric("ΔP CF01", f"{latest_ro['dp_cf01']:.2f} bar", f"{latest_ro['dp_cf01'] - baseline_ro['dp_cf01']:+.2f}", delta_color="inverse")
            c5.metric("ΔP Membrane", f"{latest_ro['dp_ro']:.2f} bar", f"{latest_ro['dp_ro'] - baseline_ro['dp_ro']:+.2f}", delta_color="inverse")
            
            tab1, tab2 = st.tabs(["Grafici di Tendenza", "Dati Tabellari"])
            with tab1:
                fig_perm = go.Figure()
                fig_perm.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['perm_norm'], mode='markers+lines', name='Dato Orario (Rumore Idraulico)', line=dict(color='lightblue', width=1)))
                fig_perm.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['perm_norm_smooth'], mode='lines', name='Trend Reale (Media 24h)', line=dict(color='darkblue', width=4)))
                fig_perm.update_layout(title='Fouling: Indice di Permeabilità ASTM (Media Mobile)', yaxis_title='Permeabilità (m³/h/bar)')
                st.plotly_chart(fig_perm, use_container_width=True)
                
                fig_press = go.Figure()
                fig_press.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['fit001'], name='Permeato (m³/h)', mode='lines+markers'))
                fig_press.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['pit003'], name='P. Ingresso (bar)', yaxis='y2'))
                fig_press.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=df_ro['pit004'], name='P. Uscita (bar)', yaxis='y2', line=dict(dash='dot')))
                fig_press.update_layout(title='Dinamica Pressioni Idrauliche', yaxis=dict(title='m³/h'), yaxis2=dict(title='bar', overlaying='y', side='right'))
                st.plotly_chart(fig_press, use_container_width=True)
            with tab2: st.dataframe(df_ro, use_container_width=True)

        # ---------------------------------------------------------
        elif impianto_selezionato == "🟢 Ultrafiltrazione (UF)":
            st.header("Analisi Ultrafiltrazione")
            c1, c2, c3 = st.columns(3)
            c1.metric("Flusso UF", f"{latest_uf['fit001']:.2f} m³/h", f"{latest_uf['fit001'] - baseline_uf['fit001']:+.2f}")
            c2.metric("TMP UF", f"{latest_uf['uftmp']:.2f} bar", f"{latest_uf['uftmp'] - baseline_uf['uftmp']:+.2f}", delta_color="inverse")
            c3.metric("ΔP Filtro", f"{latest_uf['dpscf']:.2f} bar", f"{latest_uf['dpscf'] - baseline_uf['dpscf']:+.2f}", delta_color="inverse")
            st.plotly_chart(px.line(df_uf, x='date_str', y=['uftmp', 'dpscf'], markers=True, title="Trend Pressioni UF"), use_container_width=True)

        # ---------------------------------------------------------
        elif impianto_selezionato == "⚡ Inverter & Pompe":
            st.header("Stato Flotta Inverter Nastec")
            latest_ts = df_nas['timestamp'].max()
            df_nas_latest = df_nas[df_nas['timestamp'] == latest_ts].copy()
            df_nas_latest['Nome Pompa'] = df_nas_latest['nas_id'].map(INVERTER_MAP)
            st.dataframe(df_nas_latest[['Nome Pompa', 'status', 'freq', 'current', 'power', 'cosphi']], use_container_width=True)

        # ---------------------------------------------------------
        elif impianto_selezionato == "📈 Grafici Personalizzati":
            st.header("Analisi Libera")
            df_merged = pd.merge(df_ro, df_uf, on=['timestamp', 'date_str'], how='outer', suffixes=('_RO', '_UF'))
            df_merged['DataOra'] = pd.to_datetime(df_merged['date_str'])
            date_range = st.date_input("Seleziona Intervallo:", value=[df_merged['DataOra'].min().date(), df_merged['DataOra'].max().date()])
            if len(date_range) == 2:
                df_filtered = df_merged[(df_merged['DataOra'].dt.date >= date_range[0]) & (df_merged['DataOra'].dt.date <= date_range[1])]
                cols = sorted([c for c in df_filtered.columns if c not in ['timestamp', 'date_str', 'DataOra']])
                selected_cols = st.multiselect("Scegli parametri:", options=cols, default=['pit003_RO', 'pit004'])
                if selected_cols: st.plotly_chart(px.line(df_filtered, x='DataOra', y=selected_cols, markers=True), use_container_width=True)

        # ---------------------------------------------------------
        elif impianto_selezionato == "🔮 Manutenzione Predittiva":
            st.header("🔮 Analisi Predittiva e Stato di Salute")
            
            # Limiti
            L_PERM_RO = baseline_ro['perm_norm_smooth'] * 0.85 
            L_DPCF01 = 1.0 
            L_TMP_UF = 1.5 
            
            tab_sum, tab_ro, tab_uf, tab_cf, tab_pump = st.tabs([
                "📊 Cruscotto Salute", "💧 Membrane RO", "🟢 Membrane UF", "🗑️ Cartucce CF01", "⛨ Diagnostica Motori"
            ])
            
            with tab_sum:
                st.subheader("Stato di Salute Asset (Health Score)")
                score_ro = get_health_score(latest_ro['perm_norm_smooth'], baseline_ro['perm_norm_smooth'], L_PERM_RO, is_max_limit=False)
                score_cf = get_health_score(latest_ro['dp_cf01'], baseline_ro['dp_cf01'], L_DPCF01)
                score_uf = get_health_score(latest_uf['uftmp'], baseline_uf['uftmp'], L_TMP_UF)
                
                col1, col2, col3 = st.columns(3)
                def render_health_card(col, titolo, score, giorni):
                    col.markdown(f"**{titolo}**")
                    color = "green" if score > 70 else ("orange" if score > 30 else "red")
                    col.markdown(f"<h2 style='color:{color}; margin:0;'>{score:.0f}%</h2>", unsafe_allow_html=True)
                    if giorni == 999: col.caption("Stabile - Nessun intervento")
                    elif giorni is not None: col.caption(f"Stimato in: {giorni} giorni")
                    col.progress(int(score))
                
                g_ro = stima_giorni_rimanenti(df_ro, 'perm_norm_smooth', L_PERM_RO, is_max_limit=False)
                g_cf = stima_giorni_rimanenti(df_ro[df_ro['dp_cf01'] > 0.05], 'dp_cf01', L_DPCF01)
                g_uf = stima_giorni_rimanenti(df_uf, 'uftmp', L_TMP_UF)
                
                render_health_card(col1, "Membrane RO (ASTM)", score_ro, g_ro)
                render_health_card(col2, "Filtro a Cartucce CF01", score_cf, g_cf)
                render_health_card(col3, "Membrane UF (TMP)", score_uf, g_uf)
                
            with tab_ro:
                st.subheader("Fouling Forecast (Filtrazione ASTM Smooth)")
                if g_ro is not None:
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.metric("Indice Pulito a 25°C", f"{latest_ro['perm_norm_smooth']:.2f}", f"{latest_ro['perm_norm_smooth'] - baseline_ro['perm_norm_smooth']:.2f}")
                        if g_ro == 999: st.success("Situazione Stabile")
                        else: st.warning(f"Lavaggio chimico (CIP) tra **{g_ro}** giorni.")
                    with col_b:
                        x, y = df_ro['timestamp'].values, df_ro['perm_norm_smooth'].values
                        slope, intercept = np.polyfit(x, y, 1)
                        fut_x = np.linspace(x[0], x[-1] + (30 * 86400), 100)
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=pd.to_datetime(df_ro['date_str']), y=y, name='Trend Reale'))
                        fig.add_trace(go.Scatter(x=[datetime.datetime.fromtimestamp(ts) for ts in fut_x], y=slope*fut_x+intercept, line=dict(dash='dash'), name='Previsione'))
                        fig.add_hline(y=L_PERM_RO, line_color='red', annotation_text="Limite CIP (85%)")
                        st.plotly_chart(fig, use_container_width=True)

            with tab_uf:
                st.subheader("Fouling Forecast: Membrane Ultrafiltrazione")
                if g_uf is not None:
                    x, y = df_uf['timestamp'].values, df_uf['uftmp'].values
                    slope, intercept = np.polyfit(x, y, 1)
                    fut_x = np.linspace(x[0], x[-1] + (30 * 86400), 100)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=pd.to_datetime(df_uf['date_str']), y=y, name='TMP'))
                    fig.add_trace(go.Scatter(x=[datetime.datetime.fromtimestamp(ts) for ts in fut_x], y=slope*fut_x+intercept, line=dict(dash='dash'), name='Previsione'))
                    fig.add_hline(y=L_TMP_UF, line_color='red')
                    st.plotly_chart(fig, use_container_width=True)

            with tab_cf:
                st.subheader("Intasamento Filtro Cartucce CF01")
                df_cf = df_ro[df_ro['dp_cf01'] > 0.05] 
                if g_cf is not None and len(df_cf) >= 3:
                    x, y = df_cf['timestamp'].values, df_cf['dp_cf01'].values
                    slope, intercept = np.polyfit(x, y, 1)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=pd.to_datetime(df_cf['date_str']), y=y, name='Reale ΔP'))
                    if slope > 0:
                        fut_x = np.linspace(x[0], x[-1] + (20 * 86400), 100)
                        fig.add_trace(go.Scatter(x=[datetime.datetime.fromtimestamp(ts) for ts in fut_x], y=slope*fut_x+intercept, line=dict(dash='dash'), name='Previsione'))
                    fig.add_hline(y=L_DPCF01, line_color='red')
                    st.plotly_chart(fig, use_container_width=True)

            with tab_pump:
                st.subheader("Diagnostica Elettromeccanica Pompe")
                st.markdown("Valutazione incrociata dello sforzo meccanico (A/Hz) e della salute dello statore (Deriva Cosφ).")
                
                stats_pompe = []
                for nas_id, nome_pompa in INVERTER_MAP.items():
                    df_p = df_nas[(df_nas['nas_id'] == nas_id) & (df_nas['freq'] > 10)].copy()
                    
                    if nas_id in PUMP_INSTALL_DATES:
                        install_ts = pd.to_datetime(PUMP_INSTALL_DATES[nas_id]).timestamp()
                        df_p = df_p[df_p['timestamp'] >= install_ts]
                        
                    if len(df_p) > 2:
                        indice = df_p['current'].values / df_p['freq'].values
                        base_idx = np.mean(indice[:3]) 
                        latest_idx = np.mean(indice[-3:]) 
                        
                        cosphi_vals = df_p['cosphi'].values
                        base_cos = np.mean(cosphi_vals[:3])
                        latest_cos = np.mean(cosphi_vals[-3:])
                        
                        if base_idx > 0 and base_cos > 0:
                            deg_mecc = ((latest_idx - base_idx) / base_idx) * 100
                            deg_ele = ((latest_cos - base_cos) / base_cos) * 100 
                            
                            stato_mecc = "🔴 Critico" if deg_mecc > 15 else ("🟡 Attenzione" if deg_mecc > 8 else "🟢 Ottimale")
                            stato_ele = "🔴 Critico" if deg_ele < -10 else ("🟡 Attenzione" if deg_ele < -5 else "🟢 Ottimale")
                            
                            nota = f" (Sostit. {PUMP_INSTALL_DATES[nas_id]})" if nas_id in PUMP_INSTALL_DATES else ""
                            stats_pompe.append({
                                "Pompa": nome_pompa + nota, 
                                "Deriva Cosφ (Elettrica)": f"{deg_ele:+.1f}%", 
                                "Stato Elettrico": stato_ele,
                                "Degrado A/Hz (Meccanica)": f"{deg_mecc:+.1f}%", 
                                "Stato Meccanico": stato_mecc
                            })
                
                if stats_pompe:
                    df_stats = pd.DataFrame(stats_pompe)
                    st.dataframe(df_stats, use_container_width=True)
                
                st.markdown("---")
                pompa_sel = st.selectbox("Seleziona pompa per dettaglio trend storico:", options=list(INVERTER_MAP.keys()), format_func=lambda x: f"{x} - {INVERTER_MAP[x]}")
                df_p_plot = df_nas[(df_nas['nas_id'] == pompa_sel) & (df_nas['freq'] > 10)].copy()
                
                if pompa_sel in PUMP_INSTALL_DATES:
                    install_ts = pd.to_datetime(PUMP_INSTALL_DATES[pompa_sel]).timestamp()
                    df_p_plot = df_p_plot[df_p_plot['timestamp'] >= install_ts]

                if len(df_p_plot) > 0:
                    df_p_plot['indice_coppia'] = df_p_plot['current'] / df_p_plot['freq']
                    
                    fig_coppia = px.line(df_p_plot, x=pd.to_datetime(df_p_plot['timestamp'], unit='s'), y='indice_coppia', markers=True, title=f"Sforzo Meccanico Relativo (A/Hz) - {INVERTER_MAP[pompa_sel]}")
                    fig_coppia.update_layout(yaxis_title='A/Hz')
                    st.plotly_chart(fig_coppia, use_container_width=True)
                    
                    fig_cosphi = px.line(df_p_plot, x=pd.to_datetime(df_p_plot['timestamp'], unit='s'), y='cosphi', markers=True, title=f"Salute Magnetica Statore (Cosφ) - {INVERTER_MAP[pompa_sel]}")
                    baseline_c = df_p_plot['cosphi'].iloc[:3].mean()
                    fig_cosphi.add_hline(y=baseline_c, line_dash="dash", line_color="green", annotation_text="Baseline Installazione")
                    fig_cosphi.add_hline(y=baseline_c*0.9, line_dash="dot", line_color="red", annotation_text="Allarme (-10%)")
                    fig_cosphi.update_layout(yaxis_title='Fattore di Potenza')
                    st.plotly_chart(fig_cosphi, use_container_width=True)