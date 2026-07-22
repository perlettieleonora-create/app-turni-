import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time, date, timedelta
import calendar

# --- CONFIGURAZIONE ---
conn = sqlite3.connect('db_gestione_v4.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute("CREATE TABLE IF NOT EXISTS turni (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, inizio TEXT, fine TEXT, dipendente TEXT, note TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS ferie (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data_inizio TEXT, data_fine TEXT, tipo TEXT, stato TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS timbrature (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data TEXT, inizio_effettivo TEXT, fine_effettivo TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS notifiche (id INTEGER PRIMARY KEY AUTOINCREMENT, messaggio TEXT, data_ora TEXT, letta INTEGER)")
    conn.commit()

init_db()

COLORI = {"Marco": "#3498db", "Francesco": "#2ecc71", "Martina": "#f39c12", "Suman": "#9b59b6", "Ferie": "#e74c3c", "Malattia": "#95a5a6", "Permesso": "#7f8c8d"}
DIP = ["Marco", "Francesco", "Martina", "Suman"]

st.set_page_config(page_title="Gestore Turni", layout="wide")

# --- LOGIN ---
st.sidebar.title("🔐 Login")
utente = st.sidebar.selectbox("Chi sei?", ["---", "Eleonora (Admin)"] + DIP)

auth = False
if utente == "Eleonora (Admin)":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == "admin123":
        auth = True
    elif pwd != "":
        st.sidebar.error("Sbagliata")
elif utente != "---":
    auth = True

if auth:
    st.title(f"🗓️ Portale di {utente}")
    
    # --- CALENDARIO ---
    col1, col2 = st.columns(2)
    mese_nomi = list(calendar.month_name)[1:]
    m_sel = col1.selectbox("Mese", mese_nomi, index=datetime.now().month-1)
    a_sel = col2.number_input("Anno", 2024, 2026, 2024)
    m_idx = mese_nomi.index(m_sel) + 1

    with st.expander("👁️ Calendario Mensile", expanded=True):
        cal = calendar.Calendar(firstweekday=0)
        for settimana in cal.monthdatescalendar(a_sel, m_idx):
            cols = st.columns(7)
            for i, giorno in enumerate(settimana):
                with cols[i]:
                    bg = "#ffffff" if giorno.month == m_idx else "#f0f2f6"
                    st.markdown(f"<div style='border:1px solid #ddd;padding:5px;height:120px;background:{bg};overflow-y:auto;border-radius:5px;'><b>{giorno.day}</b>", unsafe_allow_html=True)
                    # Turni
                    for r in c.execute("SELECT dipendente, inizio FROM turni WHERE data=?", (str(giorno),)).fetchall():
                        st.markdown(f"<div style='background:{COLORI.get(r[0])};color:white;font-size:10px;padding:2px;margin-bottom:2px;border-radius:3px;'>{r[0][:1]}. {r[1][:5]}</div>", unsafe_allow_html=True)
                    # Ferie/Malattia
                    for r in c.execute("SELECT dipendente, tipo FROM ferie WHERE stato='Approvato' AND ? BETWEEN data_inizio AND data_fine", (str(giorno),)).fetchall():
                        st.markdown(f"<div style='background:{COLORI.get(r[1], '#000')};color:white;font-size:10px;padding:2px;margin-bottom:2px;border-radius:3px;'>🏖️ {r[0][:1]}.</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    # --- MENU AZIONI ---
    if utente == "Eleonora (Admin)":
        t1, t2, t3, t4 = st.tabs(["📝 Turni", "💼 Approvazioni", "📊 Ore", "🔔 Notifiche"])
        with t1:
            with st.form("new_t"):
                d = st.selectbox("Dipendente", DIP)
                g = st.date_input("Giorno")
                c1, c2 = st.columns(2)
                h1 = c1.time_input("Inizio", time(9,0))
                h2 = c2.time_input("Fine", time(18,0))
                if st.form_submit_button("Salva"):
                    c.execute("INSERT INTO turni (data, inizio, fine, dipendente) VALUES (?,?,?,?)", (str(g), str(h1), str(h2), d))
                    conn.commit(); st.success("Ok!"); st.rerun()
            id_canc = st.number_input("ID turno da cancellare", step=1, value=0)
            if st.button("🗑️ Cancella Turno"):
                c.execute("DELETE FROM turni WHERE id=?", (id_canc,))
                conn.commit(); st.rerun()
        with t2:
            reqs = c.execute("SELECT id, dipendente, tipo, data_inizio FROM ferie WHERE stato='In attesa'").fetchall()
            for r in reqs:
                st.write(f"ID {r[0]}: {r[1]} ({r[2]}) - {r[3]}")
                if st.button(f"Approva {r[0]}", key=f"f_{r[0]}"):
                    c.execute("UPDATE ferie SET stato='Approvato' WHERE id=?", (r[0],))
                    conn.commit(); st.rerun()
        with t3:
            df = pd.read_sql_query("SELECT * FROM timbrature", conn)
            st.dataframe(df)
        with t4:
            st.table(pd.read_sql_query("SELECT * FROM notifiche ORDER BY id DESC", conn))
    else:
        t1, t2 = st.tabs(["✍️ Timbra", "🏖️ Assenze"])
        with t1:
            if st.button("💾 Segna Inizio/Fine Lavoro"):
                c.execute("INSERT INTO timbrature (dipendente, data, inizio_effettivo) VALUES (?,?,?)", (utente, str(date.today()), datetime.now().strftime("%H:%M")))
                c.execute("INSERT INTO notifiche (messaggio, data_ora, letta) VALUES (?,?,0)", (f"{utente} timbrato", datetime.now().strftime("%H:%M")))
                conn.commit(); st.success("Registrato!")
        with t2:
            with st.form("ferie_f"):
                tipo = st.radio("Tipo", ["Ferie", "Malattia", "Permesso"])
                date_r = st.date_input("Giorni", [])
                if st.form_submit_button("Invia"):
                    if len(date_r)==2:
                        c.execute("INSERT INTO ferie (dipendente, data_inizio, data_fine, tipo, stato) VALUES (?,?,?,?,?)", (utente, str(date_r[0]), str(date_r[1]), tipo, "In attesa"))
                        conn.commit(); st.success("Inviata!")