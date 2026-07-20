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

_EXACT_TRANSLATIONS = {'N/D': 'N/A', 'Gennaio': 'January', 'Febbraio': 'February', 'Marzo': 'March', 'Aprile': 'April', 'Maggio': 'May', 'Giugno': 'June', 'Luglio': 'July', 'Agosto': 'August', 'Settembre': 'September', 'Ottobre': 'October', 'Novembre': 'November', 'Dicembre': 'December', '🌵 GW012 Kaktus (Capo Verde)': '🌵 GW012 Kaktus (Cape Verde)', '🌴 Pingwe (Zanzibar)': '🌴 Pingwe (Zanzibar)', 'Gestione Flotta': 'Fleet Management', '🌍 Seleziona Impianto:': '🌍 Select plant:', 'Seleziona Area Analisi:': 'Select analysis area:', '🔵 Osmosi Inversa (RO)': '🔵 Reverse Osmosis (RO)', '🟢 Ultrafiltrazione (UF)': '🟢 Ultrafiltration (UF)', '⚡ Inverter & Pompe': '⚡ Inverters & Pumps', '📈 Grafici Personalizzati': '📈 Custom Charts', '🔮 Manutenzione Predittiva': '🔮 Predictive Maintenance', '⚖️ Confronto Periodi': '⚖️ Period Comparison', '📊 Produzione & ATM': '📊 Production & ATM', '☁️ Cloud Supabase': '☁️ Supabase Cloud', '🖥️ Locale SQLite': '🖥️ Local SQLite', 'Recovery': 'Recovery', 'Reiezione (Norm)': 'Rejection (Norm.)', 'ΔP Filtri a Calza': 'Bag-filter ΔP', 'Consumo SEC': 'SEC consumption', 'ΔP Cartuccia CF01': 'CF01 cartridge ΔP', 'ΔP Membrane': 'Membrane ΔP', 'Parametri Acqua (Extra)': 'Water Parameters (Additional)', 'pH Permeato': 'Permeate pH', 'Conducibilità Alimento': 'Feed conductivity', 'Conducibilità Permeato': 'Permeate conductivity', 'Grafici di Tendenza': 'Trend Charts', 'Dati Tabellari ed Esportazione': 'Tabular Data and Export', '📥 Esporta Storico in formato CSV': '📥 Export history as CSV', '📥 Esporta CSV': '📥 Export CSV', 'Nessun dato UF.': 'No UF data.', 'Flusso UF': 'UF flow', 'TMP UF': 'UF TMP', 'ΔP Filtro': 'Filter ΔP', 'Trend Pressioni UF': 'UF pressure trends', 'Nessun dato inverter.': 'No inverter data.', 'Pompa': 'Pump', 'Nome Pompa': 'Pump name', 'Analisi Salute Statore': 'Stator Health Analysis', 'Seleziona pompa per trend Cosφ:': 'Select pump for Cosφ trend:', 'Seleziona Intervallo:': 'Select range:', 'Scegli parametri:': 'Select parameters:', '🔮 Analisi Predittiva e Stato di Salute': '🔮 Predictive Analysis and Health Status', '📊 Cruscotto Salute': '📊 Health Dashboard', '💧 Membrane (Perm)': '💧 Membranes (Permeability)', '🧱 Fouling Spaziatori (ΔP)': '🧱 Spacer Fouling (ΔP)', '🟢 Membrane UF': '🟢 UF Membranes', '🧦 Filtri a Calza': '🧦 Bag Filters', '🗑️ Cartucce CF01': '🗑️ CF01 Cartridges', '⛨ Diagnostica Motori': '⛨ Motor Diagnostics', 'Membrane RO (ASTM)': 'RO membranes (ASTM)', 'Spaziatori RO (ΔP)': 'RO spacers (ΔP)', 'Filtro Cartucce CF01': 'CF01 cartridge filter', 'Membrane UF': 'UF membranes', 'Filtri a Calza': 'Bag filters', 'Stabile - Nessun intervento': 'Stable — No intervention required', 'Dati insufficienti': 'Insufficient data', 'Indice Pulito a 25°C': 'Clean index at 25°C', 'Situazione Stabile': 'Stable condition', 'ΔP Attuale': 'Current ΔP', 'Situazione Idraulica Stabile': 'Stable hydraulic condition', 'Stato Elettrico': 'Electrical status', 'Stato Meccanico': 'Mechanical status', 'Deriva Cosφ (Elettrica)': 'Cosφ drift (Electrical)', 'Degrado A/Hz (Meccanica)': 'A/Hz degradation (Mechanical)', '🔴 Critico': '🔴 Critical', '🟡 Attenzione': '🟡 Warning', '🟢 Ottimale': '🟢 Optimal', 'Seleziona pompa per dettaglio trend storico:': 'Select pump for detailed historical trend:', 'Fattore di potenza': 'Power factor', '⚖️ Analisi Comparativa (A/B Test)': '⚖️ Comparative Analysis (A/B Test)', '📊 Seleziona il Parametro da analizzare:': '📊 Select the parameter to analyse:', 'Date Periodo A:': 'Period A dates:', 'Date Periodo B:': 'Period B dates:', 'Media Periodo A': 'Period A average', 'Media Periodo B': 'Period B average', 'Variazione Percentuale': 'Percentage change', 'Permeabilità Normalizzata (Fouling RO)': 'Normalised permeability (RO fouling)', 'Salto di Pressione (ΔP RO)': 'Pressure drop (RO ΔP)', 'Reiezione Salina (%)': 'Salt rejection (%)', 'Consumo Specifico (SEC)': 'Specific energy consumption (SEC)', 'TMP Ultrafiltrazione': 'Ultrafiltration TMP', '📊 Produzione e vendite ATM': '📊 Production and ATM Sales', 'Mese da analizzare:': 'Month to analyse:', 'Dati da visualizzare nel grafico:': 'Data to display in the chart:', 'Produzione': 'Production', 'Vendite ATM': 'ATM sales', 'Concentrato': 'Concentrate', 'Totale prodotto': 'Total production', 'Totale venduto ATM': 'Total ATM sales', 'Totale concentrato': 'Total concentrate', 'Media giornaliera prodotta': 'Average daily production', 'Media giornaliera venduta': 'Average daily ATM sales', 'Media giornaliera concentrato': 'Average daily concentrate', 'Medie giornaliere per periodo personalizzato': 'Daily averages for a custom period', 'Seleziona il periodo da analizzare:': 'Select the period to analyse:', 'Media produzione nel periodo': 'Average production in the period', 'Media vendite ATM nel periodo': 'Average ATM sales in the period', 'Media concentrato nel periodo': 'Average concentrate in the period', '#### Grafico del periodo selezionato': '#### Selected-period chart', '#### Grafico del mese selezionato': '#### Selected-month chart', 'Riepilogo giornaliero': 'Daily summary', 'Dettaglio produzione PDF': 'PDF production details', 'Dettaglio ATM': 'ATM details', 'Data': 'Date', 'Prodotto (m³)': 'Production (m³)', 'Concentrato (m³)': 'Concentrate (m³)', 'Venduto ATM (L)': 'ATM sales (L)', 'Venduto ATM (m³)': 'ATM sales (m³)', 'data_rif': 'Reference date', 'permeato': 'Permeate', 'concentrato': 'Concentrate', 'insolation': 'Solar irradiation', 'file_origine': 'Source file', 'litri_erogati': 'Dispensed litres', 'atm_id': 'ATM ID', 'atm_litri': 'ATM litres', 'atm_m3': 'ATM m³', '🏢 Telemetria ATM (Distribuito)': '🏢 ATM Telemetry (Distributed)', 'Totale Litri Erogati': 'Total litres dispensed', 'Media Giornaliera': 'Daily average', '📄 Analisi Produzione da PDF': '📄 PDF Production Analysis', 'Totale Permeato': 'Total permeate', 'Media Insolazione': 'Average solar irradiation', 'Flusso Permeato': 'Permeate flow', 'Flusso Concentrato': 'Concentrate flow', 'Flusso Potabile (Uscita)': 'Potable-water flow (Outlet)', 'Pompa HP 1 (RO)': 'HP pump 1 (RO)', 'Pompa HP 2 (RO)': 'HP pump 2 (RO)', 'Pompa HP 3 (RO)': 'HP pump 3 (RO)', 'Pompa HP 4 (RO)': 'HP pump 4 (RO)', 'Pompa Pozzo Kaktus': 'Kaktus well pump', 'Pompa Alimento (RO)': 'RO feed pump', 'Pompa Travaso TK10-3': 'TK10-3 transfer pump', 'Pompa Pozzo Toninho': 'Toninho well pump', 'Pompa Travaso TK11-3': 'TK11-3 transfer pump', 'Pompa Pozzo 1 (P01)': 'Well pump 1 (P01)', 'Pompa Pozzo 2 (P05)': 'Well pump 2 (P05)', 'Pompa ATM Standard': 'Standard ATM pump', 'Pompa ATM Premium': 'Premium ATM pump', 'Pompa Ausiliaria (NAS5)': 'Auxiliary pump (NAS5)', 'Pompa Sconosciuta': 'Unknown pump', 'P. Ingresso (bar)': 'Inlet pressure (bar)', 'P. Uscita (bar)': 'Outlet pressure (bar)', 'Permeato (m³/h)': 'Permeate (m³/h)', 'Portata (m³/h)': 'Flow (m³/h)', 'Pressione (bar)': 'Pressure (bar)', 'Permeabilità (m³/h/bar)': 'Permeability (m³/h/bar)', 'Permeabilità normalizzata': 'Normalised permeability', 'Salto di pressione (bar)': 'Pressure drop (bar)', 'ΔP (bar)': 'ΔP (bar)', 'Volume giornaliero (m³)': 'Daily volume (m³)', 'Dato': 'Data series', 'Baseline': 'Baseline', 'Limite': 'Limit', 'Previsione': 'Forecast', 'Regressione': 'Regression', 'Previsione fouling': 'Fouling forecast', 'Previsione intasamento': 'Clogging forecast', 'Trend reale (media 24h)': 'Actual trend (24 h average)', 'ΔP reale (media 24h)': 'Actual ΔP (24 h average)', 'ΔP reale': 'Actual ΔP', 'TMP reale': 'Actual TMP', 'Limite TMP': 'TMP limit', 'Limite sostituzione': 'Replacement limit', 'Limite CIP (85%)': 'CIP limit (85%)', 'Limite rischio CIP (+15%)': 'CIP risk limit (+15%)', 'Baseline installazione': 'Installation baseline', 'Allarme (-10%)': 'Alarm (-10%)', 'Trend (Media 24h)': 'Trend (24 h average)', 'Dato Orario': 'Hourly data', 'm³/giorno': 'm³/day', 'L/giorno': 'L/day', "💡 **Guida alla Lettura - Osmosi Inversa (RO):**\n    - **Recovery (Recupero):** La percentuale di acqua di alimento trasformata in permeato (acqua dolce).\n    - **Reiezione Salina (Normalizzata):** Indica l'efficienza chimica della membrana nel bloccare i sali, depurata matematicamente dalle fluttuazioni di temperatura. Per calcolarla si usa il fattore $TCF = \\exp\\left[2640 \\cdot \\left(\\frac{1}{298.15} - \\frac{1}{T_{acqua} + 273.15}\\right)\\right]$. Valori ottimali: > 98%.\n    - **Consumo SEC:** Energia Specifica Consumata (kWh/m³). Rappresenta quanta energia è necessaria per produrre un singolo metro cubo di acqua dolce.\n    - **ΔP (Salto di Pressione):** Misura la perdita di carico idraulica tra l'ingresso e l'uscita dei vessel. Un aumento continuo segnala un'ostruzione fisica (fouling, bio-fouling o scaling inorganico).": "💡 **Reading Guide — Reverse Osmosis (RO):**\n    - **Recovery:** The percentage of feedwater converted into permeate (fresh water).\n    - **Normalised salt rejection:** The membrane's efficiency in retaining salts, mathematically corrected for temperature fluctuations. It uses the factor $TCF = \\exp\\left[2640 \\cdot \\left(\\frac{1}{298.15} - \\frac{1}{T_{water} + 273.15}\\right)\\right]$. Recommended values: > 98%.\n    - **SEC consumption:** Specific energy consumption (kWh/m³), indicating the energy required to produce one cubic metre of fresh water.\n    - **ΔP (pressure drop):** The hydraulic pressure loss between vessel inlet and outlet. A continuous increase indicates physical obstruction such as fouling, biofouling or inorganic scaling.", "💡 **Guida alla Lettura - Ultrafiltrazione (UF):**\n    - **TMP (Pressione Trans-Membrana):** È la pressione netta necessaria per forzare l'acqua ad attraversare i pori microscopici (fibre cave) della membrana di pre-trattamento. \n    - **Salute dell'Asset:** Un rapido e continuo aumento della TMP (verso la soglia di guardia di 1.5 bar) indica un intasamento dei pori (fouling irreversibile) o la necessità di rendere i cicli di controlavaggio (Backwash / CEB) più frequenti o aggressivi.": '💡 **Reading Guide — Ultrafiltration (UF):**\n    - **TMP (Transmembrane Pressure):** The net pressure required to force water through the microscopic pores (hollow fibres) of the pretreatment membrane.\n    - **Asset health:** A rapid and continuous rise in TMP towards the 1.5 bar warning threshold indicates pore blockage (irreversible fouling) or the need for more frequent or more intensive backwash/CEB cycles.', "💡 **Guida alla Lettura - Elettromeccanica Inverter:**\n    - **Cosφ (Fattore di Potenza):** Indica l'efficienza magnetica dello statore del motore elettrico. Un calo progressivo o brusco del Cosφ rispetto alla linea di base indica degrado dell'isolamento o possibili cortocircuiti tra le spire avvolte (situazione critica).\n    - **Sforzo Meccanico (A/Hz):** L'indice calcolato dal rapporto tra Corrente assorbita e Frequenza di rete. Un aumento di questo valore indica che la pompa sta chiedendo più Ampere a parità di giri di rotazione: è un forte campanello d'allarme per usura dei cuscinetti, attriti anomali o blocco della girante idraulica.": '💡 **Reading Guide — Inverter Electromechanics:**\n    - **Cosφ (power factor):** Indicates the magnetic efficiency of the electric motor stator. A gradual or sudden decrease from the baseline may indicate insulation degradation or possible turn-to-turn short circuits.\n    - **Mechanical load (A/Hz):** The ratio between current draw and operating frequency. An increase means the pump requires more current at the same speed, which may indicate bearing wear, abnormal friction or impeller blockage.', "💡 **Guida alla Lettura - Troubleshooting ed Esplorazione Libera:**\n    Questa sezione non impone regole predefinite o calcoli automatici. Puoi sovrapporre liberamente qualsiasi parametro (idraulico, chimico o elettrico) memorizzato nel database per identificare correlazioni anomale non ovvie (ad esempio: misurare in quale misura un picco di pressione dell'alimento influenza il consumo elettrico SEC). È lo strumento ideale per la *Root Cause Analysis* in caso di anomalie di sistema.": '💡 **Reading Guide — Troubleshooting and Free Exploration:**\n    This section applies no predefined rules or automatic calculations. You can freely overlay any hydraulic, chemical or electrical parameter stored in the database to identify non-obvious abnormal correlations, such as how a feed-pressure spike affects SEC. It is designed for *Root Cause Analysis* when system anomalies occur.', '💡 **Guida alla Lettura - Modello Predittivo:**\n    - **Health Score (%):** Un indicatore compreso tra 0 e 100 che rappresenta la "vita utile residua" dell\'asset prima di dover effettuare una manutenzione correttiva.\n    - **Come calcoliamo le date:** Il sistema utilizza un algoritmo di **Regressione Lineare** (usando l\'equazione $y = mx + q$) che elabora la tendenza dei dati storici. Quando la retta di regressione tracciata dal modello interseca i limiti ingegneristici predefiniti (ad esempio: una perdita del 15% sulla permeabilità iniziale), il sistema stima in modo proattivo i giorni rimanenti al lavaggio (CIP) o alla sostituzione.': "💡 **Reading Guide — Predictive Model:**\n    - **Health Score (%):** An indicator from 0 to 100 representing the asset's estimated remaining useful condition before corrective maintenance is required.\n    - **How dates are calculated:** The system uses a **linear regression** algorithm ($y = mx + q$) to evaluate the historical trend. When the regression line intersects a predefined engineering limit, such as a 15% loss of initial permeability, it estimates the remaining time before CIP or replacement.", '💡 **Guida alla Lettura - Analisi Comparativa (A/B Test e Box Plot):**\n    - **La "Scatola" (Box):** Rappresenta visivamente il 50% centrale delle letture di quel periodo (il range di funzionamento "normale"). Se la scatola si "allarga" molto, l\'impianto sta soffrendo di instabilità idraulica.\n    - **La Mediana (linea centrale):** È il valore medio effettivo di funzionamento. Se la mediana del Periodo B è palesemente disallineata da quella del Periodo A, significa che l\'impianto ha subito una deviazione strutturale (es. dopo aver cambiato le cartucce o eseguito un CIP).\n    - **I Puntini (Outliers):** Identificano singoli campioni anomali, fuori scala rispetto al normale ciclo produttivo (ad esempio: colpi d\'ariete, partenze repentine dell\'inverter). Più puntini vedi, più l\'infrastruttura ha subito shock termici o idraulici.': '💡 **Reading Guide — Comparative Analysis (A/B Test and Box Plot):**\n    - **The box:** Represents the central 50% of the readings in the period, corresponding to the normal operating range. A much wider box indicates greater hydraulic instability.\n    - **The median:** The central operating value. A clear shift in Period B compared with Period A indicates a structural change, such as after cartridge replacement or CIP.\n    - **Outliers:** Individual samples outside the normal operating distribution, such as water hammer or abrupt inverter starts. More outliers indicate more frequent hydraulic or thermal shocks.'}


