import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import os
import re
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


# =========================================================
# INTERFACCIA BILINGUE ITALIANO / ENGLISH
# =========================================================
_RAW_ST = st
UI_LANGUAGE = "it"


def ui_text(italiano, english):
    """Restituisce testo già localizzato per i nuovi componenti dinamici."""
    return english if UI_LANGUAGE == "en" else italiano


FLEET_OVERVIEW_KEY = "__fleet_overview__"


def _read_query_value(key, default=None):
    """Legge un valore URL mantenendo compatibilità con Streamlit 1.30+."""
    try:
        value = _RAW_ST.query_params.get(key, default)
    except (AttributeError, TypeError):
        try:
            value = _RAW_ST.experimental_get_query_params().get(key, default)
        except Exception:
            return default
    if isinstance(value, (list, tuple)):
        return value[-1] if value else default
    return value


def _write_query_values(**updates):
    """Aggiorna solo i parametri di navigazione senza cancellare gli altri."""
    clean_updates = {key: str(value) for key, value in updates.items() if value is not None}
    try:
        for key, value in clean_updates.items():
            if str(_RAW_ST.query_params.get(key, "")) != value:
                _RAW_ST.query_params[key] = value
        return
    except (AttributeError, TypeError):
        pass

    try:
        current = _RAW_ST.experimental_get_query_params()
        merged = {
            key: (value[-1] if isinstance(value, list) and value else value)
            for key, value in current.items()
        }
        if any(str(merged.get(key, "")) != value for key, value in clean_updates.items()):
            merged.update(clean_updates)
            _RAW_ST.experimental_set_query_params(**merged)
    except Exception:
        # La dashboard resta utilizzabile anche con versioni Streamlit molto vecchie;
        # in quel caso si perde soltanto la persistenza dopo un hard refresh.
        return


def _safe_rerun():
    try:
        _RAW_ST.rerun()
    except AttributeError:
        _RAW_ST.experimental_rerun()

_EXACT_TRANSLATIONS = {'N/D': 'N/A', 'Gennaio': 'January', 'Febbraio': 'February', 'Marzo': 'March', 'Aprile': 'April', 'Maggio': 'May', 'Giugno': 'June', 'Luglio': 'July', 'Agosto': 'August', 'Settembre': 'September', 'Ottobre': 'October', 'Novembre': 'November', 'Dicembre': 'December', '🌵 GW012 Kaktus (Capo Verde)': '🌵 GW012 Kaktus (Cape Verde)', '🌴 Pingwe (Zanzibar)': '🌴 Pingwe (Zanzibar)', 'Gestione Flotta': 'Fleet Management', '🌍 Seleziona Impianto:': '🌍 Select plant:', 'Seleziona Area Analisi:': 'Select analysis area:', '🔵 Osmosi Inversa (RO)': '🔵 Reverse Osmosis (RO)', '🟢 Ultrafiltrazione (UF)': '🟢 Ultrafiltration (UF)', '⚡ Inverter & Pompe': '⚡ Inverters & Pumps', '📈 Grafici Personalizzati': '📈 Custom Charts', '🔮 Manutenzione Predittiva': '🔮 Predictive Maintenance', '⚖️ Confronto Periodi': '⚖️ Period Comparison', '📊 Produzione & ATM': '📊 Production & ATM', '☁️ Cloud Supabase': '☁️ Supabase Cloud', '🖥️ Locale SQLite': '🖥️ Local SQLite', 'Recovery': 'Recovery', 'Reiezione (Norm)': 'Rejection (Norm.)', 'ΔP Filtri a Calza': 'Bag-filter ΔP', 'Consumo SEC': 'SEC consumption', 'ΔP Cartuccia CF01': 'CF01 cartridge ΔP', 'ΔP Membrane': 'Membrane ΔP', 'Parametri Acqua (Extra)': 'Water Parameters (Additional)', 'pH Permeato': 'Permeate pH', 'Conducibilità Alimento': 'Feed conductivity', 'Conducibilità Permeato': 'Permeate conductivity', 'Grafici di Tendenza': 'Trend Charts', 'Dati Tabellari ed Esportazione': 'Tabular Data and Export', '📥 Esporta Storico in formato CSV': '📥 Export history as CSV', '📥 Esporta CSV': '📥 Export CSV', 'Nessun dato UF.': 'No UF data.', 'Flusso UF': 'UF flow', 'TMP UF': 'UF TMP', 'ΔP Filtro': 'Filter ΔP', 'Trend Pressioni UF': 'UF pressure trends', 'Nessun dato inverter.': 'No inverter data.', 'Pompa': 'Pump', 'Nome Pompa': 'Pump name', 'Analisi Salute Statore': 'Stator Health Analysis', 'Seleziona pompa per trend Cosφ:': 'Select pump for Cosφ trend:', 'Seleziona Intervallo:': 'Select range:', 'Scegli parametri:': 'Select parameters:', '🔮 Analisi Predittiva e Stato di Salute': '🔮 Predictive Analysis and Health Status', '📊 Cruscotto Salute': '📊 Health Dashboard', '💧 Membrane (Perm)': '💧 Membranes (Permeability)', '🧱 Fouling Spaziatori (ΔP)': '🧱 Spacer Fouling (ΔP)', '🟢 Membrane UF': '🟢 UF Membranes', '🧦 Filtri a Calza': '🧦 Bag Filters', '🗑️ Cartucce CF01': '🗑️ CF01 Cartridges', '⛨ Diagnostica Motori': '⛨ Motor Diagnostics', 'Membrane RO (ASTM)': 'RO membranes (ASTM)', 'Spaziatori RO (ΔP)': 'RO spacers (ΔP)', 'Filtro Cartucce CF01': 'CF01 cartridge filter', 'Membrane UF': 'UF membranes', 'Filtri a Calza': 'Bag filters', 'Stabile - Nessun intervento': 'Stable — No intervention required', 'Dati insufficienti': 'Insufficient data', 'Indice Pulito a 25°C': 'Clean index at 25°C', 'Situazione Stabile': 'Stable condition', 'ΔP Attuale': 'Current ΔP', 'Situazione Idraulica Stabile': 'Stable hydraulic condition', 'Stato Elettrico': 'Electrical status', 'Stato Meccanico': 'Mechanical status', 'Deriva Cosφ (Elettrica)': 'Cosφ drift (Electrical)', 'Degrado A/Hz (Meccanica)': 'A/Hz degradation (Mechanical)', '🔴 Critico': '🔴 Critical', '🟡 Attenzione': '🟡 Warning', '🟢 Ottimale': '🟢 Optimal', 'Seleziona pompa per dettaglio trend storico:': 'Select pump for detailed historical trend:', 'Fattore di potenza': 'Power factor', '⚖️ Analisi Comparativa (A/B Test)': '⚖️ Comparative Analysis (A/B Test)', '📊 Seleziona il Parametro da analizzare:': '📊 Select the parameter to analyse:', 'Date Periodo A:': 'Period A dates:', 'Date Periodo B:': 'Period B dates:', 'Media Periodo A': 'Period A average', 'Media Periodo B': 'Period B average', 'Variazione Percentuale': 'Percentage change', 'Permeabilità Normalizzata (Fouling RO)': 'Normalised permeability (RO fouling)', 'Salto di Pressione (ΔP RO)': 'Pressure drop (RO ΔP)', 'Reiezione Salina (%)': 'Salt rejection (%)', 'Consumo Specifico (SEC)': 'Specific energy consumption (SEC)', 'TMP Ultrafiltrazione': 'Ultrafiltration TMP', '📊 Produzione e vendite ATM': '📊 Production and ATM Sales', 'Mese da analizzare:': 'Month to analyse:', 'Dati da visualizzare nel grafico:': 'Data to display in the chart:', 'Produzione': 'Production', 'Vendite ATM': 'ATM sales', 'Concentrato': 'Concentrate', 'Totale prodotto': 'Total production', 'Totale venduto ATM': 'Total ATM sales', 'Totale concentrato': 'Total concentrate', 'Media giornaliera prodotta': 'Average daily production', 'Media giornaliera venduta': 'Average daily ATM sales', 'Media giornaliera concentrato': 'Average daily concentrate', 'Medie giornaliere per periodo personalizzato': 'Daily averages for a custom period', 'Seleziona il periodo da analizzare:': 'Select the period to analyse:', 'Media produzione nel periodo': 'Average production in the period', 'Media vendite ATM nel periodo': 'Average ATM sales in the period', 'Media concentrato nel periodo': 'Average concentrate in the period', '#### Grafico del periodo selezionato': '#### Selected-period chart', '#### Grafico del mese selezionato': '#### Selected-month chart', 'Riepilogo giornaliero': 'Daily summary', 'Dettaglio produzione PDF': 'PDF production details', 'Dettaglio ATM': 'ATM details', 'Data': 'Date', 'Prodotto (m³)': 'Production (m³)', 'Concentrato (m³)': 'Concentrate (m³)', 'Venduto ATM (L)': 'ATM sales (L)', 'Venduto ATM (m³)': 'ATM sales (m³)', 'data_rif': 'Reference date', 'permeato': 'Permeate', 'concentrato': 'Concentrate', 'insolation': 'Solar irradiation', 'file_origine': 'Source file', 'litri_erogati': 'Dispensed litres', 'atm_id': 'ATM ID', 'atm_litri': 'ATM litres', 'atm_m3': 'ATM m³', '🏢 Telemetria ATM (Distribuito)': '🏢 ATM Telemetry (Distributed)', 'Totale Litri Erogati': 'Total litres dispensed', 'Media Giornaliera': 'Daily average', '📄 Analisi Produzione da PDF': '📄 PDF Production Analysis', 'Totale Permeato': 'Total permeate', 'Media Insolazione': 'Average solar irradiation', 'Flusso Permeato': 'Permeate flow', 'Flusso Concentrato': 'Concentrate flow', 'Flusso Potabile (Uscita)': 'Potable-water flow (Outlet)', 'Pompa HP 1 (RO)': 'HP pump 1 (RO)', 'Pompa HP 2 (RO)': 'HP pump 2 (RO)', 'Pompa HP 3 (RO)': 'HP pump 3 (RO)', 'Pompa HP 4 (RO)': 'HP pump 4 (RO)', 'Pompa Pozzo Kaktus': 'Kaktus well pump', 'Pompa Alimento (RO)': 'RO feed pump', 'Pompa Travaso TK10-3': 'TK10-3 transfer pump', 'Pompa Pozzo Toninho': 'Toninho well pump', 'Pompa Travaso TK11-3': 'TK11-3 transfer pump', 'Pompa Pozzo 1 (P01)': 'Well pump 1 (P01)', 'Pompa Pozzo 2 (P05)': 'Well pump 2 (P05)', 'Pompa ATM Standard': 'Standard ATM pump', 'Pompa ATM Premium': 'Premium ATM pump', 'Pompa Ausiliaria (NAS5)': 'Auxiliary pump (NAS5)', 'Pompa Sconosciuta': 'Unknown pump', 'P. Ingresso (bar)': 'Inlet pressure (bar)', 'P. Uscita (bar)': 'Outlet pressure (bar)', 'Permeato (m³/h)': 'Permeate (m³/h)', 'Portata (m³/h)': 'Flow (m³/h)', 'Pressione (bar)': 'Pressure (bar)', 'Permeabilità (m³/h/bar)': 'Permeability (m³/h/bar)', 'Permeabilità normalizzata': 'Normalised permeability', 'Salto di pressione (bar)': 'Pressure drop (bar)', 'ΔP (bar)': 'ΔP (bar)', 'Volume giornaliero (m³)': 'Daily volume (m³)', 'Dato': 'Data series', 'Baseline': 'Baseline', 'Limite': 'Limit', 'Previsione': 'Forecast', 'Regressione': 'Regression', 'Previsione fouling': 'Fouling forecast', 'Previsione intasamento': 'Clogging forecast', 'Trend reale (media 24h)': 'Actual trend (24 h average)', 'ΔP reale (media 24h)': 'Actual ΔP (24 h average)', 'ΔP reale': 'Actual ΔP', 'TMP reale': 'Actual TMP', 'Limite TMP': 'TMP limit', 'Limite sostituzione': 'Replacement limit', 'Limite CIP (85%)': 'CIP limit (85%)', 'Limite rischio CIP (+15%)': 'CIP risk limit (+15%)', 'Baseline installazione': 'Installation baseline', 'Allarme (-10%)': 'Alarm (-10%)', 'Trend (Media 24h)': 'Trend (24 h average)', 'Dato Orario': 'Hourly data', 'm³/giorno': 'm³/day', 'L/giorno': 'L/day', "💡 **Guida alla Lettura - Osmosi Inversa (RO):**\n    - **Recovery (Recupero):** La percentuale di acqua di alimento trasformata in permeato (acqua dolce).\n    - **Reiezione Salina (Normalizzata):** Indica l'efficienza chimica della membrana nel bloccare i sali, depurata matematicamente dalle fluttuazioni di temperatura. Per calcolarla si usa il fattore $TCF = \\exp\\left[2640 \\cdot \\left(\\frac{1}{298.15} - \\frac{1}{T_{acqua} + 273.15}\\right)\\right]$. Valori ottimali: > 98%.\n    - **Consumo SEC:** Energia Specifica Consumata (kWh/m³). Rappresenta quanta energia è necessaria per produrre un singolo metro cubo di acqua dolce.\n    - **ΔP (Salto di Pressione):** Misura la perdita di carico idraulica tra l'ingresso e l'uscita dei vessel. Un aumento continuo segnala un'ostruzione fisica (fouling, bio-fouling o scaling inorganico).": "💡 **Reading Guide — Reverse Osmosis (RO):**\n    - **Recovery:** The percentage of feedwater converted into permeate (fresh water).\n    - **Normalised salt rejection:** The membrane's efficiency in retaining salts, mathematically corrected for temperature fluctuations. It uses the factor $TCF = \\exp\\left[2640 \\cdot \\left(\\frac{1}{298.15} - \\frac{1}{T_{water} + 273.15}\\right)\\right]$. Recommended values: > 98%.\n    - **SEC consumption:** Specific energy consumption (kWh/m³), indicating the energy required to produce one cubic metre of fresh water.\n    - **ΔP (pressure drop):** The hydraulic pressure loss between vessel inlet and outlet. A continuous increase indicates physical obstruction such as fouling, biofouling or inorganic scaling.", "💡 **Guida alla Lettura - Ultrafiltrazione (UF):**\n    - **TMP (Pressione Trans-Membrana):** È la pressione netta necessaria per forzare l'acqua ad attraversare i pori microscopici (fibre cave) della membrana di pre-trattamento. \n    - **Salute dell'Asset:** Un rapido e continuo aumento della TMP (verso la soglia di guardia di 1.5 bar) indica un intasamento dei pori (fouling irreversibile) o la necessità di rendere i cicli di controlavaggio (Backwash / CEB) più frequenti o aggressivi.": '💡 **Reading Guide — Ultrafiltration (UF):**\n    - **TMP (Transmembrane Pressure):** The net pressure required to force water through the microscopic pores (hollow fibres) of the pretreatment membrane.\n    - **Asset health:** A rapid and continuous rise in TMP towards the 1.5 bar warning threshold indicates pore blockage (irreversible fouling) or the need for more frequent or more intensive backwash/CEB cycles.', "💡 **Guida alla Lettura - Elettromeccanica Inverter:**\n    - **Cosφ (Fattore di Potenza):** Indica l'efficienza magnetica dello statore del motore elettrico. Un calo progressivo o brusco del Cosφ rispetto alla linea di base indica degrado dell'isolamento o possibili cortocircuiti tra le spire avvolte (situazione critica).\n    - **Sforzo Meccanico (A/Hz):** L'indice calcolato dal rapporto tra Corrente assorbita e Frequenza di rete. Un aumento di questo valore indica che la pompa sta chiedendo più Ampere a parità di giri di rotazione: è un forte campanello d'allarme per usura dei cuscinetti, attriti anomali o blocco della girante idraulica.": '💡 **Reading Guide — Inverter Electromechanics:**\n    - **Cosφ (power factor):** Indicates the magnetic efficiency of the electric motor stator. A gradual or sudden decrease from the baseline may indicate insulation degradation or possible turn-to-turn short circuits.\n    - **Mechanical load (A/Hz):** The ratio between current draw and operating frequency. An increase means the pump requires more current at the same speed, which may indicate bearing wear, abnormal friction or impeller blockage.', "💡 **Guida alla Lettura - Troubleshooting ed Esplorazione Libera:**\n    Questa sezione non impone regole predefinite o calcoli automatici. Puoi sovrapporre liberamente qualsiasi parametro (idraulico, chimico o elettrico) memorizzato nel database per identificare correlazioni anomale non ovvie (ad esempio: misurare in quale misura un picco di pressione dell'alimento influenza il consumo elettrico SEC). È lo strumento ideale per la *Root Cause Analysis* in caso di anomalie di sistema.": '💡 **Reading Guide — Troubleshooting and Free Exploration:**\n    This section applies no predefined rules or automatic calculations. You can freely overlay any hydraulic, chemical or electrical parameter stored in the database to identify non-obvious abnormal correlations, such as how a feed-pressure spike affects SEC. It is designed for *Root Cause Analysis* when system anomalies occur.', '💡 **Guida alla Lettura - Modello Predittivo:**\n    - **Health Score (%):** Un indicatore compreso tra 0 e 100 che rappresenta la "vita utile residua" dell\'asset prima di dover effettuare una manutenzione correttiva.\n    - **Come calcoliamo le date:** Il sistema utilizza un algoritmo di **Regressione Lineare** (usando l\'equazione $y = mx + q$) che elabora la tendenza dei dati storici. Quando la retta di regressione tracciata dal modello interseca i limiti ingegneristici predefiniti (ad esempio: una perdita del 15% sulla permeabilità iniziale), il sistema stima in modo proattivo i giorni rimanenti al lavaggio (CIP) o alla sostituzione.': "💡 **Reading Guide — Predictive Model:**\n    - **Health Score (%):** An indicator from 0 to 100 representing the asset's estimated remaining useful condition before corrective maintenance is required.\n    - **How dates are calculated:** The system uses a **linear regression** algorithm ($y = mx + q$) to evaluate the historical trend. When the regression line intersects a predefined engineering limit, such as a 15% loss of initial permeability, it estimates the remaining time before CIP or replacement.", '💡 **Guida alla Lettura - Analisi Comparativa (A/B Test e Box Plot):**\n    - **La "Scatola" (Box):** Rappresenta visivamente il 50% centrale delle letture di quel periodo (il range di funzionamento "normale"). Se la scatola si "allarga" molto, l\'impianto sta soffrendo di instabilità idraulica.\n    - **La Mediana (linea centrale):** È il valore medio effettivo di funzionamento. Se la mediana del Periodo B è palesemente disallineata da quella del Periodo A, significa che l\'impianto ha subito una deviazione strutturale (es. dopo aver cambiato le cartucce o eseguito un CIP).\n    - **I Puntini (Outliers):** Identificano singoli campioni anomali, fuori scala rispetto al normale ciclo produttivo (ad esempio: colpi d\'ariete, partenze repentine dell\'inverter). Più puntini vedi, più l\'infrastruttura ha subito shock termici o idraulici.': '💡 **Reading Guide — Comparative Analysis (A/B Test and Box Plot):**\n    - **The box:** Represents the central 50% of the readings in the period, corresponding to the normal operating range. A much wider box indicates greater hydraulic instability.\n    - **The median:** The central operating value. A clear shift in Period B compared with Period A indicates a structural change, such as after cartridge replacement or CIP.\n    - **Outliers:** Individual samples outside the normal operating distribution, such as water hammer or abrupt inverter starts. More outliers indicate more frequent hydraulic or thermal shocks.'}


_EXACT_TRANSLATIONS.update({
    "fino a ieri": "up to yesterday",
    "Non sono ancora disponibili giorni completi nel mese corrente.": "No complete days are available yet in the current month.",
    "📄 Report": "📄 Reports",
    "📄 Generazione Report": "📄 Report Generation",
    "Periodo del report:": "Report period:",
    "Serie del grafico produzione:": "Production chart series:",
    "Sezioni da includere:": "Sections to include:",
    "Produzione e vendite": "Production and sales",
    "Performance RO": "RO performance",
    "UF e filtri": "UF and filters",
    "Motori e pompe": "Motors and pumps",
    "Tabella giornaliera": "Daily table",
    "Genera report PDF": "Generate PDF report",
    "Generazione del report in corso...": "Generating report...",
    "Report generato correttamente.": "Report generated successfully.",
    "Scarica report PDF": "Download PDF report",
    "Nessun dato disponibile per generare il report.": "No data are available to generate the report.",
    "Seleziona una data iniziale e una data finale valide.": "Select a valid start date and end date.",
    "Il report usa la lingua attualmente selezionata nella dashboard.": "The report uses the language currently selected in the dashboard.",
    "Il concentrato non è incluso di default nel grafico del report.": "Concentrate is not included in the report chart by default.",
    "Includi note automatiche e indicatori di qualità del dato": "Include automatic notes and data-quality indicators",
    "💧 Qualità Acqua (Manuale)": "💧 Water Quality (Manual)",
    "Registro Qualità Acqua (Inserimenti Manuali)": "Water Quality Log (Manual Entries)",
    "Nessun dato di qualità dell'acqua trovato per questo impianto.": "No water quality data found for this plant.",
    "Data Rilievo": "Date",
    "Operatore": "Operator",
    "Strumento": "Instrument",
    "Seleziona un report per visualizzare i valori e la firma:": "Select a report to view values and signature:",
    "Dettaglio Misurazione e Firma": "Measurement Details and Signature",
    "Nessuna firma disponibile.": "No signature available.",
    "Nessun valore registrato in questa tabella.": "No values recorded in this table.",
    "📈 Trend Temporale Qualità Acqua": "📈 Water Quality Time Trend",
    "Seleziona il parametro da analizzare:": "Select parameter to analyse:",
    "Seleziona i punti di campionamento:": "Select sampling points:",
    "Cloro (mg/l)": "Chlorine (mg/l)",
    "Conduttività (us)": "Conductivity (us)",
    "Temperatura (°C)": "Temperature (°C)",
    "Nessun dato disponibile per questa combinazione.": "No data available for this combination.",
    "Non ci sono abbastanza dati storici per generare un grafico.": "Not enough historical data to generate a chart.",
    "Qualità Acqua": "Water Quality",
    "Andamento Qualità Acqua (Manuale)": "Water Quality Trends (Manual)",
    "📉 Health Index RO": "📉 RO Health Index",
    "Health Index RO persistente": "Persistent RO Health Index",
    "Indice di salute persistente delle membrane e del circuito RO": "Persistent health index of RO membranes and hydraulic circuit",
    "Variazione 7 giorni": "7-day change",
    "Stato Health Index": "Health Index status",
    "Qualità dati Health Index": "Health Index data quality",
    "Componente permeabilità": "Permeability component",
    "Componente ΔP": "ΔP component",
    "Componente passaggio salino": "Salt-passage component",
    "Health Index storico RO": "Historical RO Health Index",
    "Health Index persistente": "Persistent Health Index",
    "Health Index grezzo": "Raw Health Index",
    "Soglia monitoraggio": "Monitoring threshold",
    "Soglia attenzione": "Warning threshold",
    "Soglia critica": "Critical threshold",
    "Impostazione baseline Health Index": "Health Index baseline setting",
    "Data baseline (ultima condizione pulita / CIP / sostituzione):": "Baseline date (last clean condition / CIP / replacement):",
    "Buono": "Good",
    "Da monitorare": "Monitor",
    "Attenzione": "Warning",
    "Critico": "Critical"
})

