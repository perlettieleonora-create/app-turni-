import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time, date, timedelta
import calendar

# --- DB E CONFIGURAZIONE ---
conn = sqlite3.connect('gestione_aziendale_finale.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute("CREATE TABLE IF NOT EXISTS turni (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, inizio TEXT, fine TEXT, dipendente TEXT, note TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS ferie (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data_inizio TEXT, data_fine TEXT, tipo TEXT, stato TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS timbrature (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data TEXT, inizio_effettivo TEXT, fine_effettivo TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS notifiche (id INTEGER PRIMARY KEY AUTOINCREMENT, messaggio TEXT, data_ora TEXT, letta INTEGER)")
    conn.commit()

init_db()

# --- CSS E COLORI ---
st.markdown("<style>.cal-box { border:1px solid #ddd; border-radius:5px; padding:3px; height:120px; overflow-y:auto; background:white; } .badge { font-size:9px; padding:2px; border-radius:3px; color:white; margin-bottom:1px; }</style>", unsafe_allow_html=True)
COLORI = {"Marco": "#3498db", "Francesco": "#2ecc71", "Martina": "#f39c12", "Suman": "#9b59b6", "Ferie": "#e74c3c", "Malattia": "#95a5a6"}
DIPENDENTI = ["Marco", "Francesco", "Martina", "Suman"]

# --- FUNZIONI ---
def invia_notifica(msg):
    c.execute("INSERT INTO notifiche (messaggio, data_ora, letta) VALUES (?,?,0)", (msg, datetime.now().strftime("%d/%m %H:%M")))
    conn.commit()

def check_conflitti(dip, giorno):
    c.execute("SELECT tipo FROM ferie WHERE dipendente=? AND stato='Approvato' AND ? BETWEEN data_inizio AND data_fine", (dip, giorno))
    return c.fetchone()

# --- LOGIN ---
st.sidebar.title("🔐 Login Sistema")
utente = st.sidebar.selectbox("Accedi come:", ["---", "Eleonora (Admin)"] + DIPENDENTI)

auth = False
if utente == "Eleonora (Admin)":
    if st.sidebar.text_input("Password Admin", type="password") == "admin123": auth = True
elif utente != "---": auth = True

if auth:
    # --- CALENDARIO MENSILE ---
    st.title(f"🗓️ Agenda Mensile - {utente}")
    
    col1, col2 = st.columns(2)
    m_nom = list(calendar.month_name)[1:]
    m_sel = col1.selectbox("Mese", m_nom, index=datetime.now().month-1)
    a_sel = col2.number_input("Anno", 2024, 2026, 2024)
    m_idx = m_nom.index(m_sel) + 1

    with st.expander("👁️ Visualizza Calendario", expanded=True):
        cal = calendar.Calendar(firstweekday=0)
        for settimana in cal.monthdatescalendar(a_sel, m_idx):
            cols = st.columns(7)
            for i, giorno in enumerate(settimana):
                with cols[i]:
                    bg = "#ffffff" if giorno.month == m_idx else "#f0f0f0"
                    st.markdown(f"<div class='cal-box' style='background:{bg}'><b>{giorno.day}</b>", unsafe_allow_html=True)
                    # Mostra Turni
                    for r in c.execute("SELECT dipendente, inizio FROM turni WHERE data=?", (str(giorno),)):
                        st.markdown(f"<div class='badge' style='background:{COLORI.get(r[0])}'>{r[0][:1]}. {r[1][:5]}</div>", unsafe_allow_html=True)
                    # Mostra Ferie/Malattia
                    for r in c.execute("SELECT dipendente, tipo FROM ferie WHERE stato='Approvato' AND ? BETWEEN data_inizio AND data_fine", (str(giorno),)):
                        color = COLORI["Ferie"] if r[1] == "Ferie" else COLORI["Malattia"]
                        st.markdown(f"<div class='badge' style='background:{color}'>{r[0][:1]}. {r[1][:1]}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    # --- AZIONI ADMIN ---
    if utente == "Eleonora (Admin)":
        t1, t2, t3, t4 = st.tabs(["📝 Gestione Turni", "💼 Approvazioni", "📊 Report Ore", "🔔 Notifiche"])
        
        with t1:
            st.subheader("Inserimento Turno")
            c1, c2 = st.columns(2)
            d_scelto = c1.selectbox("Dipendente", DIPENDENTI)
            g_scelto = c2.date_input("Data")
            
            # Controllo conflitti in tempo reale
            conflitto = check_conflitti(d_scelto, str(g_scelto))
            if conflitto: st.error(f"⚠️ Attenzione: {d_scelto} è in {conflitto[0]} in questa data!")

            h_i = c1.time_input("Dalle", time(9,0))
            h_f = c2.time_input("Alle", time(18,0))
            nota = st.text_input("Note")
            if st.button("Pubblica Turno", use_container_width=True):
                c.execute("INSERT INTO turni (data, inizio, fine, dipendente, note) VALUES (?,?,?,?,?)", (str(g_scelto), str(h_i), str(h_f), d_scelto, nota))
                conn.commit(); st.success("Turno Inserito!"); st.rerun()

        with t2:
            st.subheader("Richieste Pendenti")
            for r in c.execute("SELECT id, dipendente, tipo, data_inizio, data_fine FROM ferie WHERE stato='In attesa'").fetchall():
                st.info(f"{r[1]} chiede {r[2]} dal {r[3]} al {r[4]}")
                if st.button(f"Approva ID {r[0]}", key=f"app_{r[0]}"):
                    c.execute("UPDATE ferie SET stato='Approvato' WHERE id=?", (r[0],))
                    conn.commit(); st.rerun()

        with t3:
            st.subheader("Riepilogo Ore Mese")
            query = f"SELECT dipendente, inizio_effettivo, fine_effettivo, data FROM timbrature WHERE data LIKE '{a_sel}-{m_idx:02d}-%'"
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                st.dataframe(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica Report per Commercialista", csv, "report_ore.csv", "text/csv")
            else: st.warning("Nessuna timbratura registrata.")

        with t4:
            if st.button("Svuota Notifiche"): c.execute("DELETE FROM notifiche"); conn.commit(); st.rerun()
            st.write(pd.read_sql_query("SELECT data_ora, messaggio FROM notifiche ORDER BY id DESC", conn))

    # --- AZIONI DIPENDENTI ---
    else:
        t1, t2 = st.tabs(["✍️ Timbratura", "🏖️ Assenze"])
        with t1:
            st.subheader("Timbra Cartellino")
            c1, c2 = st.columns(2)
            ti = c1.time_input("Entrata")
            tf = c2.time_input("Uscita")
            if st.button("Salva Presenza", use_container_width=True):
                c.execute("INSERT INTO timbrature (dipendente, data, inizio_effettivo, fine_effettivo) VALUES (?,?,?,?)", (utente, str(date.today()), str(ti), str(tf)))
                invia_notifica(f"{utente} ha timbrato")
                conn.commit(); st.success("Registrato!")

        with t2:
            st.subheader("Richiesta Assenza")
            tipo = st.radio("Motivo:", ["Ferie", "Malattia", "Permesso"])
            dr = st.date_input("Seleziona date", [])
            if st.button("Invia Richiesta", use_container_width=True) and len(dr) == 2:
                c.execute("INSERT INTO ferie (dipendente, data_inizio, data_fine, tipo, stato) VALUES (?,?,?,?,?)", (utente, str(dr[0]), str(dr[1]), tipo, "In attesa"))
                invia_notifica(f"Nuova richiesta {tipo} da {utente}")
                conn.commit(); st.success("Inviata ad Eleonora!")