_EXACT_TRANSLATIONS.update({
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


@st.cache_data(ttl=300)
def load_produzione_atm(impianto_scelto):
    """Carica e normalizza produzione da PDF e vendite ATM per l'impianto scelto."""
    nome_db = "Kaktus" if "Kaktus" in impianto_scelto else "Pingwe"

    from supabase import create_client
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

    res_pdf = (
        supabase.table("produzione_pdf")
        .select("*")
        .eq("impianto", nome_db)
        .order("data_rif", desc=False)
        .execute()
    )
    res_atm = (
        supabase.table("storico_atm")
        .select("*")
        .eq("impianto", nome_db)
        .order("data_rif", desc=False)
        .execute()
    )

    df_pdf = pd.DataFrame(res_pdf.data)
    df_atm = pd.DataFrame(res_atm.data)

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
    oggi = pd.Timestamp.today().normalize()

    # Per il mese corrente non vengono conteggiati giorni futuri.
    fine_periodo_media = (
        min(fine_mese, oggi)
        if periodo == oggi.to_period("M")
        else fine_mese
    )
    giorni_periodo = max(1, (fine_periodo_media - inizio_mese).days + 1)

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
        if pd.notna(totale_prodotto)
        else np.nan
    )
    media_concentrato = (
        totale_concentrato / giorni_periodo
        if pd.notna(totale_concentrato)
        else np.nan
    )
    media_atm_m3 = (
        totale_atm_m3 / giorni_periodo
        if pd.notna(totale_atm_m3)
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

    st.caption(
        f"Le medie mensili sono calcolate su {giorni_periodo} giorni "
        f"{'trascorsi del mese' if periodo == oggi.to_period('M') else 'di calendario'}."
    )

    # ---------------------------------------------------------
    # Medie di un intervallo personalizzato
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("Medie giornaliere per periodo personalizzato")

    default_inizio = max(data_min, data_max - pd.Timedelta(days=29))

    intervallo = st.date_input(
        "Seleziona il periodo da analizzare:",
        value=[default_inizio.date(), data_max.date()],
        min_value=data_min.date(),
        max_value=data_max.date(),
        key="periodo_personalizzato_produzione_atm"
    )

    if isinstance(intervallo, (list, tuple)) and len(intervallo) == 2:
        data_da = pd.Timestamp(intervallo[0]).normalize()
        data_a = pd.Timestamp(intervallo[1]).normalize()

        if data_da > data_a:
            st.warning("La data iniziale deve precedere la data finale.")
        else:
            giorni_custom = max(1, (data_a - data_da).days + 1)

            pdf_custom = (
                df_pdf[
                    (df_pdf["data_rif"] >= data_da)
                    & (df_pdf["data_rif"] <= data_a)
                ].copy()
                if not df_pdf.empty
                else pd.DataFrame()
            )
            atm_custom = (
                df_atm[
                    (df_atm["data_rif"] >= data_da)
                    & (df_atm["data_rif"] <= data_a)
                ].copy()
                if not df_atm.empty
                else pd.DataFrame()
            )

            prod_custom, atm_custom_giorno = aggrega_giornaliero(
                pdf_custom, atm_custom
            )
            giornaliero_custom = crea_calendario_giornaliero(
                data_da, data_a, prod_custom, atm_custom_giorno
            )

            totale_prod_custom = totale_colonna(
                giornaliero_custom, "permeato"
            )
            totale_conc_custom = totale_colonna(
                giornaliero_custom, "concentrato"
            )
            totale_atm_custom_l = totale_colonna(
                giornaliero_custom, "atm_litri"
            )
            totale_atm_custom_m3 = (
                totale_atm_custom_l / 1000.0
                if pd.notna(totale_atm_custom_l)
                else np.nan
            )

            media_prod_custom = (
                totale_prod_custom / giorni_custom
                if pd.notna(totale_prod_custom)
                else np.nan
            )
            media_atm_custom = (
                totale_atm_custom_m3 / giorni_custom
                if pd.notna(totale_atm_custom_m3)
                else np.nan
            )
            media_conc_custom = (
                totale_conc_custom / giorni_custom
                if pd.notna(totale_conc_custom)
                else np.nan
            )

            p1, p2, p3 = st.columns(3)
            p1.metric(
                "Media produzione nel periodo",
                formatta_intero(media_prod_custom, "m³/giorno")
            )
            p2.metric(
                "Media vendite ATM nel periodo",
                formatta_intero(media_atm_custom, "m³/giorno")
            )
            p3.metric(
                "Media concentrato nel periodo",
                formatta_intero(media_conc_custom, "m³/giorno")
            )

            st.caption(
                f"Periodo dal {data_da.strftime('%d/%m/%Y')} al "
                f"{data_a.strftime('%d/%m/%Y')}: {giorni_custom} giorni di calendario."
            )

            st.markdown("#### Grafico del periodo selezionato")
            if not serie_scelte:
                st.info("Seleziona almeno una serie da visualizzare nel grafico.")
            else:
                fig_periodo = crea_grafico_barre(
                    giornaliero_custom,
                    serie_scelte,
                    (
                        "Volumi giornalieri — "
                        f"{data_da.strftime('%d/%m/%Y')} – "
                        f"{data_a.strftime('%d/%m/%Y')}"
                    )
                )
                if fig_periodo is not None:
                    st.plotly_chart(
                        fig_periodo,
                        use_container_width=True,
                        key="grafico_periodo_personalizzato"
                    )
    else:
        st.info("Seleziona una data iniziale e una data finale.")

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
        L_PERM_RO = float(baseline_ro.get("perm_norm_smooth", np.nan)) * 0.85
        L_DPRO = float(baseline_ro.get("dp_ro_smooth", np.nan)) * 1.15
        L_DPCF01 = 1.0
        asset_rows = [[_r("Asset", "Asset"), _r("Valore attuale", "Current value"), _r("Health score", "Health score"), _r("Stima soglia", "Threshold estimate")]]
        assets = [
            (_r("Membrane RO", "RO membranes"), "perm_norm_smooth", L_PERM_RO, False, ""),
            (_r("Spaziatori RO", "RO spacers"), "dp_ro_smooth", L_DPRO, True, "bar"),
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
        charts = []
        charts.append(_report_chart_trend(ro_period, "perm_norm_smooth", "Permeabilità normalizzata delle membrane RO", "RO membrane normalised permeability", "Permeabilità normalizzata", "Normalised permeability", limit=float(baseline_ro.get("perm_norm_smooth", np.nan)) * 0.85, forecast_days=30, direction="down"))
        charts.append(_report_chart_trend(ro_period, "dp_ro_smooth", "Salto di pressione delle membrane RO", "RO membrane pressure drop", "ΔP (bar)", "ΔP (bar)", limit=float(baseline_ro.get("dp_ro_smooth", np.nan)) * 1.15, baseline=float(baseline_ro.get("dp_ro_smooth", np.nan)), forecast_days=30, direction="up"))
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

# =========================================================
# MAIN DASHBOARD ENTRY POINT
# =========================================================
if __name__ == '__main__':
    _RAW_ST.set_page_config(page_title="Water Partners Fleet Management", layout="wide")

    english_enabled = _RAW_ST.sidebar.toggle(
        "🇬🇧 English",
        value=False,
        key="dashboard_language_english",
        help="Activate the English interface / Attiva l'interfaccia inglese"
    )
    UI_LANGUAGE = "en" if english_enabled else "it"
    st = _TranslatedStreamlit(_RAW_ST)

    st.sidebar.image("https://img.icons8.com/color/96/000000/globe.png", width=60)
    st.sidebar.title("Gestione Flotta")
    
    impianto_scelto = st.sidebar.selectbox("🌍 Seleziona Impianto:", list(CONFIG_IMPIANTI.keys()))
    config_attuale = CONFIG_IMPIANTI[impianto_scelto]

    menu_opzioni = ["🔵 Osmosi Inversa (RO)", "⚡ Inverter & Pompe", "📈 Grafici Personalizzati", 
                    "🔮 Manutenzione Predittiva", "⚖️ Confronto Periodi", "📊 Produzione & ATM", "📄 Report"]
    if config_attuale["has_uf"]: 
        menu_opzioni.insert(1, "🟢 Ultrafiltrazione (UF)")
        
    sezione_selezionata = st.sidebar.radio("Seleziona Area Analisi:", menu_opzioni)
    
    df_ro_raw, df_uf, df_nas, source_msg = load_data(impianto_scelto)
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Origine Dati: {source_msg}")

    st.title(f"Sistema di Monitoraggio - {impianto_scelto[2:]}")

    if sezione_selezionata == "📊 Produzione & ATM":
        render_produzione_atm(impianto_scelto)

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
