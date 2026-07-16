import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time, date
import calendar

# --- DATABASE ---
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

# --- COLORI ---
COLORI = {"Marco": "#3498db", "Francesco": "#2ecc71", "Martina": "#e67e22", "Suman": "#9b59b6", "Ferie": "#e74c3c"}

# --- INTERFACCIA ---
st.set_page_config(page_title="Calendario Turni", layout="wide")

st.sidebar.title("🔐 Login")
utente_attivo = st.sidebar.selectbox("Chi sei?", ["---", "Eleonora", "Marco", "Francesco", "Martina", "Suman"])

if utente_attivo != "---":
    c.execute("SELECT ruolo FROM dipendenti WHERE nome = ?", (utente_attivo,))
    ruolo = c.fetchone()[0]

st.title(f"🗓️ Calendario Mensile - {utente_attivo}")

    # Selezione Mese
    col_m, col_a = st.columns(2)
    mese_corrente = col_m.selectbox("Mese", list(calendar.month_name)[1:], index=datetime.now().month-1)
    anno_corrente = col_a.number_input("Anno", 2024, 2030, 2024)
    idx_mese = list(calendar.month_name).index(mese_corrente)

    # Legenda rapida
    st.markdown(" ".join([f"<span style='background:{c};color:white;padding:3px;border-radius:3px'>{n}</span>" for n,c in COLORI.items()]), unsafe_allow_html=True)

    # Griglia Calendario
    cal = calendar.Calendar(firstweekday=0)
    for settimana in cal.monthdatescalendar(anno_corrente, idx_mese):
        cols = st.columns(7)
        for i, giorno in enumerate(settimana):
            with cols[i]:
                color = "#f0f2f6" if giorno.month == idx_mese else "#ffffff"
                cont_style = f"border:1px solid #ddd;padding:5px;height:120px;background:{color};overflow-y:auto;"
                st.markdown(f"<div style='{cont_style}'><b>{giorno.day}</b>", unsafe_allow_html=True)
                
                # Turni
                df_t = pd.read_sql_query(f"SELECT dipendente, inizio, fine FROM turni WHERE data='{giorno}'", conn)
                for _, r in df_t.iterrows():
                    bg = COLORI.get(r['dipendente'], "#7f8c8d")
                    st.markdown(f"<div style='background:{bg};color:white;font-size:10px;margin:2px;padding:2px;border-radius:3px;'>{r['dipendente']} {r['inizio']}</div>", unsafe_allow_html=True)
                
                # Ferie
                query_f = f"SELECT dipendente FROM ferie WHERE stato='Approvato' AND '{giorno}' >= data_inizio AND '{giorno}' <= data_fine"
                df_f = pd.read_sql_query(query_f, conn)
                for _, r in df_f.iterrows():
                    st.markdown(f"<div style='background:{COLORI['Ferie']};color:white;font-size:10px;margin:2px;padding:2px;border-radius:3px;'>🏖️ {r['dipendente']}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # AZIONI
    if ruolo == "Amministratore":
        t1, t2, t3 = st.tabs(["➕ Crea Turno", "✅ Approvazioni", "🕒 Log Timbrature"])
        with t1:
            with st.form("new_turno"):
                d = st.selectbox("Dipendente", ["Marco", "Francesco", "Martina", "Suman"])
                g = st.date_input("Giorno")
                h_i = st.time_input("Inizio", time(9,0))
                h_f = st.time_input("Fine", time(18,0))
                if st.form_submit_button("Salva"):
                    c.execute("INSERT INTO turni (data, inizio, fine, dipendente) VALUES (?,?,?,?)", (str(g), str(h_i), str(h_f), d))
                    conn.commit(); st.success("Fatto!"); st.rerun()
        with t2:
            df_fe = pd.read_sql_query("SELECT * FROM ferie WHERE stato = 'In attesa'", conn)
            st.write(df_fe)
            id_f = st.number_input("Inserisci ID ferie per approvare", step=1, min_value=0)
            if st.button("Approva"):
                c.execute("UPDATE ferie SET stato='Approvato' WHERE id=?", (id_f,))
                conn.commit(); st.rerun()
        with t3:
        st.dataframe(pd.read_sql_query("SELECT * FROM timbrature", conn))

    else:
        t1, t2 = st.tabs(["✍️ Timbra", "🏖️ Richiedi Ferie"])
        with t1:
            with st.form("timb"):
                i = st.time_input("Inizio lavoro")
                f = st.time_input("Fine lavoro")
                if st.form_submit_button("Salva Timbratura"):
                    c.execute("INSERT INTO timbrature (dipendente, data, inizio_effettivo, fine_effettivo) VALUES (?,?,?,?)", (utente_attivo, str(date.today()), str(i), str(f)))
                    conn.commit(); st.success("Registrato!")
        with t2:
            dr = st.date_input("Seleziona Date", [])
            if st.button("Invia Richiesta") and len(dr) == 2:
                c.execute("INSERT INTO ferie (dipendente, data_inizio, data_fine, stato) VALUES (?,?,?,?)", (utente_attivo, str(dr[0]), str(dr[1]), "In attesa"))
                conn.commit(); st.success("Inviata ad Eleonora!")