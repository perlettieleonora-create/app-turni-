import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time, date
import calendar

# 1. DATABASE
conn = sqlite3.connect('gestione_avanzata.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute("CREATE TABLE IF NOT EXISTS turni (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, inizio TEXT, fine TEXT, dipendente TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS ferie (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data_inizio TEXT, data_fine TEXT, stato TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS timbrature (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data TEXT, inizio_effettivo TEXT, fine_effettivo TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS dipendenti (id INTEGER PRIMARY KEY, nome TEXT, ruolo TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS notifiche (id INTEGER PRIMARY KEY AUTOINCREMENT, messaggio TEXT, letta INTEGER, data_ora TEXT)")
    c.execute("SELECT COUNT(*) FROM dipendenti")
    if c.fetchone()[0] == 0:
        dips = [('Eleonora', 'Amministratore'), ('Marco', 'Dipendente'), ('Francesco', 'Dipendente'), ('Martina', 'Dipendente'), ('Suman', 'Dipendente')]
        c.executemany("INSERT INTO dipendenti (nome, ruolo) VALUES (?, ?)", dips)
        conn.commit()

init_db()

# 2. COLORI
COLORI = {"Marco": "#3498db", "Francesco": "#2ecc71", "Martina": "#e67e22", "Suman": "#9b59b6", "Ferie": "#e74c3c"}

# 3. INTERFACCIA
st.set_page_config(page_title="Calendario Turni", layout="wide")
st.sidebar.title("🔐 Login")
utente = st.sidebar.selectbox("Chi sei?", ["---", "Eleonora", "Marco", "Francesco", "Martina", "Suman"])

if utente != "---":
    c.execute("SELECT ruolo FROM dipendenti WHERE nome = ?", (utente,))
    ruolo = c.fetchone()[0]
    st.title(f"🗓️ Calendario Mensile - {utente}")

    # SCELTA DATA
    col_m, col_a = st.columns(2)
    mese_nom = list(calendar.month_name)[1:]
    m_sel = col_m.selectbox("Mese", mese_nom, index=datetime.now().month-1)
    a_sel = col_a.number_input("Anno", 2024, 2030, 2024)
    m_idx = mese_nom.index(m_sel) + 1

    # CALENDARIO
    cal = calendar.Calendar(firstweekday=0)
    for sett in cal.monthdatescalendar(a_sel, m_idx):
        cols = st.columns(7)
        for i, giorno in enumerate(sett):
            with cols[i]:
                bg = "#f0f2f6" if giorno.month == m_idx else "#ffffff"
                st.markdown(f"<div style='border:1px solid #ddd;padding:5px;height:120px;background:{bg};overflow-y:auto;'><b>{giorno.day}</b>", unsafe_allow_html=True)
                
                # Visualizza Turni
                t_df = pd.read_sql_query(f"SELECT dipendente, inizio FROM turni WHERE data='{giorno}'", conn)
                for _, r in t_df.iterrows():
                    color = COLORI.get(r['dipendente'], "#7f8c8d")
                    st.markdown(f"<div style='background:{color};color:white;font-size:10px;padding:2px;margin-bottom:2px;border-radius:3px;'>{r['dipendente']} {r['inizio']}</div>", unsafe_allow_html=True)
                
                # Visualizza Ferie
                f_df = pd.read_sql_query(f"SELECT dipendente FROM ferie WHERE stato='Approvato' AND '{giorno}' >= data_inizio AND '{giorno}' <= data_fine", conn)
                for _, r in f_df.iterrows():
                    st.markdown(f"<div style='background:{COLORI['Ferie']};color:white;font-size:10px;padding:2px;margin-bottom:2px;border-radius:3px;'>🏖️ {r['dipendente']}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # AZIONI
    if ruolo == "Amministratore":
        t1, t2, t3 = st.tabs(["➕ Crea Turno", "✅ Approvazioni", "🕒 Log Timbrature"])
        with t1:
            with st.form("t"):
                d = st.selectbox("Dipendente", ["Marco", "Francesco", "Martina", "Suman"])
                day = st.date_input("Data")
                ora_i = st.time_input("Inizio", time(9,0))
                ora_f = st.time_input("Fine", time(18,0))
                if st.form_submit_button("Salva"):
                    c.execute("INSERT INTO turni (data, inizio, fine, dipendente) VALUES (?,?,?,?)", (str(day), str(ora_i), str(ora_f), d))
                    conn.commit(); st.success("Salvato!"); st.rerun()
        with t2:
            st.write(pd.read_sql_query("SELECT id, dipendente, data_inizio, data_fine FROM ferie WHERE stato='In attesa'", conn))
            fid = st.number_input("ID richiesta ferie", step=1, min_value=0)
            if st.button("Approva Ferie"):
                c.execute("UPDATE ferie SET stato='Approvato' WHERE id=?", (fid,))
                conn.commit(); st.success("Approvate!"); st.rerun()
        with t3:
            st.dataframe(pd.read_sql_query("SELECT * FROM timbrature", conn), use_container_width=True)
    else:
        t1, t2 = st.tabs(["✍️ Timbra", "🏖️ Richiedi Ferie"])
        with t1:
            with st.form("tm"):
                ti = st.time_input("Ora inizio lavoro")
                tf = st.time_input("Ora fine lavoro")
                if st.form_submit_button("Registra Timbrata"):
                    c.execute("INSERT INTO timbrature (dipendente, data, inizio_effettivo, fine_effettivo) VALUES (?,?,?,?)", (utente, str(date.today()), str(ti), str(tf)))
                    conn.commit(); st.success("Registrato!")
        with t2:
            dfer = st.date_input("Seleziona Date", [])
            if st.button("Invia") and len(dfer) == 2:
                c.execute("INSERT INTO ferie (dipendente, data_inizio, data_fine, stato) VALUES (?,?,?,?)", (utente, str(dfer[0]), str(dfer[1]), "In attesa"))
                conn.commit(); st.success("Inviata!")