_PHRASE_TRANSLATIONS = {'Sistema di Monitoraggio - ': 'Monitoring System — ', 'Origine Dati: ': 'Data source: ', 'Nessun dato registrato per ': 'No data recorded for ', '. In attesa dei log...': '. Waiting for logs...', 'Nessun dato PDF trovato per ': 'No PDF data found for ', 'Errore caricamento dati PDF: ': 'Error loading PDF data: ', 'Nessun misuratore di portata FIT disponibile nei dati.': 'No FIT flow meter is available in the data.', '#### Portate istantanee — tutti i FIT': '#### Instantaneous flow rates — all FIT meters', 'Fouling: Indice di Permeabilità ASTM (Media Mobile)': 'Fouling: ASTM Permeability Index (Moving Average)', 'Dinamica Pressioni Idrauliche': 'Hydraulic Pressure Dynamics', 'Dati Cosφ non disponibili o insufficienti per ': 'Cosφ data are unavailable or insufficient for ', "Nessun dato numerico valido nell'intervallo selezionato.": 'No valid numerical data in the selected range.', 'Stimato in: ': 'Estimated in: ', ' giorni': ' days', 'Dati insufficienti per la previsione delle membrane RO.': 'Insufficient data for the RO membrane forecast.', 'Lavaggio chimico (CIP) tra **': 'Chemical cleaning (CIP) in **', 'Dati insufficienti per la previsione degli spaziatori RO.': 'Insufficient data for the RO spacer forecast.', 'Lavaggio (CIP) stimato tra **': 'Cleaning (CIP) estimated in **', 'In attesa di dati UF sufficienti...': 'Waiting for sufficient UF data...', 'Dati insufficienti per la previsione dei filtri a calza.': 'Insufficient data for the bag-filter forecast.', 'Dati insufficienti per la previsione delle cartucce CF01.': 'Insufficient data for the CF01 cartridge forecast.', 'In attesa di dati inverter sufficienti...': 'Waiting for sufficient inverter data...', 'Non ci sono abbastanza campioni validi per costruire il cruscotto motori.': 'There are not enough valid samples to build the motor dashboard.', 'Previsione Fouling Membrane RO': 'RO Membrane Fouling Forecast', 'Previsione Fouling Spaziatori RO': 'RO Spacer Fouling Forecast', 'Previsione TMP Ultrafiltrazione': 'Ultrafiltration TMP Forecast', 'Previsione Intasamento Filtri a Calza': 'Bag-filter Clogging Forecast', 'Previsione Intasamento Cartucce CF01': 'CF01 Cartridge Clogging Forecast', 'Sforzo Meccanico Relativo (A/Hz) - ': 'Relative Mechanical Load (A/Hz) — ', 'Salute Magnetica Statore (Cosφ) - ': 'Stator Magnetic Health (Cosφ) — ', 'Trend Cosφ - ': 'Cosφ Trend — ', 'Distribuzione e Stabilità: ': 'Distribution and Stability: ', 'Periodo A<br>(': 'Period A<br>(', 'Periodo B<br>(': 'Period B<br>(', 'Riepilogo mensile — ': 'Monthly summary — ', 'Le medie mensili sono calcolate su ': 'Monthly averages are calculated over ', ' trascorsi del mese': ' elapsed days of the month', ' di calendario': ' calendar days', 'La data iniziale deve precedere la data finale.': 'The start date must be earlier than the end date.', 'Periodo dal ': 'Period from ', ' al ': ' to ', ' giorni di calendario.': ' calendar days.', 'Seleziona una data iniziale e una data finale.': 'Select a start date and an end date.', 'Seleziona almeno una serie da visualizzare nel grafico.': 'Select at least one data series to display in the chart.', 'Volumi giornalieri — ': 'Daily volumes — ', 'Nessun dato di produzione PDF nel mese selezionato.': 'No PDF production data for the selected month.', 'Nessun dato ATM nel mese selezionato.': 'No ATM data for the selected month.', 'Errore nel caricamento dei dati Produzione/ATM: ': 'Error loading Production/ATM data: ', 'Nessun dato di produzione o ATM trovato per ': 'No production or ATM data found for ', 'Puoi mostrare Produzione, Vendite ATM e Concentrato singolarmente oppure in qualsiasi combinazione. Il concentrato non è selezionato di default.': 'You can display Production, ATM sales and Concentrate individually or in any combination. Concentrate is not selected by default.', 'Produzione: ': 'Production: ', 'Venduto: ': 'Sold: ', 'Concentrato: ': 'Concentrate: ', 'Trend Produzione - ': 'Production Trend — ', 'Distribuzione Erogazioni - ': 'Dispensing Distribution — ', 'Nessun dato ATM trovato per questo impianto.': 'No ATM data found for this plant.', 'Errore caricamento dati ATM: ': 'Error loading ATM data: ', ' (Sostit. ': ' (Replaced ', 'Media 24h': '24 h average', 'Permeabilità': 'Permeability', 'Reiezione': 'Rejection'}


