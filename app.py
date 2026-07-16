import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time, date, timedelta
import calendar

# --- CONFIGURAZIONE DATABASE ---
conn = sqlite3.connect('gestione_avanzata.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS turni 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, inizio TEXT, fine TEXT, dipendente TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ferie 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data_inizio TEXT, data_fine TEXT, stato TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS timbrature 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data TEXT, inizio_effettivo TEXT, fine_effettivo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS dipendenti (id INTEGER PRIMARY KEY, nome TEXT, ruolo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifiche 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, messaggio TEXT, letta INTEGER, data_ora TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM dipendenti")
    if c.fetchone()[0] == 0:
        dips = [('Eleonora', 'Amministratore'), ('Marco', 'Dipendente'), ('Francesco', 'Dipendente'), ('Martina', 'Dipendente'), ('Suman', 'Dipendente')]
        for n, r in dips:
            c.execute("INSERT INTO dipendenti (nome, ruolo) VALUES (?, ?)", (n, r))
        conn.commit()

init_db()

# --- COLORI E MAPPE ---
COLORI = {
    "Marco": "#3498db",      # Blu
    "Francesco": "#2ecc71",  # Verde
    "Martina": "#e67e22",    # Arancio
    "Suman": "#9b59b6",      # Viola
    "Ferie": "#e74c3c"       # Rosso
}

def get_colore_badge(nome, tipo="Turno"):
    if tipo == "Ferie": return COLORI["Ferie"]
    return COLORI.get(nome, "#7f8c8d")

# --- FUNZIONI ---
def invia_notifica(msg):
    c.execute("INSERT INTO notifiche (messaggio, letta, data_ora) VALUES (?, 0, ?)", (msg, datetime.now().strftime("%d/%m/%Y %H:%M")))
    conn.commit()

# --- INTERFACCIA ---
st.set_page_config(page_title="Calendario Turni PRO", layout="wide")

st.sidebar.title("🔐 Login")
utente_attivo = st.sidebar.selectbox("Seleziona Utente", ["---", "Eleonora", "Marco", "Francesco", "Martina", "Suman"])

if utente_attivo == "---":
    st.title("📅 Gestione Personale")
    st.info("Benvenuta Eleonora! Seleziona un utente per accedere.")
else:
    c.execute("SELECT ruolo FROM dipendenti WHERE nome = ?", (utente_attivo,))
    ruolo = c.fetchone()[0]

    # SEZIONE CALENDARIO MENSILE (Visibile a Tutti)
    st.title(f"🗓️ Calendario Mensile - {utente_attivo}")
    
    col_mese, col_anno = st.columns(2)
    mese_corrente = col_mese.selectbox("Mese", list(calendar.month_name)[1:], index=datetime.now().month-1)
    anno_corrente = col_anno.number_input("Anno", 2024, 2030, 2024)
    
    idx_mese = list(calendar.month_name).index(mese_corrente)
    cal = calendar.Calendar(firstweekday=0)
    giorni_mese = cal.monthdatescalendar(anno_corrente, idx_mese)

    # LEGENDA
    st.markdown("### Legenda")
    col_leg = st.columns(6)
    for i, (nome, col) in enumerate(COLORI.items()):
        col_leg[i].markdown(f"<div style='background-color:{col}; padding:5px; border-radius:5px; text-align:center; color:white; font-size:12px;'>{nome}</div>", unsafe_allow_html=True)
    
    st.write("")

    # COSTRUZIONE GRIGLIA CALENDARIO
    giorni_sett = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    cols_cal = st.columns(7)
    for i, g in enumerate(giorni_sett): cols_cal[i].write(f"**{g}**")

    for settimana in giorni_mese:
        cols = st.columns(7)
        for i, giorno in enumerate(settimana):
            with cols[i]:
                bg_color = "#f0f2f6" if giorno.month == idx_mese else "#ffffff"
                st.markdown(f"<div style='border:1px solid #ddd; padding:2px; height:100px; background-color:{bg_color}'><b>{giorno.day}</b>", unsafe_allow_html=True)
                
                # Cerca Turni del giorno
                df_t = pd.read_sql_query(f"SELECT dipendente, inizio, fine FROM turni WHERE data='{giorno}'", conn)
                for _, r in df_t.iterrows():
                    c_turno = get_colore_badge(r['dipendente'])
                    st.markdown(f"<div style='background-color:{c_turno}; color:white; font-size:10px; margin-top:2px; padding:2px; border-radius:3px;'>🕒 {r['dipendente']} ({r['inizio']}-{r['fine']})</div>", unsafe_allow_html=True)
                
                # Cerca Ferie Approvate
                query_f = f"SELECT dipendente FROM ferie WHERE stato='Approvato' AND '{giorno}' >= data_inizio AND '{giorno}' <= data_fine"
                df_f = pd.read_sql_query(query_f, conn)
                for _, r in df_f.iterrows():
                    st.markdown(f"<div style='background-color:{COLORI['Ferie']}; color:white; font-size:10px; margin-top:2px; padding:2px; border-radius:3px;'>🏖️ {r['dipendente']} (F)</div>", unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # --- MENU AZIONI ---
    if ruolo == "Dipendente":
        t1, t2 = st.tabs(["✍️ Timbra Presenza", "🏖️ Richiedi Ferie"])
        with t1:
            with st.form("timb"):
                ora_i = st.time_input("Inizio lavoro reale")
                ora_f = st.time_input("Fine lavoro reale")
                if st.form_submit_button("Invia Timbratura"):
                    c.execute("INSERT INTO timbrature (dipendente, data, inizio_effettivo, fine_effettivo) VALUES (?,?,?,?)", (utente_attivo, str(date.today()), str(ora_i), str(ora_f)))
                    invia_notifica(f"Timbratura da {utente_attivo}")
                    conn.commit()
                    st.success("Salvato!")
        with t2:
            dr = st.date_input("Periodo Ferie", [])
            if st.button("Richiedi"):
                if len(dr)==2:
                    c.execute("INSERT INTO ferie (dipendente, data_inizio, data_fine, stato) VALUES (?,?,?,?)", (utente_attivo, str(dr[0]), str(dr[1]), "In attesa"))
                    invia_notifica(f"Richiesta ferie: {utente_attivo}")
                    conn.commit()
                    st.success("Richiesta inviata!")

    else: # ELEONORA ADMIN
        t1, t2, t3, t4 = st.tabs(["➕ Crea Turno", "✅ Approvazioni", "🕒 Log Timbrature", "📢 Notifiche"])
        
        with t1:
            col_a, col_b, col_c = st.columns(3)
            d_scelto = col_a.selectbox("Dipendente", ["Marco", "Francesco", "Martina", "Suman"])
            g_scelto = col_b.date_input("Data Turno")
            h_i = col_c.time_input("Ora Inizio")
            h_f = col_c.time_input("Ora Fine")
            if st.button("Crea Turno"):
                c.execute("INSERT INTO turni (data, inizio, fine, dipendente) VALUES (?,?,?,?)", (str(g_scelto), str(h_i), str(h_f), d_scelto))
                conn.commit()
                st.success("Turno aggiunto a calendario!")

        with t2:
            df_ferie = pd.read_sql_query("SELECT * FROM ferie WHERE stato = 'In attesa'", conn)
            for _, r in df_ferie.iterrows():
                st.write(f"**{r['dipendente']}**: dal {r['data_inizio']} al {r['data_fine']}")
                c1, c2 = st.columns(2)
                if c1.button(f"Approva {r['id']}"):
                    c.execute("UPDATE ferie SET stato='Approvato' WHERE id=?", (r['id'],))
                    conn.commit(); st.rerun()
                if c2.button(f"Rifiuta {r['id']}"):
                    c.execute("UPDATE ferie SET stato='Rifiutato' WHERE id=?", (r['id'],))
                    conn.commit(); st.rerun()

        with t3:
            st.write("Dati effettivi lavorati oggi")
            st.dataframe(pd.read_sql_query("SELECT * FROM timbrature", conn))

        with t4:
            if st.button("Pulisci Notifiche"): c.execute("DELETE FROM notifiche"); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM notifiche ORDER BY id DESC", conn))