def tr_text(value):
    """Traduzione lato interfaccia; i valori interni restano invariati."""
    if UI_LANGUAGE != "en" or not isinstance(value, str):
        return value

    if value in _EXACT_TRANSLATIONS:
        return _EXACT_TRANSLATIONS[value]

    translated = value
    for italian, english in sorted(
        _PHRASE_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        translated = translated.replace(italian, english)

    # Applica anche le traduzioni esatte come sostituzioni di frasi lunghe,
    # senza usare chiavi molto brevi che potrebbero alterare parole tecniche.
    for italian, english in sorted(
        _EXACT_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if len(italian) >= 5:
            translated = translated.replace(italian, english)

    return translated


def _translate_dataframe(data):
    if UI_LANGUAGE != "en":
        return data

    if isinstance(data, pd.DataFrame):
        translated = data.copy()
        translated.columns = [tr_text(str(col)) for col in translated.columns]
        for col in translated.columns:
            if translated[col].dtype == "object" or str(translated[col].dtype).startswith("string"):
                translated[col] = translated[col].map(
                    lambda item: tr_text(item) if isinstance(item, str) else item
                )
        return translated

    if isinstance(data, pd.Series):
        translated = data.copy()
        translated.name = tr_text(str(translated.name)) if translated.name is not None else None
        if translated.dtype == "object" or str(translated.dtype).startswith("string"):
            translated = translated.map(
                lambda item: tr_text(item) if isinstance(item, str) else item
            )
        return translated

    return data


def _translate_plotly_figure(figure):
    if UI_LANGUAGE != "en":
        return figure

    try:
        translated = go.Figure(figure)
    except Exception:
        return figure

    for trace in translated.data:
        if getattr(trace, "name", None):
            trace.name = tr_text(trace.name)
        if getattr(trace, "hovertemplate", None):
            trace.hovertemplate = tr_text(trace.hovertemplate)
        trace_text = getattr(trace, "text", None)
        if isinstance(trace_text, str):
            trace.text = tr_text(trace_text)

    if translated.layout.title and translated.layout.title.text:
        translated.layout.title.text = tr_text(translated.layout.title.text)

    for axis_name in ("xaxis", "yaxis", "yaxis2", "yaxis3"):
        axis = getattr(translated.layout, axis_name, None)
        if axis and axis.title and axis.title.text:
            axis.title.text = tr_text(axis.title.text)

    if translated.layout.legend and translated.layout.legend.title and translated.layout.legend.title.text:
        translated.layout.legend.title.text = tr_text(translated.layout.legend.title.text)

    if translated.layout.annotations:
        for annotation in translated.layout.annotations:
            if annotation.text:
                annotation.text = tr_text(annotation.text)

    return translated


def _is_streamlit_container(value):
    module_name = getattr(value.__class__, "__module__", "")
    return module_name.startswith("streamlit") and (
        hasattr(value, "markdown") or hasattr(value, "metric")
    )


def _wrap_streamlit_result(value):
    if isinstance(value, list):
        return [_wrap_streamlit_result(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_wrap_streamlit_result(item) for item in value)
    if _is_streamlit_container(value):
        return _TranslatedStreamlit(value)
    return value


class _TranslatedStreamlit:
    """Proxy che traduce solo la presentazione, senza cambiare la logica interna."""

    def __init__(self, target):
        self._target = target

    def __enter__(self):
        self._target.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._target.__exit__(exc_type, exc_value, traceback)

    def __getattr__(self, name):
        attribute = getattr(self._target, name)

        if not callable(attribute):
            return _TranslatedStreamlit(attribute) if _is_streamlit_container(attribute) else attribute

        def translated_call(*args, **kwargs):
            args = list(args)

            if UI_LANGUAGE == "en":
                text_methods = {
                    "title", "header", "subheader", "markdown", "caption",
                    "info", "warning", "error", "success", "write", "text"
                }
                choice_methods = {"selectbox", "radio", "multiselect"}
                label_methods = {
                    "date_input", "toggle", "checkbox", "button", "download_button",
                    "text_input", "number_input", "slider"
                }

                if name in text_methods:
                    if args:
                        args[0] = tr_text(args[0])
                    for key in ("body", "text"):
                        if key in kwargs:
                            kwargs[key] = tr_text(kwargs[key])

                elif name == "metric":
                    for index in range(min(3, len(args))):
                        args[index] = tr_text(args[index])
                    for key in ("label", "value", "delta", "help"):
                        if key in kwargs:
                            kwargs[key] = tr_text(kwargs[key])

                elif name in choice_methods:
                    if args:
                        args[0] = tr_text(args[0])
                    if "label" in kwargs:
                        kwargs["label"] = tr_text(kwargs["label"])
                    if "help" in kwargs:
                        kwargs["help"] = tr_text(kwargs["help"])

                    original_format = kwargs.get("format_func")
                    if original_format is None:
                        kwargs["format_func"] = lambda option: tr_text(str(option))
                    else:
                        kwargs["format_func"] = (
                            lambda option, formatter=original_format: tr_text(formatter(option))
                        )

                elif name == "tabs":
                    if args and isinstance(args[0], (list, tuple)):
                        args[0] = [tr_text(label) for label in args[0]]
                    elif "tabs" in kwargs:
                        kwargs["tabs"] = [tr_text(label) for label in kwargs["tabs"]]

                elif name in label_methods:
                    if args:
                        args[0] = tr_text(args[0])
                    for key in ("label", "help", "placeholder"):
                        if key in kwargs:
                            kwargs[key] = tr_text(kwargs[key])

                elif name == "plotly_chart":
                    if args:
                        args[0] = _translate_plotly_figure(args[0])
                    elif "figure_or_data" in kwargs:
                        kwargs["figure_or_data"] = _translate_plotly_figure(
                            kwargs["figure_or_data"]
                        )

                elif name == "dataframe":
                    if args:
                        args[0] = _translate_dataframe(args[0])
                    elif "data" in kwargs:
                        kwargs["data"] = _translate_dataframe(kwargs["data"])

                elif name == "progress" and "text" in kwargs:
                    kwargs["text"] = tr_text(kwargs["text"])

            result = attribute(*args, **kwargs)
            return _wrap_streamlit_result(result)

        return translated_call


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
        # Nella panoramica flotta interessa la produzione RO, non la portata
        # potabile a valle della distribuzione.
        "overview_flow_column": "fit001",
        "overview_flow_label": "Flusso Permeato",
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
def load_water_quality_data(impianto_scelto):
    try:
        from supabase import create_client
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        nome_impianto = "kaktus" if "Kaktus" in impianto_scelto else "pingwe"
        res = supabase.table(f"misurazioni_{nome_impianto}").select("*").execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        
        storico_dati = []
        for _, row in df.iterrows():
            data_val = row.get('data_rilievo')
            dati_json = row.get('dati_tabella')
            if pd.notna(data_val) and dati_json:
                for punto, valori in dati_json.items():
                    for param, val in valori.items():
                        storico_dati.append({
                            '_report_date': pd.to_datetime(data_val),
                            'Punto': str(punto),
                            'Parametro': str(param),
                            'Valore': float(val)
                        })
        return pd.DataFrame(storico_dati)
    except Exception:
        return pd.DataFrame()

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

    # Il salto di pressione varia anche con la portata. Per la diagnosi CIP lo
    # riportiamo alla portata di alimento iniziale usando l'esponente idraulico
    # 1,5 comunemente adottato per i feed spacer spiral-wound. Se la portata non
    # è disponibile, il dato grezzo resta il fallback esplicito.
    if {'fit001', 'fit002'}.issubset(out.columns):
        q_feed = pd.to_numeric(out['fit001'], errors='coerce') + pd.to_numeric(out['fit002'], errors='coerce')
    elif {'fit001', 'recovery'}.issubset(out.columns):
        recovery_fraction = pd.to_numeric(out['recovery'], errors='coerce') / 100.0
        q_feed = pd.to_numeric(out['fit001'], errors='coerce') / recovery_fraction.where(recovery_fraction > 0.01)
    else:
        q_feed = pd.Series(np.nan, index=out.index, dtype=float)

    q_feed = pd.to_numeric(q_feed, errors='coerce').where(lambda s: s > 0.01)
    q_ref_values = q_feed.dropna().iloc[:24]
    q_ref = float(q_ref_values.median()) if not q_ref_values.empty else np.nan
    if np.isfinite(q_ref) and q_ref > 0:
        correction = np.power(q_ref / q_feed, 1.5).clip(lower=0.25, upper=4.0)
        out['dp_ro_norm'] = pd.to_numeric(out['dp_ro'], errors='coerce') * correction
        out['dp_ro_norm_method'] = 'flow_corrected'
    else:
        out['dp_ro_norm'] = pd.to_numeric(out['dp_ro'], errors='coerce')
        out['dp_ro_norm_method'] = 'raw_fallback'
    out['dp_ro_norm_smooth'] = out['dp_ro_norm'].rolling(window=24, min_periods=1).mean()
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


def calcola_health_index_ro(df_ro, baseline_date=None):
    """
    Health Index storico RO (0-100), distinto dalla diagnosi istantanea.

    Principi:
    - usa mediane giornaliere per ridurre transitori e picchi;
    - baseline robusta sui primi 7 giorni validi dopo la data baseline;
    - combina permeabilità normalizzata (45%), ΔP RO normalizzato (35%)
      e passaggio salino (20%);
    - applica memoria asimmetrica: recepisce il degrado più rapidamente
      del recupero, evitando salti eccessivi dopo una sola giornata buona.

    Le soglie di riferimento sono:
    - permeabilità: -15%;
    - ΔP normalizzato: +15%;
    - passaggio salino: +10% rispetto alla baseline.
    Alla soglia la singola componente vale circa 50/100.
    """
    if df_ro is None or df_ro.empty:
        return pd.DataFrame()

    dp_col = (
        "dp_ro_norm_smooth"
        if "dp_ro_norm_smooth" in df_ro.columns
        else "dp_ro_smooth"
    )
    required = ["perm_norm_smooth", dp_col, "sr_norm"]
    if not all(col in df_ro.columns for col in required):
        return pd.DataFrame()

    work = df_ro.copy()

    if "date_str" in work.columns:
        work["_health_date"] = pd.to_datetime(work["date_str"], errors="coerce")
    elif "timestamp" in work.columns:
        work["_health_date"] = pd.to_datetime(
            pd.to_numeric(work["timestamp"], errors="coerce"),
            unit="s",
            errors="coerce"
        )
    else:
        return pd.DataFrame()

    for col in required:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.dropna(subset=["_health_date"]).copy()
    if baseline_date is not None:
        baseline_ts = pd.Timestamp(baseline_date).normalize()
        work = work[work["_health_date"] >= baseline_ts].copy()

    if work.empty:
        return pd.DataFrame()

    work["date"] = work["_health_date"].dt.normalize()
    daily = (
        work.groupby("date", as_index=False)[required]
        .median()
        .sort_values("date")
        .reset_index(drop=True)
    )

    valid = daily.dropna(subset=required).copy()
    if len(valid) < 3:
        return pd.DataFrame()

    baseline_window = valid.head(min(7, len(valid)))
    base_perm = float(baseline_window["perm_norm_smooth"].median())
    base_dp = float(baseline_window[dp_col].median())
    base_sp = float((100.0 - baseline_window["sr_norm"]).median())

    if not np.isfinite(base_perm) or base_perm <= 0:
        return pd.DataFrame()

    # Deterioramenti relativi rispetto alla condizione di baseline.
    daily["perdita_perm_pct"] = np.maximum(
        0.0,
        (base_perm - daily["perm_norm_smooth"]) / base_perm * 100.0
    )

    dp_den = max(abs(base_dp), 0.10)
    daily["aumento_dp_pct"] = np.maximum(
        0.0,
        (daily[dp_col] - base_dp) / dp_den * 100.0
    )

    daily["salt_passage"] = 100.0 - daily["sr_norm"]
    sp_den = max(abs(base_sp), 0.05)
    daily["aumento_sp_pct"] = np.maximum(
        0.0,
        (daily["salt_passage"] - base_sp) / sp_den * 100.0
    )

    def score_component(degrado_pct, soglia_pct):
        # 100 alla baseline, 50 alla soglia, 0 a 2x la soglia.
        score = 100.0 - 50.0 * (degrado_pct / soglia_pct)
        return np.clip(score, 0.0, 100.0)

    daily["health_perm"] = score_component(daily["perdita_perm_pct"], 15.0)
    daily["health_dp"] = score_component(daily["aumento_dp_pct"], 15.0)
    daily["health_sp"] = score_component(daily["aumento_sp_pct"], 10.0)

    daily["health_raw"] = (
        0.45 * daily["health_perm"]
        + 0.35 * daily["health_dp"]
        + 0.20 * daily["health_sp"]
    )

    # Filtro con memoria asimmetrica.
    raw = pd.to_numeric(daily["health_raw"], errors="coerce").to_numpy(dtype=float)
    persistent = []
    previous = np.nan

    for value in raw:
        if not np.isfinite(value):
            persistent.append(previous)
            continue

        if not np.isfinite(previous):
            previous = value
        else:
            # Se peggiora, il modello reagisce più rapidamente.
            # Se migliora, recupera lentamente per evitare 47 -> 93 in un giorno.
            alpha = 0.45 if value < previous else 0.08
            previous = previous + alpha * (value - previous)

        previous = float(np.clip(previous, 0.0, 100.0))
        persistent.append(previous)

    daily["health_index"] = persistent

    # Completezza dei tre segnali usati per l'indice.
    valid_count = daily[required].notna().sum(axis=1)
    daily["data_quality"] = valid_count / len(required) * 100.0

    daily["baseline_perm"] = base_perm
    daily["baseline_dp"] = base_dp
    daily["baseline_sp"] = base_sp
    daily["dp_health_column"] = dp_col

    return daily


def stato_health_index(score):
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "N/D"

    if not np.isfinite(score):
        return "N/D"
    if score >= 85:
        return "Buono"
    if score >= 70:
        return "Da monitorare"
    if score >= 50:
        return "Attenzione"
    return "Critico"


def _finite_float(value, default=np.nan):
    try:
        converted = float(value)
        return converted if np.isfinite(converted) else default
    except (TypeError, ValueError):
        return default


def _clip01(value):
    value = _finite_float(value, 0.0)
    return float(np.clip(value, 0.0, 1.0))


def _relative_slope_per_day(df, column, reference, lookback_days=14):
    """Pendenza recente espressa come % del riferimento per giorno."""
    if df is None or df.empty or column not in df.columns or not np.isfinite(reference) or abs(reference) < 1e-12:
        return 0.0

    dates = pd.to_datetime(df.get('date_str'), errors='coerce')
    values = pd.to_numeric(df[column], errors='coerce')
    valid = dates.notna() & values.notna() & np.isfinite(values)
    if valid.sum() < 3:
        return 0.0

    recent = pd.DataFrame({'date': dates[valid], 'value': values[valid]}).sort_values('date')
    cutoff = recent['date'].max() - pd.Timedelta(days=lookback_days)
    recent = recent[recent['date'] >= cutoff]
    if len(recent) < 3 or recent['date'].nunique() < 2:
        return 0.0

    x_days = (recent['date'] - recent['date'].iloc[0]).dt.total_seconds().to_numpy(dtype=float) / 86400.0
    try:
        slope = np.polyfit(x_days, recent['value'].to_numpy(dtype=float), 1)[0]
    except (TypeError, ValueError, np.linalg.LinAlgError):
        return 0.0
    return float(slope / abs(reference) * 100.0) if np.isfinite(slope) else 0.0


def _recent_threshold_persistence(df, values, threshold, lookback_hours=24, min_fraction=0.75):
    """Verifica che un segnale superi la soglia in modo persistente, non su un solo campione."""
    dates = pd.to_datetime(df.get('date_str'), errors='coerce')
    numeric_values = pd.to_numeric(values, errors='coerce')
    valid = dates.notna() & numeric_values.notna() & np.isfinite(numeric_values)
    if valid.sum() < 6:
        return False, np.nan, 0.0

    recent = pd.DataFrame({'date': dates[valid], 'value': numeric_values[valid]}).sort_values('date')
    cutoff = recent['date'].max() - pd.Timedelta(hours=lookback_hours)
    recent = recent[recent['date'] >= cutoff]
    if len(recent) < 6:
        return False, np.nan, 0.0

    span_hours = (recent['date'].max() - recent['date'].min()).total_seconds() / 3600.0
    median_value = float(recent['value'].median())
    fraction_above = float((recent['value'] >= threshold).mean())
    persistent = span_hours >= lookback_hours * 0.75 and fraction_above >= min_fraction
    return persistent, median_value, fraction_above


def diagnostica_cip_ro(df_ro, baseline_ro, latest_ro, osservazioni=None):
    """Diagnosi euristica: i punteggi sono compatibilità relative, non probabilità statistiche."""
    osservazioni = set(osservazioni or [])
    dp_col = 'dp_ro_norm_smooth' if 'dp_ro_norm_smooth' in df_ro.columns else 'dp_ro_smooth'

    base_perm = _finite_float(baseline_ro.get('perm_norm_smooth'))
    curr_perm = _finite_float(latest_ro.get('perm_norm_smooth'))
    base_dp = _finite_float(baseline_ro.get(dp_col))
    curr_dp = _finite_float(latest_ro.get(dp_col))
    base_sr = _finite_float(baseline_ro.get('sr_norm'))
    curr_sr = _finite_float(latest_ro.get('sr_norm'))

    perm_loss_pct = max(0.0, (base_perm - curr_perm) / base_perm * 100.0) if np.isfinite(base_perm) and base_perm > 0 and np.isfinite(curr_perm) else 0.0
    perm_gain_pct = max(0.0, (curr_perm - base_perm) / base_perm * 100.0) if np.isfinite(base_perm) and base_perm > 0 and np.isfinite(curr_perm) else 0.0
    dp_rise_pct = max(0.0, (curr_dp - base_dp) / base_dp * 100.0) if np.isfinite(base_dp) and base_dp > 0 and np.isfinite(curr_dp) else 0.0
    dp_drop_pct = max(0.0, (base_dp - curr_dp) / base_dp * 100.0) if np.isfinite(base_dp) and base_dp > 0 and np.isfinite(curr_dp) else 0.0
    sr_drop_pp = max(0.0, base_sr - curr_sr) if np.isfinite(base_sr) and np.isfinite(curr_sr) else 0.0

    base_salt_passage = max(100.0 - base_sr, 0.05) if np.isfinite(base_sr) else np.nan
    curr_salt_passage = max(100.0 - curr_sr, 0.0) if np.isfinite(curr_sr) else np.nan
    salt_passage_change_pct = (
        (curr_salt_passage - base_salt_passage) / base_salt_passage * 100.0
        if np.isfinite(base_salt_passage) and np.isfinite(curr_salt_passage)
        else 0.0
    )
    sr_source = df_ro['sr_norm'] if 'sr_norm' in df_ro.columns else pd.Series(np.nan, index=df_ro.index)
    sr_series = pd.to_numeric(sr_source, errors='coerce')
    salt_passage_series = (100.0 - sr_series).clip(lower=0.0)
    salt_passage_change_series = (
        (salt_passage_series - base_salt_passage) / base_salt_passage * 100.0
        if np.isfinite(base_salt_passage) and base_salt_passage > 0
        else pd.Series(np.nan, index=df_ro.index, dtype=float)
    )
    salt_persistent_5, salt_recent_median_pct, salt_recent_fraction = _recent_threshold_persistence(
        df_ro, salt_passage_change_series, 5.0
    )
    salt_persistent_10, _, _ = _recent_threshold_persistence(
        df_ro, salt_passage_change_series, 10.0
    )

    perm_slope_pct_day = _relative_slope_per_day(df_ro, 'perm_norm_smooth', base_perm)
    dp_slope_pct_day = _relative_slope_per_day(df_ro, dp_col, base_dp)

    perm_signal = _clip01(perm_loss_pct / 15.0)
    dp_signal = _clip01(dp_rise_pct / 15.0)
    salt_signal = _clip01(max(salt_passage_change_pct / 25.0, sr_drop_pp / 0.5))
    perm_gain_signal = _clip01(perm_gain_pct / 10.0)
    dp_drop_signal = _clip01(dp_drop_pct / 15.0)
    rapid_signal = _clip01(max(-perm_slope_pct_day / 1.0, dp_slope_pct_day / 1.5))

    base_recovery = _finite_float(baseline_ro.get('recovery'))
    curr_recovery = _finite_float(latest_ro.get('recovery'))
    recovery_rise_signal = _clip01((curr_recovery - base_recovery) / 5.0) if np.isfinite(base_recovery) and np.isfinite(curr_recovery) else 0.0

    severity = _clip01(max(
        perm_loss_pct / 15.0,
        dp_rise_pct / 15.0,
        max(salt_passage_change_pct, 0.0) / 20.0,
        sr_drop_pp / 0.5,
        perm_gain_pct / 10.0,
    ))

    scores = {
        'stable': 0.05 + 3.0 * (1.0 - severity) ** 2,
        'biofilm': 0.03 + 0.48 * dp_signal + 0.28 * perm_signal + 0.15 * rapid_signal + 0.09 * salt_signal,
        'organic_colloidal': 0.04 + 0.34 * perm_signal + 0.30 * dp_signal + 0.10 * salt_signal + 0.12 * severity * (1.0 - rapid_signal),
        'mineral_scale': 0.03 + 0.34 * perm_signal + 0.18 * dp_signal + 0.32 * salt_signal + 0.10 * recovery_rise_signal,
        'metal_inorganic': 0.02 + 0.30 * dp_signal + 0.16 * perm_signal + 0.28 * salt_signal + 0.16 * rapid_signal,
        'integrity_anomaly': 0.01 + 0.48 * salt_signal + 0.34 * perm_gain_signal + 0.17 * dp_drop_signal,
    }

    observation_boosts = {
        'slimy_deposit': ('biofilm', 1.50),
        'microbiology_positive': ('biofilm', 1.25),
        'high_sdi_turbidity': ('organic_colloidal', 1.35),
        'hard_crystals': ('mineral_scale', 1.50),
        'red_brown_deposit': ('metal_inorganic', 1.50),
        'oxidant_event': ('integrity_anomaly', 1.60),
    }
    for observation in osservazioni:
        if observation in observation_boosts:
            cause, boost = observation_boosts[observation]
            scores[cause] += boost
            scores['stable'] *= 0.35

    total_score = sum(max(score, 0.0) for score in scores.values()) or 1.0
    probabilities = {cause: max(score, 0.0) / total_score * 100.0 for cause, score in scores.items()}
    ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)

    valid_signals = sum([
        np.isfinite(base_perm) and base_perm > 0 and np.isfinite(curr_perm),
        np.isfinite(base_dp) and base_dp > 0 and np.isfinite(curr_dp),
        np.isfinite(base_sr) and np.isfinite(curr_sr),
    ])
    valid_dates = pd.to_datetime(df_ro.get('date_str'), errors='coerce').dropna()
    data_span_days = (valid_dates.max() - valid_dates.min()).total_seconds() / 86400.0 if len(valid_dates) >= 2 else 0.0
    data_quality = 0.45 * _clip01(len(df_ro) / 168.0) + 0.30 * _clip01(data_span_days / 7.0) + 0.25 * (valid_signals / 3.0)
    data_quality_pct = float(np.clip(data_quality * 100.0, 0.0, 100.0))
    separation = _clip01((ranked[0][1] - ranked[1][1]) / 40.0) if len(ranked) > 1 else 0.0
    confidence_pct = 25.0 + 28.0 * data_quality + 18.0 * separation + min(12.0, 4.0 * len(osservazioni))
    if ranked[0][0] != 'stable' and not osservazioni:
        confidence_pct = min(confidence_pct, 62.0)
    confidence_pct = float(np.clip(confidence_pct, 20.0, 78.0))

    # Una piccola variazione della reiezione può produrre una variazione relativa
    # elevata del passaggio salino. Da sola genera quindi solo monitoraggio. Per
    # il preallarme richiediamo persistenza e un secondo riscontro di processo.
    salt_monitoring = salt_passage_change_pct >= 5.0 or salt_recent_median_pct >= 5.0
    process_corroboration = perm_loss_pct >= 5.0 or dp_rise_pct >= 5.0
    salt_warning_qualified = salt_persistent_5 and (process_corroboration or sr_drop_pp >= 0.5)
    cip_due = perm_loss_pct >= 15.0 or dp_rise_pct >= 15.0 or salt_persistent_10
    cip_early_warning = perm_loss_pct >= 10.0 or dp_rise_pct >= 10.0 or salt_warning_qualified
    alkaline_probability = probabilities['biofilm'] + probabilities['organic_colloidal']
    acid_probability = probabilities['mineral_scale'] + probabilities['metal_inorganic']
    integrity_probability = probabilities['integrity_anomaly']

    insufficient_data = valid_signals < 2 or len(df_ro) < 24
    if insufficient_data:
        cleaning_code = 'insufficient_data'
    elif integrity_probability >= 35.0 and ranked[0][0] == 'integrity_anomaly':
        cleaning_code = 'integrity_check'
    elif not cip_early_warning:
        cleaning_code = 'none'
    elif not cip_due:
        cleaning_code = 'verify_then_plan'
    elif alkaline_probability >= 55.0 and acid_probability < 35.0:
        cleaning_code = 'alkaline'
    elif acid_probability >= 55.0 and alkaline_probability < 35.0:
        cleaning_code = 'acid'
    else:
        cleaning_code = 'sequential_alkaline_acid'

    if cleaning_code == 'insufficient_data':
        status_code = 'insufficient'
    elif cleaning_code == 'integrity_check':
        status_code = 'investigate'
    elif cip_due:
        status_code = 'cip_due'
    elif cip_early_warning:
        status_code = 'warning'
    elif salt_monitoring:
        status_code = 'monitor'
    else:
        status_code = 'normal'

    return {
        'dp_column': dp_col,
        'dp_flow_normalized': dp_col == 'dp_ro_norm_smooth' and latest_ro.get('dp_ro_norm_method') == 'flow_corrected',
        'perm_loss_pct': perm_loss_pct,
        'dp_rise_pct': dp_rise_pct,
        'sr_drop_pp': sr_drop_pp,
        'salt_passage_change_pct': salt_passage_change_pct,
        'salt_recent_median_pct': salt_recent_median_pct,
        'salt_recent_fraction': salt_recent_fraction,
        'salt_persistent_5': salt_persistent_5,
        'salt_persistent_10': salt_persistent_10,
        'salt_monitoring': salt_monitoring,
        'salt_warning_qualified': salt_warning_qualified,
        'perm_slope_pct_day': perm_slope_pct_day,
        'dp_slope_pct_day': dp_slope_pct_day,
        'severity': severity,
        'probabilities': probabilities,
        'ranked': ranked,
        'confidence_pct': confidence_pct,
        'data_quality_pct': data_quality_pct,
        'cleaning_code': cleaning_code,
        'status_code': status_code,
        'cip_due': cip_due,
        'cip_early_warning': cip_early_warning,
        'alkaline_probability': alkaline_probability,
        'acid_probability': acid_probability,
        'integrity_probability': integrity_probability,
        'valid_signals': valid_signals,
        'insufficient_data': insufficient_data,
        'observations': sorted(osservazioni),
    }


def render_diagnosi_cip_ro(df_ro, baseline_ro, latest_ro):
    st.subheader(ui_text("🧪 Diagnosi probabile e strategia CIP", "🧪 Probable cause and CIP strategy"))
    st.caption(ui_text(
        "I valori percentuali sono punteggi euristici di compatibilità con i segnali disponibili, non probabilità statistiche né identificazioni di laboratorio.",
        "Percentages are heuristic compatibility scores based on available signals, not statistical probabilities or laboratory identifications."
    ))

    observation_labels = {
        'slimy_deposit': ui_text("Deposito viscido / gelatinoso", "Slimy / gelatinous deposit"),
        'microbiology_positive': ui_text("Conta microbiologica o ATP elevati", "High microbiological count or ATP"),
        'high_sdi_turbidity': ui_text("SDI o torbidità alimento elevati", "High feed SDI or turbidity"),
        'hard_crystals': ui_text("Cristalli o deposito minerale duro", "Crystals or hard mineral deposit"),
        'red_brown_deposit': ui_text("Deposito rosso-bruno / Fe-Mn", "Red-brown deposit / Fe-Mn"),
        'oxidant_event': ui_text("Evento cloro/ossidante o perdita improvvisa di reiezione", "Chlorine/oxidant event or sudden rejection loss"),
    }
    observations = st.multiselect(
        ui_text("Osservazioni di campo disponibili (opzionali):", "Available field observations (optional):"),
        options=list(observation_labels.keys()),
        format_func=lambda code: observation_labels[code],
        key="cip_field_observations",
        help=ui_text(
            "Selezionare solo evidenze realmente osservate o misurate: modificano il peso della diagnosi.",
            "Select only observed or measured evidence: these inputs change the diagnostic weighting."
        )
    )
    diagnosis = diagnostica_cip_ro(df_ro, baseline_ro, latest_ro, observations)

    status_messages = {
        'normal': ui_text(
            "Nessun segnale significativo di fouling: continuare il monitoraggio e non eseguire un CIP preventivo non necessario.",
            "No significant fouling signal: continue monitoring and avoid an unnecessary preventive CIP."
        ),
        'monitor': ui_text(
            f"Lieve deriva del passaggio salino ({diagnosis['salt_passage_change_pct']:+.1f}%): monitorare il trend. Il segnale non è persistente o corroborato e non costituisce un preallarme CIP.",
            f"Slight salt-passage drift ({diagnosis['salt_passage_change_pct']:+.1f}%): monitor the trend. The signal is not persistent or corroborated and is not a CIP early warning."
        ),
        'warning': ui_text(
            "Preallarme CIP confermato da un trend persistente e da segnali di processo coerenti: verificare le condizioni operative e raccogliere evidenze di campo prima di scegliere il chimico.",
            "CIP early warning confirmed by a persistent trend and consistent process signals: verify operating conditions and collect field evidence before selecting the chemical."
        ),
        'cip_due': ui_text(
            "Soglia CIP raggiunta: pianificare il lavaggio senza attendere un fouling più profondo e meno recuperabile.",
            "CIP threshold reached: schedule cleaning before fouling becomes deeper and less recoverable."
        ),
        'investigate': ui_text(
            "Il profilo è più compatibile con perdita d'integrità, ossidazione o anomalia idraulica: non avviare un CIP alla cieca.",
            "The profile is more compatible with integrity loss, oxidation or a hydraulic anomaly: do not run a blind CIP."
        ),
        'insufficient': ui_text(
            "Dati insufficienti per una diagnosi CIP: servono almeno 24 campioni e due segnali validi tra permeabilità, ΔP e reiezione.",
            "Insufficient data for a CIP diagnosis: at least 24 samples and two valid signals among permeability, ΔP and rejection are required."
        ),
    }
    if diagnosis['status_code'] == 'normal':
        st.success(status_messages['normal'])
    elif diagnosis['status_code'] == 'monitor':
        st.info(status_messages['monitor'])
    elif diagnosis['status_code'] == 'warning':
        st.warning(status_messages['warning'])
    else:
        st.error(status_messages[diagnosis['status_code']])

    quality_label = (
        ui_text("bassa", "low") if diagnosis['data_quality_pct'] < 50
        else ui_text("media", "medium") if diagnosis['data_quality_pct'] < 75
        else ui_text("alta", "high")
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(ui_text("Perdita permeabilità norm.", "Normalised permeability loss"), f"{diagnosis['perm_loss_pct']:.1f}%")
    c2.metric(ui_text("Aumento ΔP norm.", "Normalised ΔP increase"), f"{diagnosis['dp_rise_pct']:.1f}%")
    salt_delta = (
        ui_text(
            f"Mediana 24 h: {diagnosis['salt_recent_median_pct']:+.1f}%",
            f"24 h median: {diagnosis['salt_recent_median_pct']:+.1f}%"
        )
        if np.isfinite(diagnosis['salt_recent_median_pct']) else None
    )
    c3.metric(
        ui_text("Aumento passaggio salino", "Salt-passage increase"),
        f"{diagnosis['salt_passage_change_pct']:+.1f}%",
        salt_delta,
        delta_color="off",
    )
    c4.metric(ui_text("Qualità dei dati", "Data quality"), f"{diagnosis['data_quality_pct']:.0f}%", quality_label)

    if not diagnosis['dp_flow_normalized']:
        st.warning(ui_text(
            "Il ΔP non ha potuto essere corretto per la portata di alimento: la diagnosi usa il ΔP grezzo e ha qualità interpretativa inferiore.",
            "ΔP could not be corrected for feed flow: the diagnosis uses raw ΔP and has lower interpretive quality."
        ))

    cause_labels = {
        'stable': ui_text("Nessun fouling significativo", "No significant fouling"),
        'biofilm': ui_text("Biofilm / fouling biologico", "Biofilm / biological fouling"),
        'organic_colloidal': ui_text("Organico e colloidale", "Organic and colloidal fouling"),
        'mineral_scale': ui_text("Scaling / precipitato minerale", "Scaling / mineral precipitate"),
        'metal_inorganic': ui_text("Ossidi metallici / inorganico", "Metal oxides / inorganic deposit"),
        'integrity_anomaly': ui_text("Danno membrana / anomalia idraulica", "Membrane damage / hydraulic anomaly"),
    }
    cleaning_by_cause = {
        'stable': ui_text("Nessun CIP", "No CIP"),
        'biofilm': ui_text("CIP basico", "Alkaline CIP"),
        'organic_colloidal': ui_text("CIP basico", "Alkaline CIP"),
        'mineral_scale': ui_text("CIP acido", "Acid CIP"),
        'metal_inorganic': ui_text("CIP acido", "Acid CIP"),
        'integrity_anomaly': ui_text("Verifica integrità; CIP non risolutivo", "Integrity check; CIP may not resolve it"),
    }

    evidence_by_cause = {
        'stable': ui_text(
            "Nessuna combinazione persistente di segnali ha raggiunto le soglie di preallarme.",
            "No persistent combination of signals has reached the early-warning thresholds."
        ),
        'biofilm': ui_text(
            f"ΔP {diagnosis['dp_rise_pct']:+.1f}%, permeabilità -{diagnosis['perm_loss_pct']:.1f}%; un aumento rapido del ΔP rafforza questa ipotesi.",
            f"ΔP {diagnosis['dp_rise_pct']:+.1f}%, permeability -{diagnosis['perm_loss_pct']:.1f}%; a rapid ΔP rise strengthens this hypothesis."
        ),
        'organic_colloidal': ui_text(
            f"Permeabilità -{diagnosis['perm_loss_pct']:.1f}% con ΔP {diagnosis['dp_rise_pct']:+.1f}%: profilo tipico di deposito sulla superficie/spaziatore.",
            f"Permeability -{diagnosis['perm_loss_pct']:.1f}% with ΔP {diagnosis['dp_rise_pct']:+.1f}%: a surface/spacer deposit pattern."
        ),
        'mineral_scale': ui_text(
            f"Permeabilità -{diagnosis['perm_loss_pct']:.1f}% e passaggio salino {diagnosis['salt_passage_change_pct']:+.1f}%: compatibile con precipitazione, da confermare con analisi del concentrato.",
            f"Permeability -{diagnosis['perm_loss_pct']:.1f}% and salt passage {diagnosis['salt_passage_change_pct']:+.1f}%: compatible with precipitation; confirm using concentrate analysis."
        ),
        'metal_inorganic': ui_text(
            f"ΔP {diagnosis['dp_rise_pct']:+.1f}% e passaggio salino {diagnosis['salt_passage_change_pct']:+.1f}%: verificare Fe, Mn e colore del deposito.",
            f"ΔP {diagnosis['dp_rise_pct']:+.1f}% and salt passage {diagnosis['salt_passage_change_pct']:+.1f}%: check Fe, Mn and deposit colour."
        ),
        'integrity_anomaly': ui_text(
            f"Perdita di reiezione {diagnosis['sr_drop_pp']:.2f} punti percentuali senza un coerente aumento del ΔP può indicare danno, O-ring o sensore.",
            f"A rejection loss of {diagnosis['sr_drop_pp']:.2f} percentage points without a coherent ΔP rise may indicate damage, an O-ring issue or a sensor fault."
        ),
    }

    rows = []
    for cause, probability in diagnosis['ranked']:
        rows.append({
            ui_text("Possibile causa", "Possible cause"): cause_labels[cause],
            ui_text("Compatibilità", "Compatibility"): f"{probability:.0f}%",
            ui_text("Evidenza dal trend", "Trend evidence"): evidence_by_cause[cause],
            ui_text("Lavaggio associato", "Associated cleaning"): cleaning_by_cause[cause],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    chart_rows = list(reversed(diagnosis['ranked']))
    fig = go.Figure(go.Bar(
        x=[probability for _, probability in chart_rows],
        y=[cause_labels[cause] for cause, _ in chart_rows],
        orientation='h',
        text=[f"{probability:.0f}%" for _, probability in chart_rows],
        textposition='auto',
        marker_color=['#2E8B57' if cause == 'stable' else '#2F6BFF' for cause, _ in chart_rows],
    ))
    fig.update_layout(
        title=ui_text("Compatibilità delle possibili cause", "Compatibility of possible causes"),
        xaxis_title=ui_text("Punteggio normalizzato (%)", "Normalised score (%)"),
        xaxis_range=[0, max(100, max(diagnosis['probabilities'].values()) * 1.10)],
        margin=dict(l=20, r=20, t=55, b=20),
        height=340,
    )
    st.plotly_chart(fig, use_container_width=True)

    cleaning_titles = {
        'none': ui_text("Nessun CIP consigliato", "No CIP recommended"),
        'verify_then_plan': ui_text("Confermare i dati e preparare il CIP", "Confirm data and prepare the CIP"),
        'alkaline': ui_text("CIP basico consigliato", "Alkaline CIP recommended"),
        'acid': ui_text("CIP acido consigliato", "Acid CIP recommended"),
        'sequential_alkaline_acid': ui_text("CIP sequenziale: basico → risciacquo → acido", "Sequential CIP: alkaline → rinse → acid"),
        'integrity_check': ui_text("Prima verificare integrità e strumentazione", "Check integrity and instrumentation first"),
        'insufficient_data': ui_text("Raccogliere altri dati prima di decidere", "Collect more data before deciding"),
    }
    st.markdown(f"### {cleaning_titles[diagnosis['cleaning_code']]}")

    if diagnosis['cleaning_code'] == 'insufficient_data':
        st.write(ui_text(
            "Non scegliere il chimico dal solo valore istantaneo. Verificare i sensori e acquisire almeno un giorno di funzionamento stabile con portate, pressioni, temperatura, conducibilità alimento/permeato e recovery coerenti.",
            "Do not select a cleaner from a single instantaneous value. Verify instruments and acquire at least one stable operating day with consistent flows, pressures, temperature, feed/permeate conductivity and recovery."
        ))
    elif diagnosis['cleaning_code'] == 'none':
        st.write(ui_text(
            "Mantenere flush con permeato dopo gli arresti, osservare il trend e ricontrollare se uno degli scostamenti supera il preallarme.",
            "Maintain permeate flushing after shutdowns, monitor the trend and reassess if any deviation crosses the early-warning level."
        ))
    elif diagnosis['cleaning_code'] == 'verify_then_plan':
        st.write(ui_text(
            "Ripetere il confronto su almeno 24 ore di funzionamento stabile; controllare taratura pressostati/flussimetri, SDI o torbidità, Fe/Mn e microbiologia/ATP. Se il trend è confermato, applicare il tipo di CIP indicato dalle cause più compatibili.",
            "Repeat the comparison over at least 24 hours of stable operation; check pressure/flow instrument calibration, SDI or turbidity, Fe/Mn and microbiology/ATP. If confirmed, apply the CIP type indicated by the most compatible causes."
        ))
    elif diagnosis['cleaning_code'] == 'integrity_check':
        st.write(ui_text(
            "Verificare prima conducimetri, campionamento, O-ring/interconnettori, eventuale esposizione a ossidanti e test d'integrità. Un lavaggio non ripara una membrana ossidata o una perdita meccanica.",
            "First check conductivity instruments, sampling, O-rings/interconnectors, oxidant exposure and membrane integrity. Cleaning cannot repair oxidation damage or a mechanical leak."
        ))
    else:
        if diagnosis['cleaning_code'] == 'alkaline':
            chemical_step = ui_text(
                "Usare un detergente/chelante alcalino approvato per rimuovere biofilm, organico e colloidi.",
                "Use a membrane-approved alkaline detergent/chelating cleaner for biofilm, organics and colloids."
            )
        elif diagnosis['cleaning_code'] == 'acid':
            chemical_step = ui_text(
                "Usare un detergente acido/chelante approvato (tipicamente a base di acido citrico) per scaling e ossidi metallici.",
                "Use a membrane-approved acid/chelating cleaner (typically citric-acid based) for scale and metal oxides."
            )
        else:
            chemical_step = ui_text(
                "Eseguire prima il lavaggio alcalino per biofilm/organico, risciacquare completamente, quindi eseguire il lavaggio acido per precipitato/ossidi.",
                "Run the alkaline clean first for biofilm/organics, rinse completely, then run the acid clean for precipitate/metal oxides."
            )

        st.write(chemical_step)
        with st.expander(ui_text("Procedura operativa indicativa", "Indicative operating procedure"), expanded=True):
            st.markdown(ui_text(
                """
1. Registrare prestazioni normalizzate, pressioni, portate, temperatura, pH e conducibilità prima del CIP.
2. Fermare la RO e spiazzare alimento/concentrato con permeato o acqua DI priva di durezza, metalli e cloro, a bassa pressione.
3. Preparare soluzione fresca usando esclusivamente chimico compatibile con marca e modello delle membrane. Rispettare pH, temperatura, concentrazione e tempo del costruttore e della SDS.
4. Ricircolare a bassa pressione e alta velocità tangenziale, nella direzione normale del flusso. Lasciare sempre il lato permeato aperto a pressione atmosferica.
5. Alternare ricircolo e ammollo secondo la procedura del fornitore; controllare pH, temperatura, conducibilità e torbidità. Sostituire la soluzione se si satura o il pH deriva sensibilmente.
6. Scaricare e risciacquare con permeato/DI fino a pH e conducibilità prossimi all'acqua di risciacquo. Non mescolare mai acido e base.
7. Riavviare gradualmente, inviare il permeato a scarico finché rientra in specifica e confrontare subito le prestazioni normalizzate con il dato pre-CIP e la baseline.
""",
                """
1. Record normalised performance, pressures, flows, temperature, pH and conductivity before the CIP.
2. Stop the RO and displace feed/concentrate with low-pressure permeate or DI water free of hardness, metals and chlorine.
3. Prepare a fresh solution using only a cleaner compatible with the membrane make and model. Follow the manufacturer's and SDS limits for pH, temperature, concentration and exposure time.
4. Recirculate at low pressure and high crossflow in the normal feed direction. Always keep the permeate side open to atmospheric pressure.
5. Alternate recirculation and soaking according to the supplier procedure; monitor pH, temperature, conductivity and turbidity. Replace the solution if it becomes loaded or pH drifts materially.
6. Drain and rinse with permeate/DI water until pH and conductivity approach rinse-water values. Never mix acid and caustic solutions.
7. Restart gradually, divert permeate to drain until it meets specification, and immediately compare normalised post-CIP performance with pre-CIP data and baseline.
"""
            ))

    st.info(ui_text(
        "La dashboard non imposta volutamente concentrazione, pH, temperatura o durata: questi limiti devono essere configurati dopo aver confermato marca/modello delle membrane e il detergente disponibile. Per membrane in poliammide evitare cloro e altri ossidanti salvo esplicita autorizzazione del costruttore.",
        "The dashboard intentionally does not prescribe concentration, pH, temperature or duration: configure these limits only after confirming the membrane make/model and available cleaner. For polyamide membranes, avoid chlorine and other oxidants unless explicitly authorised by the manufacturer."
    ))

    with st.expander(ui_text("Soglie e logica usate", "Thresholds and logic used")):
        st.markdown(ui_text(
            """
- **Preallarme:** permeabilità normalizzata -10%, ΔP normalizzato +10% oppure passaggio salino +5%.
- **CIP da eseguire:** permeabilità normalizzata -15%, ΔP normalizzato +15% oppure passaggio salino +10%.
- **Basico:** prevalenza di segnali biofilm/organico/colloidale.
- **Acido:** prevalenza di segnali scaling/precipitato/ossidi metallici.
- **Sequenziale:** quadro misto o ambiguo; se è plausibile biofilm/organico, la sequenza parte dal basico, con risciacquo completo prima dell'acido.
""",
            """
- **Early warning:** normalised permeability -10%, normalised ΔP +10%, or salt passage +5%.
- **CIP due:** normalised permeability -15%, normalised ΔP +15%, or salt passage +10%.
- **Alkaline:** biological/organic/colloidal signals predominate.
- **Acid:** scaling/precipitate/metal-oxide signals predominate.
- **Sequential:** mixed or ambiguous profile; when biofilm/organics are plausible, start with alkaline cleaning and rinse completely before acid cleaning.
"""
        ))

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


def _render_cip_forecast_notice(days, stable_message, forecast_subject):
    """Colora la previsione in base all'urgenza, evitando allarmi rossi molto lontani."""
    if days == 999:
        st.success(stable_message)
        return

    message = ui_text(
        f"{forecast_subject} stimata tra circa **{days}** giorni (proiezione indicativa).",
        f"{forecast_subject} estimated in about **{days}** days (indicative projection)."
    )
    if days >= 180:
        st.success(message)
    elif days >= 60:
        st.info(message)
    elif days >= 30:
        st.warning(message)
    else:
        st.error(message)


def render_predittiva(df_ro, df_uf, df_nas, baseline_ro, latest_ro, baseline_uf, latest_uf, config_attuale, impianto_scelto):
    st.header("🔮 Analisi Predittiva e Stato di Salute")
    dp_predictive_col = 'dp_ro_norm_smooth' if 'dp_ro_norm_smooth' in df_ro.columns else 'dp_ro_smooth'
    L_PERM_RO, L_DPCF01, L_DPRO, L_DP_CALZE, L_TMP_UF = baseline_ro['perm_norm_smooth'] * 0.85, 1.0, baseline_ro[dp_predictive_col] * 1.15, 1.0, 1.5
    
    g_ro = stima_giorni_rimanenti(df_ro, 'perm_norm_smooth', L_PERM_RO, False)
    g_dp = stima_giorni_rimanenti(df_ro, dp_predictive_col, L_DPRO, True)
    g_cf = stima_giorni_rimanenti(df_ro[df_ro['dp_cf01'] > 0.05].copy(), 'dp_cf01', L_DPCF01)
    df_calze = df_ro[df_ro['pit007'] > 0.05].copy() if config_attuale["has_bag_filters"] and 'pit007' in df_ro.columns else pd.DataFrame()
    g_calze = stima_giorni_rimanenti(df_calze, 'pit007', L_DP_CALZE) if not df_calze.empty else None
    g_uf = stima_giorni_rimanenti(df_uf, 'uftmp', L_TMP_UF) if config_attuale["has_uf"] and not df_uf.empty else None

    diagnosis_tab_label = ui_text("🧪 Diagnosi & CIP", "🧪 Diagnosis & CIP")
    health_tab_label = ui_text("📉 Health Index RO", "📉 RO Health Index")
    tab_labels = ["📊 Cruscotto Salute", health_tab_label, diagnosis_tab_label, "💧 Membrane (Perm)", "🧱 Fouling Spaziatori (ΔP)"]
    if config_attuale["has_uf"]: tab_labels.append("🟢 Membrane UF")
    if config_attuale["has_bag_filters"]: tab_labels.append("🧦 Filtri a Calza")
    tab_labels.extend(["🗑️ Cartucce CF01", "⛨ Diagnostica Motori"])

    tab_map = dict(zip(tab_labels, st.tabs(tab_labels)))

    with tab_map["📊 Cruscotto Salute"]:
        cards = [
            ("Membrane RO (ASTM)", get_health_score(latest_ro['perm_norm_smooth'], baseline_ro['perm_norm_smooth'], L_PERM_RO, False), g_ro),
            (ui_text("Spaziatori RO (ΔP norm.)", "RO spacers (normalised ΔP)"), get_health_score(latest_ro[dp_predictive_col], baseline_ro[dp_predictive_col], L_DPRO, True), g_dp),
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

        st.caption(
            ui_text(
                "Questi Health Score descrivono la posizione attuale rispetto alle soglie. "
                "Il tab Health Index RO aggiunge memoria temporale e inerzia; Diagnosi & CIP "
                "descrive invece la compatibilità dei segnali correnti con le possibili cause.",
                "These Health Scores describe the current position relative to the thresholds. "
                "The RO Health Index tab adds temporal memory and inertia; Diagnosis & CIP "
                "instead describes how compatible the current signals are with possible causes."
            )
        )

    with tab_map[health_tab_label]:
        st.subheader(
            ui_text(
                "Indice di salute persistente delle membrane e del circuito RO",
                "Persistent health index of RO membranes and hydraulic circuit"
            )
        )

        date_health = pd.to_datetime(df_ro.get("date_str"), errors="coerce").dropna()

        if date_health.empty:
            st.info("Dati insufficienti")
        else:
            data_min_health = date_health.min().date()
            data_max_health = date_health.max().date()
            health_key = f"health_baseline_{impianto_scelto}"

            with st.expander(
                ui_text(
                    "Impostazione baseline Health Index",
                    "Health Index baseline setting"
                ),
                expanded=False
            ):
                baseline_health_date = st.date_input(
                    ui_text(
                        "Data baseline (ultima condizione pulita / CIP / sostituzione):",
                        "Baseline date (last clean condition / CIP / replacement):"
                    ),
                    value=data_min_health,
                    min_value=data_min_health,
                    max_value=data_max_health,
                    key=health_key
                )

            health_df = calcola_health_index_ro(
                df_ro,
                baseline_date=baseline_health_date
            )

            if health_df.empty:
                st.info("Dati insufficienti")
            else:
                latest_h = health_df.iloc[-1]
                score_h = float(latest_h["health_index"])

                target_7d = latest_h["date"] - pd.Timedelta(days=7)
                storico_precedente = health_df[
                    health_df["date"] <= target_7d
                ]
                ref_7d = (
                    storico_precedente.iloc[-1]
                    if not storico_precedente.empty
                    else health_df.iloc[0]
                )
                delta_7d = score_h - float(ref_7d["health_index"])

                ultimi_7 = health_df[
                    health_df["date"] >= latest_h["date"] - pd.Timedelta(days=6)
                ]
                quality_h = (
                    float(ultimi_7["data_quality"].mean())
                    if not ultimi_7.empty
                    else np.nan
                )

                h1, h2, h3, h4 = st.columns(4)
                h1.metric(
                    ui_text("Health Index RO persistente", "Persistent RO Health Index"),
                    f"{score_h:.0f}%",
                    f"{delta_7d:+.1f} pt",
                    delta_color="normal"
                )
                h2.metric(
                    ui_text("Variazione 7 giorni", "7-day change"),
                    f"{delta_7d:+.1f} pt"
                )
                h3.metric(
                    ui_text("Stato Health Index", "Health Index status"),
                    ui_text(
                        stato_health_index(score_h),
                        {
                            "Buono": "Good",
                            "Da monitorare": "Monitor",
                            "Attenzione": "Warning",
                            "Critico": "Critical",
                            "N/D": "N/A"
                        }.get(stato_health_index(score_h), stato_health_index(score_h))
                    )
                )
                h4.metric(
                    ui_text("Qualità dati Health Index", "Health Index data quality"),
                    f"{quality_h:.0f}%" if np.isfinite(quality_h) else "N/D"
                )

                c1, c2, c3 = st.columns(3)
                c1.metric(
                    ui_text("Componente permeabilità", "Permeability component"),
                    f"{latest_h['health_perm']:.0f}%"
                )
                c2.metric(
                    ui_text("Componente ΔP", "ΔP component"),
                    f"{latest_h['health_dp']:.0f}%"
                )
                c3.metric(
                    ui_text("Componente passaggio salino", "Salt-passage component"),
                    f"{latest_h['health_sp']:.0f}%"
                )

                fig_health = go.Figure()
                fig_health.add_trace(go.Scatter(
                    x=health_df["date"],
                    y=health_df["health_raw"],
                    mode="lines",
                    name=ui_text("Health Index grezzo", "Raw Health Index"),
                    line=dict(width=1, dash="dot"),
                    opacity=0.45
                ))
                fig_health.add_trace(go.Scatter(
                    x=health_df["date"],
                    y=health_df["health_index"],
                    mode="lines",
                    name=ui_text("Health Index persistente", "Persistent Health Index"),
                    line=dict(width=4)
                ))
                fig_health.add_hline(
                    y=85,
                    line_dash="dot",
                    annotation_text=ui_text(
                        "Soglia monitoraggio", "Monitoring threshold"
                    )
                )
                fig_health.add_hline(
                    y=70,
                    line_dash="dash",
                    annotation_text=ui_text(
                        "Soglia attenzione", "Warning threshold"
                    )
                )
                fig_health.add_hline(
                    y=50,
                    line_dash="dashdot",
                    annotation_text=ui_text(
                        "Soglia critica", "Critical threshold"
                    )
                )
                fig_health.update_layout(
                    title=ui_text(
                        "Health Index storico RO",
                        "Historical RO Health Index"
                    ),
                    yaxis_title="Health Index (%)",
                    yaxis=dict(range=[0, 105]),
                    hovermode="x unified",
                    margin=dict(l=20, r=20, t=55, b=20)
                )
                st.plotly_chart(
                    fig_health,
                    use_container_width=True,
                    key=f"health_index_chart_{impianto_scelto}"
                )

                st.info(
                    ui_text(
                        "Il Health Index è distinto dalla diagnosi corrente. Usa mediane "
                        "giornaliere, permeabilità normalizzata, ΔP RO normalizzato e "
                        "passaggio salino. Il peggioramento viene recepito più rapidamente "
                        "del recupero: una sola giornata buona non cancella il degrado "
                        "precedente. Dopo un CIP o una sostituzione imposta qui una nuova "
                        "data di baseline.",
                        "The Health Index is separate from the current diagnosis. It uses "
                        "daily medians, normalised permeability, normalised RO ΔP and salt "
                        "passage. Deterioration is incorporated faster than recovery, so "
                        "one good day does not erase previous degradation. After CIP or "
                        "replacement, set a new baseline date here."
                    )
                )

    with tab_map[diagnosis_tab_label]:
        render_diagnosi_cip_ro(df_ro, baseline_ro, latest_ro)

    with tab_map["💧 Membrane (Perm)"]:
        if g_ro is None: 
            st.info("Dati insufficienti per la previsione delle membrane RO.")
        else:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.metric("Indice Pulito a 25°C", f"{latest_ro['perm_norm_smooth']:.2f}", f"{latest_ro['perm_norm_smooth'] - baseline_ro['perm_norm_smooth']:+.2f}")
                _render_cip_forecast_notice(
                    g_ro,
                    ui_text("Situazione stabile", "Stable condition"),
                    ui_text("Soglia CIP sulla permeabilità", "Permeability CIP threshold"),
                )
                    
            with col_b:
                fig = crea_grafico_previsione(df_ro, 'perm_norm_smooth', 'Previsione Fouling Membrane RO', 'Trend reale (media 24h)', 'Regressione / previsione', 30, L_PERM_RO, 'Limite CIP (85%)', yaxis_title='Permeabilità normalizzata')
                if fig: st.plotly_chart(fig, use_container_width=True)

    with tab_map["🧱 Fouling Spaziatori (ΔP)"]:
        if g_dp is None: 
            st.info("Dati insufficienti per la previsione degli spaziatori RO.")
        else:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.metric(ui_text("ΔP normalizzato attuale", "Current normalised ΔP"), f"{latest_ro[dp_predictive_col]:.2f} bar", f"{latest_ro[dp_predictive_col] - baseline_ro[dp_predictive_col]:+.2f} bar", delta_color="inverse")
                _render_cip_forecast_notice(
                    g_dp,
                    ui_text("Situazione idraulica stabile", "Stable hydraulic condition"),
                    ui_text("Soglia CIP sul ΔP", "ΔP CIP threshold"),
                )
                    
            with col_b:
                fig = crea_grafico_previsione(df_ro, dp_predictive_col, 'Previsione Fouling Spaziatori RO', ui_text('ΔP normalizzato (media 24h)', 'Normalised ΔP (24 h average)'), 'Previsione fouling', 30, L_DPRO, 'Limite rischio CIP (+15%)', baseline_ro[dp_predictive_col], 'Baseline installazione', ui_text('Salto di pressione normalizzato (bar)', 'Normalised pressure drop (bar)'), 'up')
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
                        
    st.info(ui_text(
        """💡 **Guida alla Lettura - Modello Predittivo:**
        - **Health Score:** posizione istantanea dell'asset rispetto alla baseline e alla soglia ingegneristica.
        - **Health Index RO:** indice storico persistente 0–100. Integra permeabilità, ΔP normalizzato e passaggio salino con memoria temporale, quindi è molto meno sensibile alle oscillazioni di un singolo giorno.
        - **Diagnosi & CIP:** valuta la compatibilità dei segnali correnti con diversi meccanismi di fouling; non è una probabilità statistica di guasto.
        - **Previsioni:** le date sono stimate tramite regressione dei trend storici verso le soglie ingegneristiche.""",
        """💡 **Reading Guide — Predictive Model:**
        - **Health Score:** instantaneous position of the asset relative to its baseline and engineering threshold.
        - **RO Health Index:** persistent historical 0–100 index combining permeability, normalised ΔP and salt passage with temporal memory, making it much less sensitive to a single day's fluctuations.
        - **Diagnosis & CIP:** evaluates how compatible current signals are with different fouling mechanisms; it is not a statistical failure probability.
        - **Forecasts:** dates are estimated by regressing historical trends towards engineering thresholds."""
    ))

def render_confronto(df_ro, df_uf, config_attuale):
    st.header("⚖️ Analisi Comparativa (A/B Test)")
    df_merged = pd.merge(df_ro, df_uf, on=['timestamp', 'date_str'], how='outer', suffixes=('_RO', '_UF')) if not df_uf.empty else df_ro.copy()
    df_merged['DataOra'] = pd.to_datetime(df_merged['date_str'])

    dp_compare_col = "dp_ro_norm_smooth" if "dp_ro_norm_smooth" in df_ro.columns else "dp_ro_smooth"
    metriche_disp = {
        "Permeabilità Normalizzata (Fouling RO)": "perm_norm_smooth",
        ui_text("Salto di Pressione Normalizzato (ΔP RO)", "Normalised pressure drop (RO ΔP)"): dp_compare_col,
        "Reiezione Salina (%)": "sr_norm"
    }
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


@st.cache_data(ttl=300)
def load_produzione_atm(impianto_scelto):
    """Carica e normalizza produzione da PDF e vendite ATM per l'impianto scelto."""
    nome_db = "Kaktus" if "Kaktus" in impianto_scelto else "Pingwe"

    from supabase import create_client
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

    # Funzione interna per bypassare il limite di 1000 righe di Supabase
    def fetch_all_by_impianto(table_name, impianto_name):
        all_data = []
        offset = 0
        limit = 1000
        while True:
            res = (
                supabase.table(table_name)
                .select("*")
                .eq("impianto", impianto_name)
                .order("data_rif", desc=False)
                .range(offset, offset + limit - 1)
                .execute()
            )
            if not res.data:
                break
            all_data.extend(res.data)
            if len(res.data) < limit:
                break
            offset += limit
        return all_data

    # Estrazione completa senza limiti
    data_pdf = fetch_all_by_impianto("produzione_pdf", nome_db)
    data_atm = fetch_all_by_impianto("storico_atm", nome_db)

    df_pdf = pd.DataFrame(data_pdf)
    df_atm = pd.DataFrame(data_atm)

    if not df_pdf.empty:
        df_pdf["data_rif"] = pd.to_datetime(df_pdf["data_rif"], errors="coerce").dt.normalize()
        for col in ["permeato", "concentrato", "insolation"]:
            if col in df_pdf.columns:
                df_pdf[col] = pd.to_numeric(df_pdf[col], errors="coerce")
        df_pdf = df_pdf.dropna(subset=["data_rif"]).sort_values("data_rif").reset_index(drop=True)

    if not df_atm.empty:
        df_atm["data_rif"] = pd.to_datetime(df_atm["data_rif"], errors="coerce").dt.normalize()
        if "litri_erogati" in df_atm.columns:
            df_atm["litri_erogati"] = pd.to_numeric(df_atm["litri_erogati"], errors="coerce")
        df_atm = df_atm.dropna(subset=["data_rif"]).sort_values("data_rif").reset_index(drop=True)

    return df_pdf, df_atm, nome_db


def render_produzione_atm(impianto_scelto):
    st.header("📊 Produzione e vendite ATM")

    try:
        df_pdf, df_atm, nome_db = load_produzione_atm(impianto_scelto)
    except Exception as e:
        st.error(f"Errore nel caricamento dei dati Produzione/ATM: {e}")
        return

    if df_pdf.empty and df_atm.empty:
        st.info(f"Nessun dato di produzione o ATM trovato per {nome_db}.")
        return

    # ---------------------------------------------------------
    # Funzioni locali
    # ---------------------------------------------------------
    nomi_mesi = {
        1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
        5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
        9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
    }

    def etichetta_mese(valore):
        periodo_locale = pd.Period(valore, freq="M")
        return f"{nomi_mesi[periodo_locale.month]} {periodo_locale.year}"

    def formatta_intero(valore, unita):
        if valore is None or pd.isna(valore) or not np.isfinite(float(valore)):
            return "N/D"
        return f"{float(valore):,.0f} {unita}"

    def aggrega_giornaliero(df_pdf_filtrato, df_atm_filtrato):
        if not df_pdf_filtrato.empty:
            aggregazioni_pdf = {}
            if "permeato" in df_pdf_filtrato.columns:
                aggregazioni_pdf["permeato"] = "sum"
            if "concentrato" in df_pdf_filtrato.columns:
                aggregazioni_pdf["concentrato"] = "sum"
            if "insolation" in df_pdf_filtrato.columns:
                aggregazioni_pdf["insolation"] = "mean"

            prod_giorno_locale = (
                df_pdf_filtrato.groupby("data_rif", as_index=False).agg(aggregazioni_pdf)
                if aggregazioni_pdf
                else pd.DataFrame(columns=["data_rif"])
            )
        else:
            prod_giorno_locale = pd.DataFrame(
                columns=["data_rif", "permeato", "concentrato"]
            )

        if not df_atm_filtrato.empty and "litri_erogati" in df_atm_filtrato.columns:
            atm_giorno_locale = (
                df_atm_filtrato.groupby("data_rif", as_index=False)["litri_erogati"]
                .sum()
                .rename(columns={"litri_erogati": "atm_litri"})
            )
        else:
            atm_giorno_locale = pd.DataFrame(columns=["data_rif", "atm_litri"])

        return prod_giorno_locale, atm_giorno_locale

    def crea_calendario_giornaliero(data_inizio, data_fine, prod_giorno, atm_giorno):
        calendario_locale = pd.DataFrame({
            "data_rif": pd.date_range(data_inizio, data_fine, freq="D")
        })

        giornaliero_locale = calendario_locale.merge(
            prod_giorno, on="data_rif", how="left"
        )
        giornaliero_locale = giornaliero_locale.merge(
            atm_giorno, on="data_rif", how="left"
        )

        for col in ["permeato", "concentrato", "atm_litri"]:
            if col not in giornaliero_locale.columns:
                giornaliero_locale[col] = np.nan

        giornaliero_locale["atm_m3"] = giornaliero_locale["atm_litri"] / 1000.0
        return giornaliero_locale

    def totale_colonna(df, colonna):
        if colonna not in df.columns or not df[colonna].notna().any():
            return np.nan
        return df[colonna].sum(min_count=1)

    def crea_grafico_barre(dati_giornalieri, serie, titolo):
        """Crea il grafico a barre per mese o intervallo personalizzato."""
        if dati_giornalieri is None or dati_giornalieri.empty or not serie:
            return None

        fig_locale = go.Figure()

        if "Produzione" in serie:
            fig_locale.add_trace(go.Bar(
                x=dati_giornalieri["data_rif"],
                y=dati_giornalieri["permeato"],
                name="Produzione",
                marker_color="#2E86DE",
                offsetgroup="produzione",
                texttemplate="%{y:,.0f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "%{x|%d/%m/%Y}<br>"
                    "Produzione: %{y:,.0f} m³<extra></extra>"
                )
            ))

        if "Vendite ATM" in serie:
            fig_locale.add_trace(go.Bar(
                x=dati_giornalieri["data_rif"],
                y=dati_giornalieri["atm_m3"],
                name="Vendite ATM",
                marker_color="#F39C12",
                offsetgroup="atm",
                texttemplate="%{y:,.0f}",
                textposition="outside",
                cliponaxis=False,
                customdata=dati_giornalieri[["atm_litri"]],
                hovertemplate=(
                    "%{x|%d/%m/%Y}<br>"
                    "Venduto: %{y:,.0f} m³<br>"
                    "(%{customdata[0]:,.0f} L)<extra></extra>"
                )
            ))

        if "Concentrato" in serie:
            fig_locale.add_trace(go.Bar(
                x=dati_giornalieri["data_rif"],
                y=dati_giornalieri["concentrato"],
                name="Concentrato",
                marker_color="#7F8C8D",
                offsetgroup="concentrato",
                texttemplate="%{y:,.0f}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "%{x|%d/%m/%Y}<br>"
                    "Concentrato: %{y:,.0f} m³<extra></extra>"
                )
            ))

        fig_locale.update_layout(
            title=titolo,
            xaxis_title="Data",
            yaxis_title="Volume giornaliero (m³)",
            barmode="group",
            bargap=0.22,
            bargroupgap=0.04,
            hovermode="x unified",
            legend_title_text="Dato",
            uniformtext_minsize=8,
            uniformtext_mode="show",
            margin=dict(l=20, r=20, t=85, b=20)
        )
        fig_locale.update_yaxes(rangemode="tozero", automargin=True)
        return fig_locale

    # ---------------------------------------------------------
    # Intervallo complessivo disponibile
    # ---------------------------------------------------------
    date_disponibili = []
    if not df_pdf.empty:
        date_disponibili.extend(df_pdf["data_rif"].dropna().tolist())
    if not df_atm.empty:
        date_disponibili.extend(df_atm["data_rif"].dropna().tolist())

    data_min = pd.Timestamp(min(date_disponibili)).normalize()
    data_max = pd.Timestamp(max(date_disponibili)).normalize()

    # ---------------------------------------------------------
    # Selezione mese e serie da mostrare
    # ---------------------------------------------------------
    mesi = set()
    if not df_pdf.empty:
        mesi.update(df_pdf["data_rif"].dt.to_period("M").astype(str).tolist())
    if not df_atm.empty:
        mesi.update(df_atm["data_rif"].dt.to_period("M").astype(str).tolist())
    mesi = sorted(mesi, reverse=True)

    serie_disponibili = []
    if not df_pdf.empty and "permeato" in df_pdf.columns:
        serie_disponibili.append("Produzione")
    if not df_atm.empty and "litri_erogati" in df_atm.columns:
        serie_disponibili.append("Vendite ATM")
    if not df_pdf.empty and "concentrato" in df_pdf.columns:
        serie_disponibili.append("Concentrato")

    col_mese, col_serie = st.columns([1, 2])
    with col_mese:
        mese_scelto = st.selectbox(
            "Mese da analizzare:",
            options=mesi,
            format_func=etichetta_mese
        )

    with col_serie:
        serie_predefinite = [
            serie for serie in ["Produzione", "Vendite ATM"]
            if serie in serie_disponibili
        ]
        serie_scelte = st.multiselect(
            "Dati da visualizzare nel grafico:",
            options=serie_disponibili,
            default=serie_predefinite,
            help=(
                "Puoi mostrare Produzione, Vendite ATM e Concentrato "
                "singolarmente oppure in qualsiasi combinazione. "
                "Il concentrato non è selezionato di default."
            )
        )

    # ---------------------------------------------------------
    # Riepilogo del mese selezionato
    # ---------------------------------------------------------
    periodo = pd.Period(mese_scelto, freq="M")
    inizio_mese = periodo.start_time.normalize()
    fine_mese = periodo.end_time.normalize()
    # Usa il fuso orario italiano per evitare differenze di data
    # quando l'app Streamlit è ospitata su un server in UTC.
    oggi = (
        pd.Timestamp.now(tz="Europe/Rome")
        .tz_localize(None)
        .normalize()
    )
    mese_corrente = periodo == oggi.to_period("M")

    # I dati giornalieri ricevuti oggi si riferiscono sempre a ieri.
    # Per il mese corrente il periodo utile termina quindi a ieri:
    # il 5 del mese la media viene calcolata su 4 giorni.
    fine_periodo_media = (
        min(fine_mese, oggi - pd.Timedelta(days=1))
        if mese_corrente
        else fine_mese
    )

    giorni_periodo = (
        (fine_periodo_media - inizio_mese).days + 1
        if fine_periodo_media >= inizio_mese
        else 0
    )

    pdf_mese = (
        df_pdf[df_pdf["data_rif"].dt.to_period("M") == periodo].copy()
        if not df_pdf.empty
        else pd.DataFrame()
    )
    atm_mese = (
        df_atm[df_atm["data_rif"].dt.to_period("M") == periodo].copy()
        if not df_atm.empty
        else pd.DataFrame()
    )

    prod_giorno, atm_giorno = aggrega_giornaliero(pdf_mese, atm_mese)
    giornaliero = crea_calendario_giornaliero(
        inizio_mese, fine_periodo_media, prod_giorno, atm_giorno
    )

    totale_prodotto = totale_colonna(giornaliero, "permeato")
    totale_concentrato = totale_colonna(giornaliero, "concentrato")
    totale_atm_litri = totale_colonna(giornaliero, "atm_litri")
    totale_atm_m3 = (
        totale_atm_litri / 1000.0
        if pd.notna(totale_atm_litri)
        else np.nan
    )

    media_prod = (
        totale_prodotto / giorni_periodo
        if giorni_periodo > 0 and pd.notna(totale_prodotto)
        else np.nan
    )
    media_concentrato = (
        totale_concentrato / giorni_periodo
        if giorni_periodo > 0 and pd.notna(totale_concentrato)
        else np.nan
    )
    media_atm_m3 = (
        totale_atm_m3 / giorni_periodo
        if giorni_periodo > 0 and pd.notna(totale_atm_m3)
        else np.nan
    )

    st.subheader(f"Riepilogo mensile — {etichetta_mese(mese_scelto)}")

    t1, t2, t3 = st.columns(3)
    t1.metric("Totale prodotto", formatta_intero(totale_prodotto, "m³"))
    t2.metric("Totale venduto ATM", formatta_intero(totale_atm_m3, "m³"))
    t3.metric("Totale concentrato", formatta_intero(totale_concentrato, "m³"))

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Media giornaliera prodotta",
        formatta_intero(media_prod, "m³/giorno")
    )
    m2.metric(
        "Media giornaliera venduta",
        formatta_intero(media_atm_m3, "m³/giorno")
    )
    m3.metric(
        "Media giornaliera concentrato",
        formatta_intero(media_concentrato, "m³/giorno")
    )

    if mese_corrente:
        if giorni_periodo > 0:
            st.caption(
                f"Le medie mensili sono calcolate su {giorni_periodo} "
                "giorni trascorsi del mese, fino a ieri."
            )
        else:
            st.caption(
                "Non sono ancora disponibili giorni completi nel mese corrente."
            )
    else:
        st.caption(
            f"Le medie mensili sono calcolate su {giorni_periodo} "
            "giorni di calendario."
        )

    # ---------------------------------------------------------
    # Confronto tra due periodi personalizzati (Side-by-side)
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader(ui_text("⚖️ Confronto periodi personalizzati", "⚖️ Custom period comparison"))
    
    # Calcolo dei default: Periodo A (ultimi 30 giorni), Periodo B (i 30 giorni ancora precedenti)
    default_a_end = data_max
    default_a_start = max(data_min, default_a_end - pd.Timedelta(days=29))
    default_b_end = max(data_min, default_a_start - pd.Timedelta(days=1))
    default_b_start = max(data_min, default_b_end - pd.Timedelta(days=29))

    col_a, col_b = st.columns(2)

    def render_periodo_confronto(container, label_periodo, default_dates, key_suffix):
        with container:
            st.markdown(f"#### {label_periodo}")
            intervallo = st.date_input(
                ui_text("Seleziona il periodo da analizzare:", "Select the period to analyse:"),
                value=default_dates,
                min_value=data_min.date(),
                max_value=data_max.date(),
                key=f"periodo_personalizzato_produzione_atm_{key_suffix}"
            )

            if isinstance(intervallo, (list, tuple)) and len(intervallo) == 2:
                data_da = pd.Timestamp(intervallo[0]).normalize()
                data_a = pd.Timestamp(intervallo[1]).normalize()

                if data_da > data_a:
                    st.warning(ui_text("La data iniziale deve precedere la data finale.", "Start date must precede end date."))
                    return
                
                giorni_custom = max(1, (data_a - data_da).days + 1)

                pdf_custom = (
                    df_pdf[(df_pdf["data_rif"] >= data_da) & (df_pdf["data_rif"] <= data_a)].copy()
                    if not df_pdf.empty else pd.DataFrame()
                )
                atm_custom = (
                    df_atm[(df_atm["data_rif"] >= data_da) & (df_atm["data_rif"] <= data_a)].copy()
                    if not df_atm.empty else pd.DataFrame()
                )

                prod_custom, atm_custom_giorno = aggrega_giornaliero(pdf_custom, atm_custom)
                giornaliero_custom = crea_calendario_giornaliero(data_da, data_a, prod_custom, atm_custom_giorno)

                totale_prod_custom = totale_colonna(giornaliero_custom, "permeato")
                totale_conc_custom = totale_colonna(giornaliero_custom, "concentrato")
                totale_atm_custom_l = totale_colonna(giornaliero_custom, "atm_litri")
                totale_atm_custom_m3 = (totale_atm_custom_l / 1000.0 if pd.notna(totale_atm_custom_l) else np.nan)

                media_prod_custom = (totale_prod_custom / giorni_custom if pd.notna(totale_prod_custom) else np.nan)
                media_atm_custom = (totale_atm_custom_m3 / giorni_custom if pd.notna(totale_atm_custom_m3) else np.nan)
                media_conc_custom = (totale_conc_custom / giorni_custom if pd.notna(totale_conc_custom) else np.nan)

                p1, p2, p3 = st.columns(3)
                p1.metric(ui_text("Media Prod.", "Avg Prod."), formatta_intero(media_prod_custom, ui_text("m³/g", "m³/d")))
                p2.metric(ui_text("Media Vendite", "Avg Sales"), formatta_intero(media_atm_custom, ui_text("m³/g", "m³/d")))
                p3.metric(ui_text("Media Conc.", "Avg Conc."), formatta_intero(media_conc_custom, ui_text("m³/g", "m³/d")))

                st.caption(
                    ui_text(f"Dal {data_da.strftime('%d/%m/%Y')} al {data_a.strftime('%d/%m/%Y')} ({giorni_custom} gg)", 
                            f"From {data_da.strftime('%d/%m/%Y')} to {data_a.strftime('%d/%m/%Y')} ({giorni_custom} days)")
                )

                if not serie_scelte:
                    st.info(ui_text("Seleziona almeno una serie nel menu in alto.", "Select at least one series in the top menu."))
                else:
                    fig_periodo = crea_grafico_barre(
                        giornaliero_custom,
                        serie_scelte,
                        ui_text("Volumi giornalieri", "Daily volumes")
                    )
                    if fig_periodo is not None:
                        # Ottimizziamo l'altezza e i margini per la visualizzazione a due colonne
                        fig_periodo.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
                        st.plotly_chart(
                            fig_periodo,
                            use_container_width=True,
                            key=f"grafico_periodo_personalizzato_{key_suffix}"
                        )
            else:
                st.info(ui_text("Seleziona una data iniziale e una data finale.", "Select a start date and an end date."))

    # Disegniamo i due riquadri affiancati
    render_periodo_confronto(col_a, ui_text("Periodo A", "Period A"), [default_a_start.date(), default_a_end.date()], "A")
    render_periodo_confronto(col_b, ui_text("Periodo B", "Period B"), [default_b_start.date(), default_b_end.date()], "B")

    # ---------------------------------------------------------
    # Grafico mensile
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("#### Grafico del mese selezionato")

    if not serie_scelte:
        st.info("Seleziona almeno una serie da visualizzare nel grafico.")
    else:
        fig_mese = crea_grafico_barre(
            giornaliero,
            serie_scelte,
            f"Volumi giornalieri — {etichetta_mese(mese_scelto)}"
        )
        if fig_mese is not None:
            st.plotly_chart(
                fig_mese,
                use_container_width=True,
                key="grafico_mese_produzione_atm"
            )

    # ---------------------------------------------------------
    # Tabelle
    # ---------------------------------------------------------
    tab_giorno, tab_pdf, tab_atm = st.tabs([
        "Riepilogo giornaliero",
        "Dettaglio produzione PDF",
        "Dettaglio ATM"
    ])

    with tab_giorno:
        tabella_giorno = giornaliero.copy()
        tabella_giorno["Data"] = tabella_giorno["data_rif"].dt.strftime("%d/%m/%Y")

        colonne_tabella = ["Data"]
        rinomina = {}

        if "permeato" in tabella_giorno.columns:
            colonne_tabella.append("permeato")
            rinomina["permeato"] = "Prodotto (m³)"

        if "concentrato" in tabella_giorno.columns:
            colonne_tabella.append("concentrato")
            rinomina["concentrato"] = "Concentrato (m³)"

        colonne_tabella.extend(["atm_litri", "atm_m3"])
        rinomina.update({
            "atm_litri": "Venduto ATM (L)",
            "atm_m3": "Venduto ATM (m³)"
        })

        st.dataframe(
            tabella_giorno[colonne_tabella].rename(columns=rinomina),
            use_container_width=True,
            hide_index=True
        )

    with tab_pdf:
        if pdf_mese.empty:
            st.info("Nessun dato di produzione PDF nel mese selezionato.")
        else:
            colonne_pdf = [
                col for col in
                [
                    "data_rif", "permeato", "concentrato",
                    "insolation", "file_origine"
                ]
                if col in pdf_mese.columns
            ]
            st.dataframe(
                pdf_mese[colonne_pdf],
                use_container_width=True,
                hide_index=True
            )

    with tab_atm:
        if atm_mese.empty:
            st.info("Nessun dato ATM nel mese selezionato.")
        else:
            colonne_atm = [
                col for col in ["data_rif", "atm_id", "litri_erogati"]
                if col in atm_mese.columns
            ]
            st.dataframe(
                atm_mese[colonne_atm],
                use_container_width=True,
                hide_index=True
            )


# =========================================================
# REPORT PDF PERIODICI
# =========================================================
def _r(it_text, en_text):
    return en_text if UI_LANGUAGE == "en" else it_text


def _report_format_number(value, unit=""):
    try:
        if value is None or pd.isna(value) or not np.isfinite(float(value)):
            return _r("N/D", "N/A")
        formatted = f"{float(value):,.0f}"
        return f"{formatted} {unit}".strip()
    except (TypeError, ValueError):
        return _r("N/D", "N/A")


def _report_filter_period(df, start_date, end_date, date_col="date_str"):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if date_col in out.columns:
        dates = pd.to_datetime(out[date_col], errors="coerce")
    elif "timestamp" in out.columns:
        dates = pd.to_datetime(
            pd.to_numeric(out["timestamp"], errors="coerce"),
            unit="s",
            errors="coerce",
        )
    else:
        return pd.DataFrame()
    out["_report_date"] = dates
    mask = (
        out["_report_date"].notna()
        & (out["_report_date"] >= pd.Timestamp(start_date))
        & (out["_report_date"] < pd.Timestamp(end_date) + pd.Timedelta(days=1))
    )
    return out.loc[mask].sort_values("_report_date").reset_index(drop=True)


def _report_build_daily(df_pdf, df_atm, start_date, end_date):
    calendar = pd.DataFrame({
        "data_rif": pd.date_range(start_date, end_date, freq="D")
    })

    if df_pdf is not None and not df_pdf.empty:
        pdf = df_pdf.copy()
        pdf["data_rif"] = pd.to_datetime(pdf["data_rif"], errors="coerce").dt.normalize()
        pdf = pdf[
            (pdf["data_rif"] >= pd.Timestamp(start_date))
            & (pdf["data_rif"] <= pd.Timestamp(end_date))
        ]
        aggregations = {}
        for col in ("permeato", "concentrato"):
            if col in pdf.columns:
                pdf[col] = pd.to_numeric(pdf[col], errors="coerce")
                aggregations[col] = "sum"
        if "insolation" in pdf.columns:
            pdf["insolation"] = pd.to_numeric(pdf["insolation"], errors="coerce")
            aggregations["insolation"] = "mean"
        prod_daily = (
            pdf.groupby("data_rif", as_index=False).agg(aggregations)
            if aggregations else pd.DataFrame(columns=["data_rif"])
        )
    else:
        prod_daily = pd.DataFrame(columns=["data_rif", "permeato", "concentrato"])

    if df_atm is not None and not df_atm.empty:
        atm = df_atm.copy()
        atm["data_rif"] = pd.to_datetime(atm["data_rif"], errors="coerce").dt.normalize()
        atm["litri_erogati"] = pd.to_numeric(atm.get("litri_erogati"), errors="coerce")
        atm = atm[
            (atm["data_rif"] >= pd.Timestamp(start_date))
            & (atm["data_rif"] <= pd.Timestamp(end_date))
        ]
        atm_daily = (
            atm.groupby("data_rif", as_index=False)["litri_erogati"]
            .sum()
            .rename(columns={"litri_erogati": "atm_litri"})
        )
    else:
        atm_daily = pd.DataFrame(columns=["data_rif", "atm_litri"])

    daily = calendar.merge(prod_daily, on="data_rif", how="left")
    daily = daily.merge(atm_daily, on="data_rif", how="left")
    for col in ("permeato", "concentrato", "atm_litri"):
        if col not in daily.columns:
            daily[col] = np.nan
    daily["atm_m3"] = daily["atm_litri"] / 1000.0
    return daily


def _report_daily_mean(df, col):
    if df is None or df.empty or col not in df.columns:
        return pd.DataFrame(columns=["date", col])
    work = df[["_report_date", col]].copy()
    work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=["_report_date", col])
    if work.empty:
        return pd.DataFrame(columns=["date", col])
    work["date"] = work["_report_date"].dt.normalize()
    return work.groupby("date", as_index=False)[col].mean()


def _report_motor_stats(df_nas, config_attuale, impianto_scelto):
    if df_nas is None or df_nas.empty:
        return pd.DataFrame()
    rows = []
    install_dates = PUMP_INSTALL_DATES.get(impianto_scelto, {})
    for nas_id, pump_name in config_attuale.get("inverters", {}).items():
        pump = df_nas[df_nas["nas_id"] == nas_id].copy()
        if "freq" not in pump.columns:
            continue
        pump = pump[pd.to_numeric(pump["freq"], errors="coerce") > 10]
        if nas_id in install_dates:
            install_date = pd.to_datetime(install_dates[nas_id], errors="coerce")
            if pd.notna(install_date):
                pump = pump[pump["_report_date"] >= install_date]
        if len(pump) < 3 or not {"current", "freq", "cosphi"}.issubset(pump.columns):
            continue
        current = pd.to_numeric(pump["current"], errors="coerce")
        freq = pd.to_numeric(pump["freq"], errors="coerce")
        cosphi = pd.to_numeric(pump["cosphi"], errors="coerce")
        torque_index = (current / freq).replace([np.inf, -np.inf], np.nan).dropna()
        cosphi = cosphi.replace([np.inf, -np.inf], np.nan).dropna()
        if len(torque_index) < 3 or len(cosphi) < 3:
            continue
        base_idx, last_idx = torque_index.iloc[:3].mean(), torque_index.iloc[-3:].mean()
        base_cos, last_cos = cosphi.iloc[:3].mean(), cosphi.iloc[-3:].mean()
        if not all(np.isfinite(v) for v in (base_idx, last_idx, base_cos, last_cos)) or base_idx <= 0 or base_cos <= 0:
            continue
        mech = ((last_idx - base_idx) / base_idx) * 100
        elec = ((last_cos - base_cos) / base_cos) * 100
        elec_status = _r("Critico", "Critical") if elec < -10 else (_r("Attenzione", "Watch") if elec < -5 else "OK")
        mech_status = _r("Critico", "Critical") if mech > 15 else (_r("Attenzione", "Watch") if mech > 8 else "OK")
        rows.append({
            "ID": nas_id,
            _r("Pompa", "Pump"): tr_text(pump_name),
            _r("Deriva Cosφ", "Cosφ drift"): elec,
            _r("Stato elettrico", "Electrical status"): elec_status,
            _r("Deriva A/Hz", "A/Hz drift"): mech,
            _r("Stato meccanico", "Mechanical status"): mech_status,
        })
    return pd.DataFrame(rows)


def _report_fig_to_png(fig):
    import matplotlib.pyplot as plt
    stream = io.BytesIO()
    fig.savefig(stream, format="png", dpi=155, bbox_inches="tight")
    plt.close(fig)
    stream.seek(0)
    return stream


def _report_chart_daily_volumes(daily, selected_series):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(figsize=(7.2, 3.25))
    dates = pd.to_datetime(daily["data_rif"])
    series = []
    if "Produzione" in selected_series:
        series.append((_r("Produzione", "Production"), pd.to_numeric(daily["permeato"], errors="coerce")))
    if "Vendite ATM" in selected_series:
        series.append((_r("Vendite ATM", "ATM sales"), pd.to_numeric(daily["atm_m3"], errors="coerce")))
    if "Concentrato" in selected_series:
        series.append((_r("Concentrato", "Concentrate"), pd.to_numeric(daily["concentrato"], errors="coerce")))

    count = max(1, len(series))
    width = 0.8 / count
    offsets = (np.arange(count) - (count - 1) / 2) * width
    for idx, (label, values) in enumerate(series):
        bars = ax.bar(dates + pd.to_timedelta(offsets[idx], unit="D"), values, width=width, label=label)
        if len(daily) <= 45:
            ax.bar_label(bars, labels=["" if pd.isna(v) else f"{v:.0f}" for v in values], padding=2, fontsize=6)

    ax.set_title(_r("Produzione e vendite giornaliere", "Daily production and sales"))
    ax.set_ylabel(_r("Volume (m³/giorno)", "Volume (m³/day)"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8, ncol=max(1, len(series)))
    fig.tight_layout()
    return _report_fig_to_png(fig)


def _report_chart_health_index(df_ro, start_date=None, end_date=None):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    # Calcola l'indice sull'intera storia per non azzerare la memoria
    # all'inizio del periodo scelto nel report.
    health = calcola_health_index_ro(df_ro)
    if health.empty:
        return None

    if start_date is not None:
        health = health[
            health["date"] >= pd.Timestamp(start_date).normalize()
        ]
    if end_date is not None:
        health = health[
            health["date"] <= pd.Timestamp(end_date).normalize()
        ]

    if health.empty:
        return None

    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.plot(
        health["date"],
        health["health_raw"],
        linewidth=1,
        linestyle=":",
        alpha=0.35,
        label=_r("Health Index grezzo", "Raw Health Index")
    )
    ax.plot(
        health["date"],
        health["health_index"],
        linewidth=2.4,
        label=_r("Health Index persistente", "Persistent Health Index")
    )
    ax.axhline(85, linestyle=":", linewidth=1, alpha=0.7)
    ax.axhline(70, linestyle="--", linewidth=1, alpha=0.7)
    ax.axhline(50, linestyle="-.", linewidth=1, alpha=0.7)
    ax.set_ylim(0, 105)
    ax.set_title(_r("Health Index storico RO", "Historical RO Health Index"))
    ax.set_ylabel("Health Index (%)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.grid(axis="y", alpha=0.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _report_fig_to_png(fig)


def _report_chart_trend(df, col, title_it, title_en, y_it, y_en, limit=None, baseline=None, forecast_days=30, direction=None):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    daily = _report_daily_mean(df, col)
    if daily.empty:
        return None

    fig, ax = plt.subplots(figsize=(7.2, 3.05))
    ax.plot(daily["date"], daily[col], marker="o", markersize=2.5, linewidth=1.4, label=_r("Dato giornaliero", "Daily value"))

    if len(daily) >= 3 and daily["date"].nunique() >= 2:
        x = (daily["date"] - daily["date"].iloc[0]).dt.total_seconds().to_numpy() / 86400.0
        y = daily[col].to_numpy(dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        if valid.sum() >= 3:
            slope, intercept = np.polyfit(x[valid], y[valid], 1)
            show = np.isfinite(slope) and np.isfinite(intercept)
            if direction == "up":
                show = show and slope > 0
            elif direction == "down":
                show = show and slope < 0
            if show:
                x_future = np.linspace(x[valid].min(), x[valid].max() + forecast_days, 100)
                future_dates = daily["date"].iloc[0] + pd.to_timedelta(x_future, unit="D")
                ax.plot(future_dates, slope * x_future + intercept, linestyle="--", linewidth=1.2, label=_r("Regressione / previsione", "Regression / forecast"))

    if limit is not None and np.isfinite(float(limit)):
        ax.axhline(float(limit), linestyle="--", linewidth=1.1, label=_r("Limite", "Limit"))
    if baseline is not None and np.isfinite(float(baseline)):
        ax.axhline(float(baseline), linestyle=":", linewidth=1.1, label="Baseline")

    ax.set_title(_r(title_it, title_en))
    ax.set_ylabel(_r(y_it, y_en))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    return _report_fig_to_png(fig)


def _report_chart_two_percent(df, col_a, col_b):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    a = _report_daily_mean(df, col_a)
    b = _report_daily_mean(df, col_b)
    if a.empty and b.empty:
        return None
    merged = pd.merge(a, b, on="date", how="outer").sort_values("date")
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    if col_a in merged:
        ax.plot(merged["date"], merged[col_a], marker="o", markersize=2.5, label=_r("Recovery", "Recovery"))
    if col_b in merged:
        ax.plot(merged["date"], merged[col_b], marker="o", markersize=2.5, label=_r("Reiezione normalizzata", "Normalised rejection"))
    ax.set_title(_r("Indicatori di processo RO", "RO process indicators"))
    ax.set_ylabel("%")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _report_fig_to_png(fig)


def _report_chart_motors(df_nas, config_attuale, metric):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    if df_nas is None or df_nas.empty:
        return None
    work = df_nas.copy()
    work["freq"] = pd.to_numeric(work.get("freq"), errors="coerce")
    work = work[work["freq"] > 10]
    if work.empty:
        return None
    if metric == "cosphi":
        work["value"] = pd.to_numeric(work.get("cosphi"), errors="coerce")
        title = _r("Andamento Cosφ dei motori", "Motor Cosφ trends")
        ylabel = "Cosφ"
    else:
        current = pd.to_numeric(work.get("current"), errors="coerce")
        work["value"] = current / work["freq"]
        title = _r("Andamento dello sforzo meccanico A/Hz", "Mechanical load A/Hz trends")
        ylabel = "A/Hz"
    work = work.dropna(subset=["_report_date", "value", "nas_id"])
    if work.empty:
        return None
    work["date"] = work["_report_date"].dt.normalize()
    daily = work.groupby(["date", "nas_id"], as_index=False)["value"].mean()

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    plotted = 0
    for nas_id, group in daily.groupby("nas_id"):
        if nas_id not in config_attuale.get("inverters", {}):
            continue
        ax.plot(group["date"], group["value"], marker="o", markersize=2, linewidth=1, label=tr_text(config_attuale["inverters"][nas_id]))
        plotted += 1
    if plotted == 0:
        plt.close(fig)
        return None
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6, ncol=2, loc="best")
    fig.tight_layout()
    return _report_fig_to_png(fig)

def _report_chart_water_quality(df, param, title_it, title_en, ylabel):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    df_param = df[df['Parametro'] == param].copy()
    if df_param.empty:
        return None
        
    df_param['date'] = df_param['_report_date'].dt.normalize()
    
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    punti = sorted(df_param['Punto'].unique())
    
    plotted = 0
    for p in punti:
        df_p = df_param[df_param['Punto'] == p].groupby('date', as_index=False)['Valore'].mean()
        if not df_p.empty:
            ax.plot(df_p['date'], df_p['Valore'], marker='o', markersize=2.5, linewidth=1.2, label=p)
            plotted += 1
            
    if plotted == 0:
        plt.close(fig)
        return None
        
    ax.set_title(_r(title_it, title_en))
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.grid(alpha=0.25)
    
    # Se ci sono molti punti di campionamento, spostiamo la legenda in basso
    if plotted <= 8:
        ax.legend(fontsize=6, ncol=4, loc="best")
    else:
        ax.legend(fontsize=5, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.2))
        fig.subplots_adjust(bottom=0.35)
        
    fig.tight_layout()
    return _report_fig_to_png(fig)

def verifica_dipendenze_report():
    """Restituisce l'elenco delle dipendenze mancanti per i report PDF."""
    mancanti = []
    try:
        import reportlab  # noqa: F401
    except ModuleNotFoundError:
        mancanti.append("reportlab")
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        mancanti.append("matplotlib")
    return mancanti

def genera_report_pdf(impianto_scelto, config_attuale, start_date, end_date, df_ro_raw, df_uf, df_nas, selected_sections, selected_series, include_notes=True):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, KeepTogether
    )
    from xml.sax.saxutils import escape

    # Font Unicode per accenti, simboli tecnici e lingua inglese/italiana.
    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    font_candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for regular_path, bold_path in font_candidates:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont("ReportRegular", regular_path))
                pdfmetrics.registerFont(TTFont("ReportBold", bold_path))
                regular_font, bold_font = "ReportRegular", "ReportBold"
                break
            except Exception:
                pass

    try:
        df_pdf, df_atm, _ = load_produzione_atm(impianto_scelto)
    except Exception:
        df_pdf, df_atm = pd.DataFrame(), pd.DataFrame()

    daily = _report_build_daily(df_pdf, df_atm, start_date, end_date)
    ro_all = calcola_metriche_derivate(df_ro_raw) if df_ro_raw is not None and not df_ro_raw.empty else pd.DataFrame()
    ro_period = _report_filter_period(ro_all, start_date, end_date)
    uf_period = _report_filter_period(df_uf, start_date, end_date)
    nas_period = _report_filter_period(df_nas, start_date, end_date)
    df_wq_all = load_water_quality_data(impianto_scelto)
    wq_period = _report_filter_period(df_wq_all, start_date, end_date, date_col="_report_date") if not df_wq_all.empty else pd.DataFrame()

    days = max(1, (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days + 1)
    def total(col):
        if col not in daily.columns or not daily[col].notna().any():
            return np.nan
        return pd.to_numeric(daily[col], errors="coerce").sum(min_count=1)

    total_prod = total("permeato")
    total_conc = total("concentrato")
    total_atm_l = total("atm_litri")
    total_atm = total_atm_l / 1000.0 if pd.notna(total_atm_l) else np.nan
    avg_prod = total_prod / days if pd.notna(total_prod) else np.nan
    avg_conc = total_conc / days if pd.notna(total_conc) else np.nan
    avg_atm = total_atm / days if pd.notna(total_atm) else np.nan
    balance = total_prod - total_atm if pd.notna(total_prod) and pd.notna(total_atm) else np.nan
    ratio = total_atm / total_prod * 100 if pd.notna(total_prod) and total_prod > 0 and pd.notna(total_atm) else np.nan

    buffer = io.BytesIO()
    plant_display = tr_text(impianto_scelto)[2:].strip()
    period_label = f"{pd.Timestamp(start_date).strftime('%d/%m/%Y')} - {pd.Timestamp(end_date).strftime('%d/%m/%Y')}"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.35 * cm,
        leftMargin=1.35 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.35 * cm,
        title=_r("Report operativo e manutentivo", "Operational and Maintenance Report"),
        author="Water Partners Fleet Management",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName=bold_font, fontSize=21, leading=25, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="ReportSubtitle", parent=styles["Normal"], fontName=regular_font, fontSize=10, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#475569"), spaceAfter=18))
    styles.add(ParagraphStyle(name="ReportH1", parent=styles["Heading1"], fontName=bold_font, fontSize=15, leading=18, textColor=colors.HexColor("#0F4C5C"), spaceBefore=7, spaceAfter=8))
    styles.add(ParagraphStyle(name="ReportH2", parent=styles["Heading2"], fontName=bold_font, fontSize=11.5, leading=14, textColor=colors.HexColor("#1F2937"), spaceBefore=5, spaceAfter=5))
    styles.add(ParagraphStyle(name="ReportBody", parent=styles["BodyText"], fontName=regular_font, fontSize=8.8, leading=12, spaceAfter=5))
    styles.add(ParagraphStyle(name="ReportSmall", parent=styles["BodyText"], fontName=regular_font, fontSize=7.2, leading=9))
    styles.add(ParagraphStyle(name="ReportMetric", parent=styles["BodyText"], fontName=bold_font, fontSize=11.5, leading=14, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="ReportMetricLabel", parent=styles["BodyText"], fontName=regular_font, fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#475569")))

    story = []
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(_r("REPORT OPERATIVO E MANUTENTIVO", "OPERATIONAL AND MAINTENANCE REPORT"), styles["ReportTitle"]))
    story.append(Paragraph(f"{escape(plant_display)}<br/>{_r('Periodo', 'Period')}: {period_label}<br/>{_r('Generato il', 'Generated on')}: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["ReportSubtitle"]))

    metric_data = [
        [Paragraph(_r("Totale prodotto", "Total production"), styles["ReportMetricLabel"]), Paragraph(_r("Totale venduto ATM", "Total ATM sales"), styles["ReportMetricLabel"]), Paragraph(_r("Totale concentrato", "Total concentrate"), styles["ReportMetricLabel"])],
        [Paragraph(_report_format_number(total_prod, "m³"), styles["ReportMetric"]), Paragraph(_report_format_number(total_atm, "m³"), styles["ReportMetric"]), Paragraph(_report_format_number(total_conc, "m³"), styles["ReportMetric"])],
        [Paragraph(_r("Media produzione", "Average production"), styles["ReportMetricLabel"]), Paragraph(_r("Media vendite ATM", "Average ATM sales"), styles["ReportMetricLabel"]), Paragraph(_r("Media concentrato", "Average concentrate"), styles["ReportMetricLabel"])],
        [Paragraph(_report_format_number(avg_prod, _r("m³/giorno", "m³/day")), styles["ReportMetric"]), Paragraph(_report_format_number(avg_atm, _r("m³/giorno", "m³/day")), styles["ReportMetric"]), Paragraph(_report_format_number(avg_conc, _r("m³/giorno", "m³/day")), styles["ReportMetric"])],
    ]
    metric_table = Table(metric_data, colWidths=[6.05 * cm] * 3, rowHeights=[0.55 * cm, 0.72 * cm, 0.55 * cm, 0.72 * cm])
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 0.35 * cm))

    secondary_rows = [
        [_r("Giorni nel periodo", "Days in period"), str(days)],
        [_r("Rapporto vendite ATM / produzione", "ATM sales / production ratio"), f"{ratio:.0f}%" if pd.notna(ratio) else _r("N/D", "N/A")],
        [_r("Differenza produzione - vendite ATM", "Production - ATM sales difference"), _report_format_number(balance, "m³")],
        [_r("Campioni RO", "RO samples"), f"{len(ro_period):,}"],
        [_r("Campioni UF", "UF samples"), f"{len(uf_period):,}"],
        [_r("Campioni inverter", "Inverter samples"), f"{len(nas_period):,}"],
    ]
    sec_table = Table(secondary_rows, colWidths=[9.6 * cm, 8.55 * cm])
    sec_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), regular_font),
        ("FONTNAME", (0, 0), (0, -1), bold_font),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF2F4")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sec_table)

    # Asset health summary and automatic observations.
    if not ro_period.empty:
        baseline_ro = ro_all.iloc[0]
        latest_ro = ro_period.iloc[-1]
        dp_report_col = "dp_ro_norm_smooth" if "dp_ro_norm_smooth" in ro_period.columns else "dp_ro_smooth"
        L_PERM_RO = float(baseline_ro.get("perm_norm_smooth", np.nan)) * 0.85
        L_DPRO = float(baseline_ro.get(dp_report_col, np.nan)) * 1.15
        L_DPCF01 = 1.0
        asset_rows = [[_r("Asset", "Asset"), _r("Valore attuale", "Current value"), _r("Health score", "Health score"), _r("Stima soglia", "Threshold estimate")]]
        assets = [
            (_r("Membrane RO", "RO membranes"), "perm_norm_smooth", L_PERM_RO, False, ""),
            (_r("Spaziatori RO (ΔP norm.)", "RO spacers (normalised ΔP)"), dp_report_col, L_DPRO, True, "bar"),
            (_r("Cartucce CF01", "CF01 cartridges"), "dp_cf01", L_DPCF01, True, "bar"),
        ]
        if config_attuale.get("has_bag_filters") and "pit007" in ro_period.columns:
            assets.append((_r("Filtri a calza", "Bag filters"), "pit007", 1.0, True, "bar"))
        for name, col, limit, is_max, unit in assets:
            if col not in ro_period.columns or col not in baseline_ro.index:
                continue
            current = pd.to_numeric(pd.Series([latest_ro.get(col)]), errors="coerce").iloc[0]
            base = pd.to_numeric(pd.Series([baseline_ro.get(col)]), errors="coerce").iloc[0]
            if pd.isna(current) or pd.isna(base) or pd.isna(limit):
                continue
            score = get_health_score(current, base, limit, is_max)
            days_left = stima_giorni_rimanenti(ro_period, col, limit, is_max)
            estimate = _r("Stabile", "Stable") if days_left == 999 else (f"{days_left} {_r('giorni', 'days')}" if days_left is not None else _r("Dati insufficienti", "Insufficient data"))
            asset_rows.append([name, f"{current:.2f} {unit}".strip(), f"{score:.0f}%", estimate])

        if config_attuale.get("has_uf") and not uf_period.empty and "uftmp" in uf_period.columns:
            uf_base = pd.to_numeric(pd.Series([df_uf.iloc[0].get("uftmp")]), errors="coerce").iloc[0]
            uf_current = pd.to_numeric(pd.Series([uf_period.iloc[-1].get("uftmp")]), errors="coerce").iloc[0]
            if pd.notna(uf_base) and pd.notna(uf_current) and uf_base != 0:
                score = get_health_score(uf_current, uf_base, 1.5, True)
                days_left = stima_giorni_rimanenti(uf_period, "uftmp", 1.5, True)
                estimate = _r("Stabile", "Stable") if days_left == 999 else (f"{days_left} {_r('giorni', 'days')}" if days_left is not None else _r("Dati insufficienti", "Insufficient data"))
                asset_rows.append([_r("Membrane UF", "UF membranes"), f"{uf_current:.2f} bar", f"{score:.0f}%", estimate])

        if len(asset_rows) > 1:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(_r("Sintesi dello stato degli asset", "Asset condition summary"), styles["ReportH1"]))
            asset_table = Table(asset_rows, repeatRows=1, colWidths=[6.2 * cm, 4.0 * cm, 3.4 * cm, 4.55 * cm])
            asset_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), regular_font),
                ("FONTSIZE", (0, 0), (-1, -1), 7.7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C5C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(asset_table)

    if include_notes:
        observations = []
        if pd.notna(ratio):
            observations.append(_r(
                f"Nel periodo le vendite ATM equivalgono al {ratio:.0f}% della produzione registrata. Il rapporto non rappresenta automaticamente una perdita, perché può risentire di accumuli, altri consumi e differenze temporali.",
                f"During the period, ATM sales equal {ratio:.0f}% of recorded production. This ratio does not automatically represent a loss, as it may reflect storage, other uses and timing differences."
            ))
        if len(daily) > 0:
            days_prod = int(daily["permeato"].notna().sum())
            days_atm = int(daily["atm_litri"].notna().sum())
            observations.append(_r(
                f"Copertura dati: produzione disponibile per {days_prod} giorni e ATM per {days_atm} giorni su {days}.",
                f"Data coverage: production is available for {days_prod} days and ATM sales for {days_atm} days out of {days}."
            ))
        if observations:
            story.append(Spacer(1, 0.25 * cm))
            story.append(Paragraph(_r("Osservazioni automatiche", "Automatic observations"), styles["ReportH1"]))
            for item in observations:
                story.append(Paragraph(f"- {escape(item)}", styles["ReportBody"]))

    # Production and sales section.
    if "Produzione e vendite" in selected_sections:
        story.append(PageBreak())
        story.append(Paragraph(_r("Produzione, concentrato e vendite ATM", "Production, concentrate and ATM sales"), styles["ReportH1"]))
        production_chart = _report_chart_daily_volumes(daily, selected_series)
        if production_chart is not None:
            story.append(Image(production_chart, width=18.1 * cm, height=8.15 * cm))
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(_r(
            "Le medie sono calcolate sui giorni di calendario compresi nel periodo selezionato. La differenza tra produzione e vendite ATM può includere variazioni di livello dei serbatoi, altri utilizzi e sfasamenti temporali.",
            "Averages are calculated over the calendar days in the selected period. The difference between production and ATM sales may include tank-level changes, other uses and timing offsets."
        ), styles["ReportSmall"]))

    # RO predictive charts.
    if "Performance RO" in selected_sections and not ro_period.empty:
        story.append(PageBreak())
        story.append(Paragraph(_r("Andamento e previsione degli asset RO", "RO asset trends and forecasts"), styles["ReportH1"]))
        baseline_ro = ro_all.iloc[0]
        dp_report_col = "dp_ro_norm_smooth" if "dp_ro_norm_smooth" in ro_period.columns else "dp_ro_smooth"
        charts = []
        charts.append(_report_chart_health_index(ro_all, start_date, end_date))
        charts.append(_report_chart_trend(ro_period, "perm_norm_smooth", "Permeabilità normalizzata delle membrane RO", "RO membrane normalised permeability", "Permeabilità normalizzata", "Normalised permeability", limit=float(baseline_ro.get("perm_norm_smooth", np.nan)) * 0.85, forecast_days=30, direction="down"))
        charts.append(_report_chart_trend(ro_period, dp_report_col, "Salto di pressione normalizzato delle membrane RO", "RO membrane normalised pressure drop", "ΔP normalizzato (bar)", "Normalised ΔP (bar)", limit=float(baseline_ro.get(dp_report_col, np.nan)) * 1.15, baseline=float(baseline_ro.get(dp_report_col, np.nan)), forecast_days=30, direction="up"))
        charts.append(_report_chart_trend(ro_period, "dp_cf01", "Intasamento delle cartucce CF01", "CF01 cartridge clogging", "ΔP (bar)", "ΔP (bar)", limit=1.0, baseline=float(baseline_ro.get("dp_cf01", np.nan)), forecast_days=20, direction="up"))
        charts.append(_report_chart_two_percent(ro_period, "recovery", "sr_norm"))
        if config_attuale.get("has_sec") and "sec" in ro_period.columns:
            charts.append(_report_chart_trend(ro_period, "sec", "Consumo specifico di energia", "Specific energy consumption", "SEC (kWh/m³)", "SEC (kWh/m³)"))
        for chart in [c for c in charts if c is not None]:
            story.append(Image(chart, width=18.1 * cm, height=7.65 * cm))
            story.append(Spacer(1, 0.2 * cm))

    # UF / bag filters.
    if "UF e filtri" in selected_sections:
        filter_charts = []
        if config_attuale.get("has_uf") and not uf_period.empty:
            filter_charts.append(_report_chart_trend(uf_period, "uftmp", "TMP delle membrane UF", "UF membrane TMP", "TMP (bar)", "TMP (bar)", limit=1.5, baseline=float(df_uf.iloc[0].get("uftmp", np.nan)), forecast_days=30, direction="up"))
            filter_charts.append(_report_chart_trend(uf_period, "dpscf", "Salto di pressione del filtro UF", "UF filter pressure drop", "ΔP (bar)", "ΔP (bar)"))
        if config_attuale.get("has_bag_filters") and not ro_period.empty and "pit007" in ro_period.columns:
            filter_charts.append(_report_chart_trend(ro_period, "pit007", "Intasamento dei filtri a calza", "Bag-filter clogging", "ΔP (bar)", "ΔP (bar)", limit=1.0, baseline=float(ro_all.iloc[0].get("pit007", np.nan)), forecast_days=20, direction="up"))
        filter_charts = [c for c in filter_charts if c is not None]
        if filter_charts:
            story.append(PageBreak())
            story.append(Paragraph(_r("Ultrafiltrazione e filtri", "Ultrafiltration and filters"), styles["ReportH1"]))
            for chart in filter_charts:
                story.append(Image(chart, width=18.1 * cm, height=7.65 * cm))
                story.append(Spacer(1, 0.2 * cm))

    # Motor diagnostics.
    if "Motori e pompe" in selected_sections and not nas_period.empty:
        story.append(PageBreak())
        story.append(Paragraph(_r("Diagnostica di motori e pompe", "Motor and pump diagnostics"), styles["ReportH1"]))
        motor_stats = _report_motor_stats(nas_period, config_attuale, impianto_scelto)
        if not motor_stats.empty:
            headers = list(motor_stats.columns)
            motor_rows = [headers]
            for _, row in motor_stats.iterrows():
                motor_rows.append([
                    str(row["ID"]),
                    str(row[_r("Pompa", "Pump")]),
                    f"{row[_r('Deriva Cosφ', 'Cosφ drift')]:+.1f}%",
                    str(row[_r("Stato elettrico", "Electrical status")]),
                    f"{row[_r('Deriva A/Hz', 'A/Hz drift')]:+.1f}%",
                    str(row[_r("Stato meccanico", "Mechanical status")]),
                ])
            motor_table = Table(motor_rows, repeatRows=1, colWidths=[1.25 * cm, 5.0 * cm, 2.5 * cm, 3.0 * cm, 2.5 * cm, 3.5 * cm])
            motor_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), regular_font),
                ("FONTSIZE", (0, 0), (-1, -1), 6.7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C5C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(motor_table)
            story.append(Spacer(1, 0.25 * cm))
        for metric in ("cosphi", "ahz"):
            chart = _report_chart_motors(nas_period, config_attuale, metric)
            if chart is not None:
                story.append(Image(chart, width=18.1 * cm, height=8.0 * cm))
                story.append(Spacer(1, 0.2 * cm))

    # Sezione: Qualità Acqua Manuale
    if "Qualità Acqua" in selected_sections and not wq_period.empty:
        story.append(PageBreak())
        story.append(Paragraph(_r("Andamento Qualità Acqua (Manuale)", "Water Quality Trends (Manual)"), styles["ReportH1"]))
        
        param_configs = [
            ('cl', "Trend Cloro Residuo", "Chlorine Trend", "Cloro (mg/l)"),
            ('cond', "Trend Conduttività", "Conductivity Trend", "Conduttività (µS/cm)"),
            ('temp', "Trend Temperatura", "Temperature Trend", "Temperatura (°C)"),
            ('ph', "Trend pH", "pH Trend", "pH")
        ]
        
        for param, title_it, title_en, ylabel in param_configs:
            chart = _report_chart_water_quality(wq_period, param, title_it, title_en, ylabel)
            if chart is not None:
                story.append(Image(chart, width=18.1 * cm, height=8.0 * cm))
                story.append(Spacer(1, 0.2 * cm))

    if "Tabella giornaliera" in selected_sections:
        story.append(PageBreak())
        story.append(Paragraph(_r("Dettaglio giornaliero", "Daily detail"), styles["ReportH1"]))
        daily_rows = [[_r("Data", "Date"), _r("Produzione (m³)", "Production (m³)"), _r("Vendite ATM (m³)", "ATM sales (m³)"), _r("Concentrato (m³)", "Concentrate (m³)")]]
        for _, row in daily.iterrows():
            daily_rows.append([
                pd.Timestamp(row["data_rif"]).strftime("%d/%m/%Y"),
                "" if pd.isna(row["permeato"]) else f"{row['permeato']:.0f}",
                "" if pd.isna(row["atm_m3"]) else f"{row['atm_m3']:.0f}",
                "" if pd.isna(row["concentrato"]) else f"{row['concentrato']:.0f}",
            ])
        daily_table = Table(daily_rows, repeatRows=1, colWidths=[4.1 * cm, 4.7 * cm, 4.7 * cm, 4.7 * cm])
        daily_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), regular_font),
            ("FONTSIZE", (0, 0), (-1, -1), 7.4),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C5C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(daily_table)

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(_r(
        "Nota: le stime predittive sono indicatori di supporto e devono essere confermate con verifica tecnica, qualità del dato e condizioni operative dell'impianto.",
        "Note: predictive estimates are decision-support indicators and should be confirmed through technical inspection, data quality checks and the plant's operating conditions."
    ), styles["ReportSmall"]))

    def header_footer(canvas, document):
        canvas.saveState()
        canvas.setFont(regular_font, 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(document.leftMargin, 0.72 * cm, f"Water Partners Fleet Management - {plant_display}")
        canvas.drawRightString(A4[0] - document.rightMargin, 0.72 * cm, f"{_r('Pagina', 'Page')} {canvas.getPageNumber()}")
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(document.leftMargin, 1.0 * cm, A4[0] - document.rightMargin, 1.0 * cm)
        canvas.restoreState()

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    buffer.seek(0)
    return buffer.getvalue()


def render_report(impianto_scelto, config_attuale, df_ro_raw, df_uf, df_nas):
    st.header("📄 Generazione Report")
    st.caption("Il report usa la lingua attualmente selezionata nella dashboard.")

    dipendenze_mancanti = verifica_dipendenze_report()
    if dipendenze_mancanti:
        elenco = ", ".join(dipendenze_mancanti)
        st.error(
            _r(
                f"Impossibile generare il PDF: mancano i pacchetti {elenco}. "
                "Aggiungi il file requirements.txt alla cartella principale del progetto "
                "e riavvia o ridistribuisci l'app.",
                f"PDF generation is unavailable because these packages are missing: {elenco}. "
                "Add requirements.txt to the project root and restart or redeploy the app."
            )
        )
        st.code("reportlab>=4.0,<5\nmatplotlib>=3.8,<4", language="text")
        return

    # Recupera le date disponibili da tutte le sorgenti per proporre un periodo sensato.
    all_dates = []
    for frame in (df_ro_raw, df_uf, df_nas):
        if frame is None or frame.empty:
            continue
        if "date_str" in frame.columns:
            all_dates.extend(pd.to_datetime(frame["date_str"], errors="coerce").dropna().tolist())
        elif "timestamp" in frame.columns:
            all_dates.extend(pd.to_datetime(pd.to_numeric(frame["timestamp"], errors="coerce"), unit="s", errors="coerce").dropna().tolist())
    try:
        df_pdf, df_atm, _ = load_produzione_atm(impianto_scelto)
        if not df_pdf.empty:
            all_dates.extend(pd.to_datetime(df_pdf["data_rif"], errors="coerce").dropna().tolist())
        if not df_atm.empty:
            all_dates.extend(pd.to_datetime(df_atm["data_rif"], errors="coerce").dropna().tolist())
    except Exception:
        pass

    if not all_dates:
        st.info("Nessun dato disponibile per generare il report.")
        return

    min_date = pd.Timestamp(min(all_dates)).normalize()
    max_date = pd.Timestamp(max(all_dates)).normalize()
    default_start = max(min_date, max_date.to_period("M").start_time.normalize())

    period = st.date_input(
        "Periodo del report:",
        value=[default_start.date(), max_date.date()],
        min_value=min_date.date(),
        max_value=max_date.date(),
        key="report_date_range",
    )

    available_series = ["Produzione", "Vendite ATM", "Concentrato"]
    selected_series = st.multiselect(
        "Serie del grafico produzione:",
        options=available_series,
        default=["Produzione", "Vendite ATM"],
        help="Il concentrato non è incluso di default nel grafico del report.",
        key="report_volume_series",
    )

    available_sections = ["Produzione e vendite", "Performance RO"]
    if config_attuale.get("has_uf") or config_attuale.get("has_bag_filters"):
        available_sections.append("UF e filtri")
    available_sections.append("Motori e pompe")

    if "Kaktus" in impianto_scelto:
        available_sections.append("Qualità Acqua")

    available_sections.append("Tabella giornaliera")
    default_sections = [section for section in ["Produzione e vendite", "Performance RO", "UF e filtri", "Motori e pompe"] if section in available_sections]
    selected_sections = st.multiselect(
        "Sezioni da includere:",
        options=available_sections,
        default=default_sections,
        key="report_sections",
    )
    include_notes = st.checkbox(
        "Includi note automatiche e indicatori di qualità del dato",
        value=True,
        key="report_include_notes",
    )

    valid_period = isinstance(period, (list, tuple)) and len(period) == 2 and period[0] <= period[1]
    if not valid_period:
        st.warning("Seleziona una data iniziale e una data finale valide.")
        return

    start_date, end_date = pd.Timestamp(period[0]), pd.Timestamp(period[1])
    report_key = f"generated_report_{re.sub(r'[^A-Za-z0-9]+', '_', impianto_scelto)}"

    if st.button("Genera report PDF", type="primary", key="generate_pdf_report"):
        try:
            with _RAW_ST.spinner(tr_text("Generazione del report in corso...")):
                pdf_bytes = genera_report_pdf(
                    impianto_scelto=impianto_scelto,
                    config_attuale=config_attuale,
                    start_date=start_date,
                    end_date=end_date,
                    df_ro_raw=df_ro_raw,
                    df_uf=df_uf,
                    df_nas=df_nas,
                    selected_sections=selected_sections,
                    selected_series=selected_series,
                    include_notes=include_notes,
                )
            _RAW_ST.session_state[report_key] = pdf_bytes
            _RAW_ST.session_state[f"{report_key}_filename"] = (
                f"report_{'en' if UI_LANGUAGE == 'en' else 'it'}_"
                f"{re.sub(r'[^A-Za-z0-9]+', '_', impianto_scelto[2:]).strip('_')}_"
                f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
            )
            st.success("Report generato correttamente.")
        except Exception as exc:
            st.error(f"{_r('Errore nella generazione del report', 'Report generation error')}: {exc}")

    if report_key in _RAW_ST.session_state:
        st.download_button(
            "Scarica report PDF",
            data=_RAW_ST.session_state[report_key],
            file_name=_RAW_ST.session_state.get(f"{report_key}_filename", "report.pdf"),
            mime="application/pdf",
            key="download_generated_pdf_report",
        )

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

def valuta_parametro_who(valore, parametro, impianto_scelto="", punto=""):
    """Valuta il parametro chimico-fisico rispetto alle soglie operative configurate per impianto e punto."""
    if pd.isna(valore):
        return "⚪", "N/D", "normal"
        
    is_pingwe = "Pingwe" in impianto_scelto
    is_pozzo = is_pingwe and punto in ["BH 1", "BH 2"]
    is_ro = is_pingwe and punto == "RO"
        
    if parametro == "pH":
        if is_pingwe:
            if 6.5 <= valore <= 8.5: return "🟢", "Ottimale", "normal"
            elif 5.0 <= valore < 6.5 or 8.5 < valore <= 9.0: return "🟡", "Attenzione", "off"
            else: return "🔴", "Critico", "inverse"
        else: # Kaktus
            if 6.0 <= valore <= 8.5: return "🟢", "Ottimale", "normal"
            elif 5.5 <= valore < 6.0 or 8.5 < valore <= 9.0: return "🟡", "Attenzione", "off"
            else: return "🔴", "Critico", "inverse"
        
    elif parametro == "Cloro":
        if is_pingwe:
            if is_pozzo or is_ro:
                if valore <= 0.1: return "🟢", "Ottimale", "normal"
                elif 0.1 < valore <= 0.2: return "🟡", "Attenzione", "off"
                else: return "🔴", "Critico", "inverse"
            else: # Standard Potabile Pingwe
                if 0.2 <= valore <= 0.55: return "🟢", "Ottimale", "normal"
                elif 0.1 <= valore < 0.2 or 0.55 < valore <= 1.0: return "🟡", "Attenzione", "off"
                else: return "🔴", "Critico", "inverse"
        else: # Kaktus
            if 0.2 <= valore <= 1.0: return "🟢", "Ottimale", "normal"
            elif 0.1 <= valore < 0.2 or 1.0 < valore <= 2.0: return "🟡", "Attenzione", "off"
            else: return "🔴", "Critico", "inverse"
        
    elif parametro == "Conducibilità":
        if is_pingwe and is_pozzo:
            if 1500 <= valore <= 7500: return "🟢", "Ottimale", "normal"
            elif valore < 1500: return "🟡", "Attenzione", "off"
            else: return "🔴", "Critico", "inverse"
        else: # Kaktus, Pingwe RO, Pingwe Potabile
            if valore <= 500: return "🟢", "Ottimale", "normal"
            elif 500 < valore <= 1000: return "🟡", "Attenzione", "off"
            else: return "🔴", "Critico", "inverse"
            
    return "⚪", "", "normal"

def render_qualita_acqua(impianto_scelto):
    st.header("💧 Qualità Acqua e Soglie Operative (Manuale)")
    
    nome_impianto = "kaktus" if "Kaktus" in impianto_scelto else "pingwe"
    tabella_db = f"misurazioni_{nome_impianto}"
    
    try:
        from supabase import create_client
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        res = supabase.table(tabella_db).select("*").order("data_rilievo", desc=True).execute()
        df_acqua = pd.DataFrame(res.data)
        
    except Exception as e:
        if "pingwe" in nome_impianto:
            st.info("Il modulo Qualità Acqua non è ancora stato attivato o configurato nel database per questo impianto.")
            return
        st.error(f"Errore durante il caricamento dei dati da Supabase: {e}")
        return

    if df_acqua.empty:
        st.info(f"Nessun dato di qualità dell'acqua trovato per l'impianto {impianto_scelto}.")
        return

    storico_dati = []
    for _, row in df_acqua.iterrows():
        data_val = row.get('data_rilievo')
        dati_json = row.get('dati_tabella')
        if pd.notna(data_val) and dati_json:
            for punto, valori in dati_json.items():
                for param, val in valori.items():
                    storico_dati.append({
                        'Data': pd.to_datetime(data_val),
                        'Punto': punto,
                        'Parametro_Raw': param,
                        'Valore': val
                    })

    df_storico = pd.DataFrame(storico_dati)
    if df_storico.empty:
        st.warning("I report caricati non contengono dati numerici validi.")
        return

    mappa_parametri = {
        'cl': 'Cloro',
        'cond': 'Conducibilità',
        'temp': 'Temperatura',
        'ph': 'pH'
    }
    df_storico['Parametro'] = df_storico['Parametro_Raw'].map(mappa_parametri).fillna(df_storico['Parametro_Raw'])
    tutti_punti = sorted(df_storico['Punto'].unique())

    # ==========================================
    # 1. CRUSCOTTO WHO (AT-A-GLANCE)
    # ==========================================
    st.subheader("Cruscotto Attuale (Ultimo Campionamento)")
    
    default_dash = "ATM" if "ATM" in tutti_punti else tutti_punti[0]
    punto_cruscotto = st.selectbox("📍 Seleziona il punto di prelievo per il cruscotto:", tutti_punti, index=tutti_punti.index(default_dash) if default_dash in tutti_punti else 0)
    
    ultima_data = df_storico['Data'].max()
    df_ultimo_punto = df_storico[(df_storico['Data'] == ultima_data) & (df_storico['Punto'] == punto_cruscotto)]
    valori_attuali = df_ultimo_punto.set_index('Parametro')['Valore'].to_dict()
    
    c1, c2, c3 = st.columns(3)
    
    val_ph = valori_attuali.get('pH', np.nan)
    icona_ph, stato_ph, delta_ph = valuta_parametro_who(val_ph, "pH", impianto_scelto, punto_cruscotto)
    with c1: 
        st.metric(label=f"pH ({punto_cruscotto}) {icona_ph}", value=f"{val_ph:.2f}" if pd.notna(val_ph) else "N/D", delta=stato_ph, delta_color=delta_ph)
        
    val_cl = valori_attuali.get('Cloro', np.nan)
    icona_cl, stato_cl, delta_cl = valuta_parametro_who(val_cl, "Cloro", impianto_scelto, punto_cruscotto)
    with c2: 
        st.metric(label=f"Cloro ({punto_cruscotto}) {icona_cl}", value=f"{val_cl:.2f} mg/L" if pd.notna(val_cl) else "N/D", delta=stato_cl, delta_color=delta_cl)
        
    val_cond = valori_attuali.get('Conducibilità', np.nan)
    icona_cond, stato_cond, delta_cond = valuta_parametro_who(val_cond, "Conducibilità", impianto_scelto, punto_cruscotto)
    with c3: 
        st.metric(label=f"Cond. ({punto_cruscotto}) {icona_cond}", value=f"{val_cond:.0f} µS/cm" if pd.notna(val_cond) else "N/D", delta=stato_cond, delta_color=delta_cond)
        
    st.caption(f"Valori riferiti all'ultimo campionamento del: **{ultima_data.strftime('%d/%m/%Y')}**")
    st.markdown("---")

    # ==========================================
    # 2. GRAFICI DI TREND CON FASCE DINAMICHE
    # ==========================================
    st.subheader("📈 Trend Storico e Soglie Operative")
    
    col_param, col_punti = st.columns(2)
    with col_param:
        parametri_qualita = ['pH', 'Cloro', 'Conducibilità', 'Temperatura']
        param_selezionato = st.selectbox(
            "Seleziona il parametro da analizzare:",
            parametri_qualita,
            index=parametri_qualita.index('Cloro'),
            key="water_quality_parameter",
        )
    with col_punti:
        punti_atm_default = [
            punto for punto in tutti_punti
            if re.sub(r'[^A-Za-z0-9]+', '', str(punto)).upper() in {'ATM1', 'ATM2', 'ATM'}
        ]
        default_punti = punti_atm_default or (["Tk11"] if "Tk11" in tutti_punti else [tutti_punti[0]])
        punti_selezionati = st.multiselect(
            "Seleziona i punti di campionamento:",
            tutti_punti,
            default=default_punti,
            key="water_quality_sampling_points",
        )

    df_plot = df_storico[(df_storico['Parametro'] == param_selezionato) & (df_storico['Punto'].isin(punti_selezionati))]

    if not df_plot.empty:
        df_plot = df_plot.sort_values('Data')
        fig = px.line(df_plot, x='Data', y='Valore', color='Punto', markers=True, title=f"Andamento {param_selezionato} rispetto alle soglie operative")
        
        punto_rif = punti_selezionati[0] if len(punti_selezionati) > 0 else ""
        is_pingwe = "Pingwe" in impianto_scelto
        is_pozzo = is_pingwe and punto_rif in ["BH 1", "BH 2"]
        is_ro = is_pingwe and punto_rif == "RO"

        if param_selezionato == 'pH':
            if is_pingwe:
                fig.add_hrect(y0=6.5, y1=8.5, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Ottimale")
                fig.add_hrect(y0=5.0, y1=6.5, line_width=0, fillcolor="orange", opacity=0.1, annotation_text="Attenzione")
                fig.add_hrect(y0=8.5, y1=9.0, line_width=0, fillcolor="orange", opacity=0.1)
                fig.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="Critico Minimo")
                fig.add_hline(y=9.0, line_dash="dash", line_color="red", annotation_text="Critico Massimo")
                fig.update_yaxes(range=[4.0, 10.0])
            else: # Kaktus
                fig.add_hrect(y0=6.0, y1=8.5, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Regolare")
                fig.add_hrect(y0=5.5, y1=6.0, line_width=0, fillcolor="orange", opacity=0.1, annotation_text="Attenzione")
                fig.add_hrect(y0=8.5, y1=9.0, line_width=0, fillcolor="orange", opacity=0.1)
                fig.add_hline(y=5.5, line_dash="dash", line_color="red", annotation_text="Critico Minimo")
                fig.add_hline(y=9.0, line_dash="dash", line_color="red", annotation_text="Critico Massimo")
                fig.update_yaxes(range=[4.0, 10.0])
            
        elif param_selezionato == 'Cloro':
            if is_pingwe:
                if is_pozzo or is_ro:
                    fig.add_hrect(y0=0, y1=0.1, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Ottimale")
                    fig.add_hrect(y0=0.1, y1=0.2, line_width=0, fillcolor="orange", opacity=0.1, annotation_text="Attenzione")
                    fig.add_hline(y=0.2, line_dash="dash", line_color="red", annotation_text="Critico Massimo")
                else: # Standard Potabile Pingwe
                    fig.add_hrect(y0=0.2, y1=0.55, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Ottimale")
                    fig.add_hrect(y0=0.1, y1=0.2, line_width=0, fillcolor="orange", opacity=0.1, annotation_text="Attenzione")
                    fig.add_hrect(y0=0.55, y1=1.0, line_width=0, fillcolor="orange", opacity=0.1)
                    fig.add_hline(y=0.1, line_dash="dash", line_color="red", annotation_text="Sottodosaggio")
                    fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Sovradosaggio")
            else: # Kaktus
                fig.add_hrect(y0=0.2, y1=1.0, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Ottimale")
                fig.add_hline(y=0.1, line_dash="dash", line_color="orange", annotation_text="Sottodosaggio")
                fig.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="Sovradosaggio")
            
        elif param_selezionato == 'Conducibilità':
            if is_pingwe and is_pozzo:
                fig.add_hrect(y0=1500, y1=7500, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Ottimale (TDS atteso)")
                fig.add_hrect(y0=0, y1=1500, line_width=0, fillcolor="orange", opacity=0.1, annotation_text="Attenzione (Acqua dolce)")
                fig.add_hline(y=7500, line_dash="dash", line_color="red", annotation_text="Critico (Elevata Salinità)")
            else: # Kaktus, Pingwe RO, Pingwe Potabile
                fig.add_hrect(y0=0, y1=500, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Ottimale")
                fig.add_hrect(y0=500, y1=1000, line_width=0, fillcolor="orange", opacity=0.1, annotation_text="Accettabile")
                fig.add_hline(y=1000, line_dash="dash", line_color="red", annotation_text="Limite WHO")

        fig.update_layout(xaxis_title="Data", yaxis_title=param_selezionato, hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Le fasce di tolleranza visive sono calibrate sulle soglie operative del punto: **{punto_rif}**.")
    else:
        st.info("Nessun dato disponibile per questa combinazione di parametri e punti di prelievo.")

    st.markdown("---")

    # ==========================================
    # 3. DETTAGLIO REPORT MANUALE 
    # ==========================================
    st.subheader("Dettaglio Misurazione e Firma Operatore")
    
    opzioni = df_acqua.apply(lambda x: f"{x['data_rilievo']} - {x['operatore']} ({x['strumento']})", axis=1).tolist()
    scelta = st.selectbox("Seleziona un inserimento manuale storico:", range(len(opzioni)), format_func=lambda i: opzioni[i])

    record = df_acqua.iloc[scelta]
    col1, col2 = st.columns([2, 1])

    with col1:
        dati_tabella = record['dati_tabella']
        if dati_tabella:
            parsed_data = []
            for punto, valori in dati_tabella.items():
                riga = {"Punto": punto}
                if 'cl' in valori: riga['Cl. (mg/l)'] = valori['cl']
                if 'cond' in valori: riga['Cond. (us)'] = valori['cond']
                if 'temp' in valori: riga['°C'] = valori['temp']
                if 'ph' in valori: riga['PH'] = valori['ph']
                parsed_data.append(riga)
            
            df_dettaglio = pd.DataFrame(parsed_data)
            st.dataframe(df_dettaglio, use_container_width=True, hide_index=True)
        else:
            st.warning("Nessun valore registrato in questa tabella.")

    with col2:
        firma = record['firma_operatore']
        if firma and str(firma).startswith('data:image'):
            st.image(firma, caption=f"Firma di {record['operatore']}", use_container_width=True)
        else:
            st.info("Nessuna firma disponibile.")


def _latest_telemetry_timestamp(*frames):
    latest_values = []
    for frame in frames:
        if frame is None or frame.empty:
            continue
        if 'date_str' in frame.columns:
            dates = pd.to_datetime(frame['date_str'], errors='coerce', utc=True).dropna()
        elif 'timestamp' in frame.columns:
            dates = pd.to_datetime(pd.to_numeric(frame['timestamp'], errors='coerce'), unit='s', errors='coerce', utc=True).dropna()
        else:
            continue
        if not dates.empty:
            latest_values.append(dates.max())
    return max(latest_values) if latest_values else pd.NaT


def _telemetry_age_hours(timestamp):
    if pd.isna(timestamp):
        return np.inf
    return max(0.0, (pd.Timestamp.now(tz='UTC') - timestamp).total_seconds() / 3600.0)


def _motor_health_summary(df_nas, config_attuale, impianto_scelto):
    result = {'level': 'unknown', 'checked': 0, 'warning_count': 0, 'critical_count': 0, 'messages': []}
    required = {'nas_id', 'freq', 'current', 'cosphi'}
    if df_nas is None or df_nas.empty or not required.issubset(df_nas.columns):
        return result

    install_dates = PUMP_INSTALL_DATES.get(impianto_scelto, {})
    for nas_id, pump_name in config_attuale.get('inverters', {}).items():
        pump_data = df_nas[df_nas['nas_id'] == nas_id].copy()
        if nas_id in install_dates:
            install_date = pd.to_datetime(install_dates[nas_id], errors='coerce')
            if pd.notna(install_date):
                pump_data = pump_data[pd.to_datetime(pump_data['date_str'], errors='coerce') >= install_date]

        pump_data['freq_num'] = pd.to_numeric(pump_data['freq'], errors='coerce')
        pump_data['current_num'] = pd.to_numeric(pump_data['current'], errors='coerce')
        pump_data['cosphi_num'] = pd.to_numeric(pump_data['cosphi'], errors='coerce')
        pump_data = pump_data[
            (pump_data['freq_num'] > 10)
            & pump_data['current_num'].notna()
            & pump_data['cosphi_num'].notna()
        ]
        if len(pump_data) < 3:
            continue

        torque_index = pump_data['current_num'] / pump_data['freq_num']
        base_idx, latest_idx = torque_index.iloc[:3].mean(), torque_index.iloc[-3:].mean()
        base_cos, latest_cos = pump_data['cosphi_num'].iloc[:3].mean(), pump_data['cosphi_num'].iloc[-3:].mean()
        if not all(np.isfinite(value) and value > 0 for value in [base_idx, latest_idx, base_cos, latest_cos]):
            continue

        result['checked'] += 1
        mechanical_drift = (latest_idx - base_idx) / base_idx * 100.0
        electrical_drift = (latest_cos - base_cos) / base_cos * 100.0
        is_critical = mechanical_drift > 15.0 or electrical_drift < -10.0
        is_warning = mechanical_drift > 8.0 or electrical_drift < -5.0

        if is_critical:
            result['critical_count'] += 1
            result['messages'].append(ui_text(
                f"{pump_name}: deriva critica (A/Hz {mechanical_drift:+.1f}%, Cosφ {electrical_drift:+.1f}%).",
                f"{pump_name}: critical drift (A/Hz {mechanical_drift:+.1f}%, power factor {electrical_drift:+.1f}%)."
            ))
        elif is_warning:
            result['warning_count'] += 1
            result['messages'].append(ui_text(
                f"{pump_name}: attenzione (A/Hz {mechanical_drift:+.1f}%, Cosφ {electrical_drift:+.1f}%).",
                f"{pump_name}: warning (A/Hz {mechanical_drift:+.1f}%, power factor {electrical_drift:+.1f}%)."
            ))

    if result['critical_count']:
        result['level'] = 'critical'
    elif result['warning_count']:
        result['level'] = 'warning'
    elif result['checked']:
        result['level'] = 'ok'
    return result


def _water_quality_summary(impianto_scelto):
    quality = load_water_quality_data(impianto_scelto)
    result = {'level': 'unknown', 'date': pd.NaT, 'checked': 0, 'messages': []}
    required = {'_report_date', 'Punto', 'Parametro', 'Valore'}
    if quality is None or quality.empty or not required.issubset(quality.columns):
        return result

    quality = quality.copy()
    quality['_report_date'] = pd.to_datetime(quality['_report_date'], errors='coerce')
    quality['Valore'] = pd.to_numeric(quality['Valore'], errors='coerce')
    quality = quality.dropna(subset=['_report_date', 'Valore'])
    if quality.empty:
        return result

    result['date'] = quality['_report_date'].max()
    latest = quality[quality['_report_date'] == result['date']]
    parameter_map = {
        'ph': ('pH', ''),
        'cl': ('Cloro', 'mg/L'),
        'cond': ('Conducibilità', 'µS/cm'),
    }
    worst_level = 'ok'
    for _, row in latest.iterrows():
        raw_parameter = str(row['Parametro']).strip().lower()
        if raw_parameter not in parameter_map:
            continue
        parameter, unit = parameter_map[raw_parameter]
        value = float(row['Valore'])
        punto = str(row['Punto'])
        
        # ORA PASSIAMO IMPIANTO E PUNTO PER DISINNESCARE I FALSI ALLARMI
        _, status, _ = valuta_parametro_who(value, parameter, impianto_scelto, punto)
        
        result['checked'] += 1
        if status == 'Critico':
            worst_level = 'critical'
        elif status == 'Attenzione' and worst_level != 'critical':
            worst_level = 'warning'
        else:
            continue
            
        formatted_value = f"{value:.2f}" if parameter != 'Conducibilità' else f"{value:.0f}"
        result['messages'].append(ui_text(
            f"{punto} – {parameter}: {formatted_value} {unit} ({status.lower()}).",
            f"{punto} – {parameter}: {formatted_value} {unit} ({'critical' if status == 'Critico' else 'warning'})."
        ))

    if result['checked']:
        result['level'] = worst_level
    return result


def _plant_overview_summary(impianto_scelto):
    config_attuale = CONFIG_IMPIANTI[impianto_scelto]
    df_ro_raw, df_uf, df_nas, source_msg = load_data(impianto_scelto)
    result = {
        'plant': impianto_scelto,
        'config': config_attuale,
        'source': source_msg,
        'warnings': [],
        'overall_level': 'unknown',
        'telemetry_level': 'unknown',
        'cip_level': 'unknown',
        'motor_level': 'unknown',
        'quality_level': 'unknown',
        # La freschezza della flotta è riferita alla telemetria di processo RO:
        # un pacchetto NAS recente non deve mascherare una RO ferma/offline.
        'latest_timestamp': _latest_telemetry_timestamp(df_ro_raw),
        'age_hours': np.inf,
        'main_flow': np.nan,
        'main_flow_label': ui_text('Portata principale', 'Main flow'),
        'recovery': np.nan,
        'salt_rejection': np.nan,
        'specific_value': np.nan,
        'specific_label': ui_text('KPI impianto', 'Plant KPI'),
        'specific_unit': '',
    }
    result['age_hours'] = _telemetry_age_hours(result['latest_timestamp'])
    if not np.isfinite(result['age_hours']):
        result['telemetry_level'] = 'critical'
        result['warnings'].append(('critical', ui_text('Telemetria non disponibile.', 'Telemetry unavailable.')))
    elif result['age_hours'] > 24:
        result['telemetry_level'] = 'critical'
        result['warnings'].append(('critical', ui_text(
            f"Nessun dato aggiornato da {result['age_hours'] / 24:.1f} giorni.",
            f"No fresh data for {result['age_hours'] / 24:.1f} days."
        )))
    elif result['age_hours'] > 6:
        result['telemetry_level'] = 'warning'
        result['warnings'].append(('warning', ui_text(
            f"Ultimo dato ricevuto {result['age_hours']:.1f} ore fa.",
            f"Latest data received {result['age_hours']:.1f} hours ago."
        )))
    else:
        result['telemetry_level'] = 'ok'

    df_ro = calcola_metriche_derivate(df_ro_raw) if df_ro_raw is not None and not df_ro_raw.empty else pd.DataFrame()
    if not df_ro.empty:
        baseline_ro, latest_ro = df_ro.iloc[0], df_ro.iloc[-1]
        diagnosis = diagnostica_cip_ro(df_ro, baseline_ro, latest_ro)
        result['cip_diagnosis'] = diagnosis
        if diagnosis['status_code'] in {'cip_due', 'investigate'}:
            result['cip_level'] = 'critical'
            if diagnosis['status_code'] == 'cip_due':
                result['warnings'].append(('critical', ui_text(
                    f"CIP/RO: soglia raggiunta rispetto alla baseline (permeabilità -{diagnosis['perm_loss_pct']:.1f}%, ΔP +{diagnosis['dp_rise_pct']:.1f}%, passaggio salino {diagnosis['salt_passage_change_pct']:+.1f}%).",
                    f"CIP/RO: threshold reached versus baseline (permeability -{diagnosis['perm_loss_pct']:.1f}%, ΔP +{diagnosis['dp_rise_pct']:.1f}%, salt passage {diagnosis['salt_passage_change_pct']:+.1f}%)."
                )))
            else:
                result['warnings'].append(('critical', ui_text(
                    'CIP/RO: possibile anomalia d’integrità o idraulica; eseguire una verifica tecnica prima del lavaggio.',
                    'CIP/RO: possible integrity or hydraulic anomaly; perform a technical check before cleaning.'
                )))
        elif diagnosis['status_code'] == 'warning':
            result['cip_level'] = 'warning'
            result['warnings'].append(('warning', ui_text(
                f"CIP/RO: preallarme rispetto alla baseline (permeabilità -{diagnosis['perm_loss_pct']:.1f}%, ΔP +{diagnosis['dp_rise_pct']:.1f}%, passaggio salino {diagnosis['salt_passage_change_pct']:+.1f}%).",
                f"CIP/RO: early warning versus baseline (permeability -{diagnosis['perm_loss_pct']:.1f}%, ΔP +{diagnosis['dp_rise_pct']:.1f}%, salt passage {diagnosis['salt_passage_change_pct']:+.1f}%)."
            )))
        elif diagnosis['status_code'] in {'normal', 'monitor'}:
            # Una lieve deriva salina isolata resta visibile nel dettaglio, ma
            # non deve generare un warning generale di impianto.
            result['cip_level'] = 'ok'

        result['recovery'] = _finite_float(latest_ro.get('recovery'))
        result['salt_rejection'] = _finite_float(latest_ro.get('sr_norm'))
        overview_flow = config_attuale.get('overview_flow_column')
        flow_candidates = (
            [overview_flow]
            if overview_flow
            else list(config_attuale.get('fit_labels', {}).keys())
        )
        flow_column = next((column for column in flow_candidates if column in latest_ro.index), None)
        if flow_column:
            result['main_flow'] = _finite_float(latest_ro.get(flow_column))
            result['main_flow_label'] = config_attuale.get(
                'overview_flow_label',
                config_attuale.get('fit_labels', {}).get(flow_column, flow_column.upper())
            )

        if config_attuale.get('has_sec') and 'sec' in latest_ro.index:
            result['specific_label'] = ui_text('Consumo SEC', 'SEC consumption')
            result['specific_value'] = _finite_float(latest_ro.get('sec'))
            result['specific_unit'] = 'kWh/m³'
        elif config_attuale.get('has_bag_filters') and 'pit007' in latest_ro.index:
            result['specific_label'] = ui_text('ΔP filtri a calza', 'Bag-filter ΔP')
            result['specific_value'] = _finite_float(latest_ro.get('pit007'))
            result['specific_unit'] = 'bar'
            if np.isfinite(result['specific_value']) and result['specific_value'] >= 1.0:
                result['warnings'].append(('critical', ui_text(
                    f"Filtri a calza da verificare: ΔP {result['specific_value']:.2f} bar.",
                    f"Check bag filters: ΔP {result['specific_value']:.2f} bar."
                )))

        dp_cf01 = _finite_float(latest_ro.get('dp_cf01'))
        if np.isfinite(dp_cf01) and dp_cf01 >= 1.0:
            result['warnings'].append(('critical', ui_text(
                f"Cartuccia CF01 a limite: ΔP {dp_cf01:.2f} bar.",
                f"CF01 cartridge at limit: ΔP {dp_cf01:.2f} bar."
            )))

    if config_attuale.get('has_uf') and df_uf is not None and not df_uf.empty and 'uftmp' in df_uf.columns:
        latest_tmp = _finite_float(df_uf.iloc[-1].get('uftmp'))
        if np.isfinite(latest_tmp):
            if not np.isfinite(result['specific_value']):
                result['specific_label'] = ui_text('TMP UF', 'UF TMP')
                result['specific_value'] = latest_tmp
                result['specific_unit'] = 'bar'
            if latest_tmp >= 1.5:
                result['warnings'].append(('critical', ui_text(
                    f"TMP UF oltre limite: {latest_tmp:.2f} bar.",
                    f"UF TMP above limit: {latest_tmp:.2f} bar."
                )))
            elif latest_tmp >= 1.2:
                result['warnings'].append(('warning', ui_text(
                    f"TMP UF in aumento: {latest_tmp:.2f} bar.",
                    f"UF TMP rising: {latest_tmp:.2f} bar."
                )))

    motor_summary = _motor_health_summary(df_nas, config_attuale, impianto_scelto)
    result['motor_summary'] = motor_summary
    result['motor_level'] = motor_summary['level']
    for message in motor_summary['messages']:
        level = 'critical' if motor_summary['level'] == 'critical' and 'crit' in message.lower() else 'warning'
        result['warnings'].append((level, message))

    quality_summary = _water_quality_summary(impianto_scelto)
    result['quality_summary'] = quality_summary
    result['quality_level'] = quality_summary['level']
    for message in quality_summary['messages']:
        level = 'critical' if quality_summary['level'] == 'critical' and ('critic' in message.lower() or 'critico' in message.lower()) else 'warning'
        result['warnings'].append((level, message))

    levels = [result['telemetry_level'], result['cip_level'], result['motor_level'], result['quality_level']]
    warning_levels = [level for level, _ in result['warnings']]
    if 'critical' in warning_levels or 'critical' in levels:
        result['overall_level'] = 'critical'
    elif 'warning' in warning_levels or 'warning' in levels:
        result['overall_level'] = 'warning'
    elif any(level == 'ok' for level in levels):
        result['overall_level'] = 'ok'
    return result


def _status_display(level):
    displays = {
        'ok': ('🟢', ui_text('Regolare', 'Normal')),
        'warning': ('🟡', ui_text('Attenzione', 'Warning')),
        'critical': ('🔴', ui_text('Critico', 'Critical')),
        'unknown': ('⚪', ui_text('N/D', 'N/A')),
    }
    return displays.get(level, displays['unknown'])


def _format_last_update(summary):
    if pd.isna(summary['latest_timestamp']):
        return ui_text('N/D', 'N/A')
    age = summary['age_hours']
    if age < 1:
        return ui_text(f"{age * 60:.0f} min fa", f"{age * 60:.0f} min ago")
    if age < 24:
        return ui_text(f"{age:.1f} h fa", f"{age:.1f} h ago")
    return ui_text(f"{age / 24:.1f} giorni fa", f"{age / 24:.1f} days ago")


def render_fleet_overview():
    st.title(ui_text('Panoramica di tutti gli impianti', 'All-plants overview'))
    st.caption(ui_text(
        'Stato sintetico di telemetria, membrane/CIP, pompe-motori, processo e qualità dell’acqua.',
        'At-a-glance status for telemetry, membranes/CIP, pumps and motors, process and water quality.'
    ))

    with _RAW_ST.spinner(ui_text('Aggiornamento dati della flotta...', 'Refreshing fleet data...')):
        summaries = [_plant_overview_summary(plant) for plant in CONFIG_IMPIANTI]

    total_warnings = sum(len(summary['warnings']) for summary in summaries)
    online_count = sum(summary['telemetry_level'] == 'ok' for summary in summaries)
    warning_plants = sum(summary['overall_level'] == 'warning' for summary in summaries)
    critical_plants = sum(summary['overall_level'] == 'critical' for summary in summaries)

    a, b, c, d, e = st.columns(5)
    a.metric(ui_text('Impianti totali', 'Total plants'), len(summaries))
    b.metric(ui_text('Online', 'Online'), online_count)
    c.metric(ui_text('In attenzione', 'Warning'), warning_plants)
    d.metric(ui_text('Critici', 'Critical'), critical_plants)
    e.metric(ui_text('Segnalazioni attive', 'Active alerts'), total_warnings)
    st.markdown('---')

    for summary in summaries:
        with st.container(border=True):
            status_icon, status_label = _status_display(summary['overall_level'])
            header_col, button_col = st.columns([5, 1])
            with header_col:
                st.subheader(f"{summary['plant']} — {status_icon} {status_label}")
            with button_col:
                if st.button(
                    ui_text('Apri dettaglio', 'Open details'),
                    key=f"open_{re.sub(r'[^A-Za-z0-9]+', '_', summary['plant'])}",
                    use_container_width=True,
                ):
                    # La nuova selezione verrà inizializzata dall'URL al rerun;
                    # eliminiamo i valori widget correnti per evitare conflitti.
                    _RAW_ST.session_state.pop('nav_plant', None)
                    _RAW_ST.session_state.pop('nav_section', None)
                    _write_query_values(plant=summary['plant'], section='🔵 Osmosi Inversa (RO)')
                    _safe_rerun()

            state_cols = st.columns(4)
            quality_date = summary.get('quality_summary', {}).get('date', pd.NaT)
            quality_detail = (
                ui_text(
                    f"Campione: {quality_date.strftime('%d/%m/%Y')}",
                    f"Sample: {quality_date.strftime('%d/%m/%Y')}"
                )
                if pd.notna(quality_date) else ''
            )
            status_items = [
                (ui_text('Telemetria', 'Telemetry'), summary['telemetry_level'], _format_last_update(summary)),
                (ui_text('Membrane / CIP', 'Membranes / CIP'), summary['cip_level'], ''),
                (ui_text('Pompe / motori', 'Pumps / motors'), summary['motor_level'], ''),
                (ui_text('Qualità acqua', 'Water quality'), summary['quality_level'], quality_detail),
            ]
            for column, (label, level, detail) in zip(state_cols, status_items):
                icon, state_label = _status_display(level)
                column.markdown(f"**{label}**")
                column.write(f"{icon} {state_label}")
                if detail:
                    column.caption(detail)

            kpi_cols = st.columns(4)
            flow_value = f"{summary['main_flow']:.2f} m³/h" if np.isfinite(summary['main_flow']) else ui_text('N/D', 'N/A')
            recovery_value = f"{summary['recovery']:.1f}%" if np.isfinite(summary['recovery']) else ui_text('N/D', 'N/A')
            rejection_value = f"{summary['salt_rejection']:.2f}%" if np.isfinite(summary['salt_rejection']) else ui_text('N/D', 'N/A')
            specific_value = (
                f"{summary['specific_value']:.2f} {summary['specific_unit']}".strip()
                if np.isfinite(summary['specific_value']) else ui_text('N/D', 'N/A')
            )
            kpi_cols[0].metric(summary['main_flow_label'], flow_value)
            kpi_cols[1].metric('Recovery', recovery_value)
            kpi_cols[2].metric(ui_text('Reiezione normalizzata', 'Normalised rejection'), rejection_value)
            kpi_cols[3].metric(summary['specific_label'], specific_value)

            if summary['warnings']:
                with st.expander(ui_text(
                    f"Segnalazioni attive ({len(summary['warnings'])})",
                    f"Active alerts ({len(summary['warnings'])})"
                ), expanded=summary['overall_level'] == 'critical'):
                    for level, message in summary['warnings']:
                        st.markdown(f"{'🔴' if level == 'critical' else '🟡'} {message}")
            else:
                st.success(ui_text('Nessuna segnalazione attiva.', 'No active alerts.'))

# =========================================================
# MAIN DASHBOARD ENTRY POINT
# =========================================================
if __name__ == '__main__':
    _RAW_ST.set_page_config(page_title="Water Partners Fleet Management", layout="wide")

    # --- 1. LOGO DINAMICO IN CIMA ALLA SIDEBAR ---
    import base64
    import streamlit.components.v1 as components

    try:
        # Leggiamo le immagini e le convertiamo in testo (Base64) per iniettarle nell'HTML
        with open("Logo v1.png", "rb") as f:
            logo_light = base64.b64encode(f.read()).decode()
        with open("Logo v1_dark mode.png", "rb") as f:
            logo_dark = base64.b64encode(f.read()).decode()
        
        html_logo = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: transparent;
                display: flex;
                align-items: center;
                justify-content: flex-start; /* Allinea a sinistra */
            }}
            img {{
                width: 100%;
                max-width: 250px;
                max-height: 85px;
                object-fit: contain;
            }}
        </style>
        </head>
        <body>
            <img id="logo" src="data:image/png;base64,{logo_light}">
            <script>
                function updateLogo() {{
                    // Legge il colore del testo che Streamlit applica automaticamente
                    const color = window.getComputedStyle(document.body).color;
                    const match = color.match(/\d+/g);
                    if (match) {{
                        const r = parseInt(match[0]);
                        const g = parseInt(match[1]);
                        const b = parseInt(match[2]);
                        // Calcola la luminosità del testo
                        const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
                        
                        // Se il testo è chiaro (luma > 128), lo sfondo è scuro -> Mostra logo Dark
                        if (luma > 128) {{
                            document.getElementById('logo').src = "data:image/png;base64,{logo_dark}";
                        }} else {{
                            document.getElementById('logo').src = "data:image/png;base64,{logo_light}";
                        }}
                    }}
                }}
                
                // Resta in ascolto: se cambi tema dal menu in alto a destra, cambia il logo all'istante
                const observer = new MutationObserver(updateLogo);
                observer.observe(document.body, {{ attributes: true, attributeFilter: ['style', 'class'] }});
                
                updateLogo();
                setTimeout(updateLogo, 100);
            </script>
        </body>
        </html>
        """
        # Inseriamo il blocco HTML nella sidebar (con un'altezza fissa per evitare barre di scorrimento)
        with _RAW_ST.sidebar:
            components.html(html_logo, height=90)
            
    except Exception:
        _RAW_ST.sidebar.warning("Immagini del logo non trovate. Verifica i nomi dei file.")

    # --- 2. SELEZIONE LINGUA ---
    saved_language = _read_query_value('lang', 'it')
    english_enabled = _RAW_ST.sidebar.toggle(
        "🇬🇧 English",
        value=saved_language == 'en',
        key="dashboard_language_english",
        help="Activate the English interface / Attiva l'interfaccia inglese"
    )
    UI_LANGUAGE = "en" if english_enabled else "it"
    _write_query_values(lang=UI_LANGUAGE)
    st = _TranslatedStreamlit(_RAW_ST)

    st.sidebar.title(ui_text("Gestione Flotta", "Fleet Management"))

    plant_options = [FLEET_OVERVIEW_KEY] + list(CONFIG_IMPIANTI.keys())
    saved_plant = _read_query_value('plant', FLEET_OVERVIEW_KEY)
    if saved_plant not in plant_options:
        saved_plant = FLEET_OVERVIEW_KEY
    if 'nav_plant' in _RAW_ST.session_state and _RAW_ST.session_state['nav_plant'] not in plant_options:
        del _RAW_ST.session_state['nav_plant']

    def format_plant_option(option):
        if option == FLEET_OVERVIEW_KEY:
            return ui_text('🌐 Tutti gli impianti', '🌐 All plants')
        return tr_text(option)

    plant_widget_kwargs = {'format_func': format_plant_option, 'key': 'nav_plant'}
    if 'nav_plant' not in _RAW_ST.session_state:
        plant_widget_kwargs['index'] = plant_options.index(saved_plant)
    impianto_scelto = st.sidebar.selectbox("🌍 Seleziona Impianto:", plant_options, **plant_widget_kwargs)
    _write_query_values(plant=impianto_scelto)

    if impianto_scelto == FLEET_OVERVIEW_KEY:
        st.sidebar.markdown('---')
        st.sidebar.caption(ui_text('Vista riepilogativa della flotta', 'Fleet overview'))
        render_fleet_overview()
    else:
        config_attuale = CONFIG_IMPIANTI[impianto_scelto]

        menu_opzioni = ["🔵 Osmosi Inversa (RO)", "⚡ Inverter & Pompe", "📈 Grafici Personalizzati", 
                        "🔮 Manutenzione Predittiva", "⚖️ Confronto Periodi", "📊 Produzione & ATM", "💧 Qualità Acqua (Manuale)", "📄 Report"]
        if config_attuale["has_uf"]: 
            menu_opzioni.insert(1, "🟢 Ultrafiltrazione (UF)")

        saved_section = _read_query_value('section', menu_opzioni[0])
        if saved_section not in menu_opzioni:
            saved_section = menu_opzioni[0]
        if 'nav_section' in _RAW_ST.session_state and _RAW_ST.session_state['nav_section'] not in menu_opzioni:
            del _RAW_ST.session_state['nav_section']

        section_widget_kwargs = {'key': 'nav_section'}
        if 'nav_section' not in _RAW_ST.session_state:
            section_widget_kwargs['index'] = menu_opzioni.index(saved_section)
        sezione_selezionata = st.sidebar.radio("Seleziona Area Analisi:", menu_opzioni, **section_widget_kwargs)
        _write_query_values(plant=impianto_scelto, section=sezione_selezionata)

        df_ro_raw, df_uf, df_nas, source_msg = load_data(impianto_scelto)
        st.sidebar.markdown("---")
        st.sidebar.caption(f"Origine Dati: {source_msg}")

        st.title(f"Sistema di Monitoraggio - {impianto_scelto[2:]}")

        if sezione_selezionata == "📊 Produzione & ATM":
            render_produzione_atm(impianto_scelto)

        elif sezione_selezionata == "💧 Qualità Acqua (Manuale)":
            render_qualita_acqua(impianto_scelto)

        elif sezione_selezionata == "📄 Report":
            render_report(impianto_scelto, config_attuale, df_ro_raw, df_uf, df_nas)

        elif df_ro_raw.empty:
            st.info(f"Nessun dato registrato per {impianto_scelto}. In attesa dei log...")

        else:
            df_ro = calcola_metriche_derivate(df_ro_raw)
            latest_ro, baseline_ro = df_ro.iloc[-1], df_ro.iloc[0]
            latest_uf, baseline_uf = (
                (df_uf.iloc[-1], df_uf.iloc[0])
                if config_attuale["has_uf"] and not df_uf.empty
                else (
                    pd.Series({"fit001": 0.0, "uftmp": 0.0, "dpscf": 0.0}),
                    pd.Series({"fit001": 0.0, "uftmp": 0.0, "dpscf": 0.0})
                )
            )

            if sezione_selezionata == "🔵 Osmosi Inversa (RO)":
                render_osmosi(df_ro, baseline_ro, latest_ro, config_attuale, impianto_scelto)
            elif sezione_selezionata == "🟢 Ultrafiltrazione (UF)":
                render_uf(df_uf, baseline_uf, latest_uf, impianto_scelto)
            elif sezione_selezionata == "⚡ Inverter & Pompe":
                render_inverter(df_nas, config_attuale, impianto_scelto)
            elif sezione_selezionata == "📈 Grafici Personalizzati":
                render_grafici_personalizzati(df_ro, df_uf)
            elif sezione_selezionata == "🔮 Manutenzione Predittiva":
                render_predittiva(
                    df_ro, df_uf, df_nas, baseline_ro, latest_ro,
                    baseline_uf, latest_uf, config_attuale, impianto_scelto
                )
            elif sezione_selezionata == "⚖️ Confronto Periodi":
                render_confronto(df_ro, df_uf, config_attuale)
