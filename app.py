import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time

# --- CONFIGURAZIONE DATABASE ---
conn = sqlite3.connect('gestione_avanzata.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS turni 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, inizio TEXT, fine TEXT, dipendente TEXT)''')
    # Aggiunta colonna STATO alle ferie
    c.execute('''CREATE TABLE IF NOT EXISTS ferie 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, dipendente TEXT, data_inizio TEXT, data_fine TEXT, stato TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS dipendenti (id INTEGER PRIMARY KEY, nome TEXT, ruolo TEXT)''')
    # Tabella Notifiche
    c.execute('''CREATE TABLE IF NOT EXISTS notifiche 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, messaggio TEXT, letta INTEGER, data_ora TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM dipendenti")
    if c.fetchone()[0] == 0:
        for nome, ruolo in [('Eleonora', 'Amministratore'), ('Marco', 'Dipendente'), 
                            ('Francesco', 'Dipendente'), ('Martina', 'Dipendente'), ('Suman', 'Dipendente')]:
            c.execute("INSERT INTO dipendenti (nome, ruolo) VALUES (?, ?)", (nome, ruolo))
        conn.commit()

init_db()

# --- FUNZIONI UTILI ---
def invia_notifica(msg):
    ora_attuale = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute("INSERT INTO notifiche (messaggio, letta, data_ora) VALUES (?, 0, ?)", (msg, ora_attuale))
    conn.commit()

def calcola_ore(inizio_str, fine_str):
    try:
        fmt = '%H:%M:%S'
        t1 = datetime.strptime(inizio_str, fmt)
        t2 = datetime.strptime(fine_str, fmt)
        return (t2 - t1).total_seconds() / 3600
    except: return 0

# --- INTERFACCIA ---
st.set_page_config(page_title="Gestione Turni & Notifiche", layout="wide")

st.sidebar.title("🔐 Login")
utente_attivo = st.sidebar.selectbox("Seleziona Utente", ["---", "Eleonora", "Marco", "Francesco", "Martina", "Suman"])

if utente_attivo == "---":
    st.title("Benvenuto/a nel Sistema Gestionale")
    st.info("Effettua il login per vedere i tuoi turni o richiedere ferie.")
else:
    c.execute("SELECT ruolo FROM dipendenti WHERE nome = ?", (utente_attivo,))
    ruolo = c.fetchone()[0]

    # --- BARRA NOTIFICHE PER ELEONORA ---
    if ruolo == "Amministratore":
        c.execute("SELECT COUNT(*) FROM notifiche WHERE letta = 0")
        num_notifiche = c.fetchone()[0]
        if num_notifiche > 0:
            st.sidebar.warning(f"🔔 Hai {num_notifiche} nuove notifiche!")

    st.title(f"Benvenuta/o, {utente_attivo}")

    # Definizione Tabs
    if ruolo == "Amministratore":
        tabs = st.tabs(["📊 Dashboard", "📅 Gestione Turni", "✅ Approvazione Ferie", "🔔 Notifiche", "📈 Report Ore"])
    else:
        tabs = st.tabs(["📅 I Miei Turni", "🏖️ Richiedi Ferie"])

    # --- LOGICA DIPENDENTE ---
    if ruolo == "Dipendente":
        with tabs[0]:
            st.subheader("I tuoi turni programmati")
            df = pd.read_sql_query(f"SELECT data, inizio, fine FROM turni WHERE dipendente='{utente_attivo}'", conn)
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            st.subheader("Stato tue richieste ferie")
            df_f = pd.read_sql_query(f"SELECT data_inizio, data_fine, stato FROM ferie WHERE dipendente='{utente_attivo}'", conn)
            st.table(df_f)

        with tabs[1]:
            st.subheader("Inserisci nuova richiesta ferie")
            date_range = st.date_input("Seleziona periodo", [])
            if st.button("Invia Richiesta"):
                if len(date_range) == 2:
                    c.execute("INSERT INTO ferie (dipendente, data_inizio, data_fine, stato) VALUES (?, ?, ?, ?)",
                              (utente_attivo, str(date_range[0]), str(date_range[1]), "In attesa"))
                    invia_notifica(f"Nuova richiesta ferie da parte di {utente_attivo}")
                    conn.commit()
                    st.success("Richiesta inviata ad Eleonora!")
                else:
                    st.error("Seleziona inizio e fine.")

    # --- LOGICA ADMIN (ELEONORA) ---
    else:
        # DASHBOARD
        with tabs[0]:
            st.subheader("Panoramica Turni Approvati")
            df_all = pd.read_sql_query("SELECT * FROM turni ORDER BY data DESC", conn)
            st.dataframe(df_all, use_container_width=True)

        # GESTIONE TURNI
        with tabs[1]:
            st.subheader("Assegna Turno")
            col1, col2, col3 = st.columns(3)
            dip = col1.selectbox("Dipendente", ["Marco", "Francesco", "Martina", "Suman"])
            giorno = col2.date_input("Giorno")
            inizio = col3.time_input("Inizio", time(9,0))
            fine = col3.time_input("Fine", time(18,0))
            if st.button("Pubblica Turno"):
                c.execute("INSERT INTO turni (data, inizio, fine, dipendente) VALUES (?,?,?,?)",
                          (str(giorno), str(inizio), str(fine), dip))
                conn.commit()
                st.success("Turno pubblicato!")

        # APPROVAZIONE FERIE
        with tabs[2]:
            st.subheader("Richieste Ferie in Attesa")
            df_attesa = pd.read_sql_query("SELECT * FROM ferie WHERE stato = 'In attesa'", conn)
            if not df_attesa.empty:
                for index, row in df_attesa.iterrows():
                    col1, col2, col3, col4 = st.columns([2,2,1,1])
                    col1.write(f"**{row['dipendente']}**")
                    col2.write(f"{row['data_inizio']} al {row['data_fine']}")
                    if col3.button("✅ Approva", key=f"app_{row['id']}"):
                        c.execute("UPDATE ferie SET stato = 'Approvato' WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.rerun()
                    if col4.button("❌ Rifiuta", key=f"rif_{row['id']}"):
                        c.execute("UPDATE ferie SET stato = 'Rifiutato' WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.rerun()
            else:
                st.info("Nessuna richiesta pendente.")

        # NOTIFICHE
        with tabs[3]:
            st.subheader("Centro Notifiche")
            if st.button("Segna tutte come lette"):
                c.execute("UPDATE notifiche SET letta = 1")
                conn.commit()
                st.rerun()
            
            notifiche = pd.read_sql_query("SELECT data_ora, messaggio, letta FROM notifiche ORDER BY id DESC", conn)
            for i, n in notifiche.iterrows():
                prefix = "🆕" if n['letta'] == 0 else "✅"
                st.write(f"{prefix} {n['data_ora']} - {n['messaggio']}")

        # REPORT ORE
        with tabs[4]:
            st.subheader("Totale Ore Lavorate")
            df_ore = pd.read_sql_query("SELECT inizio, fine, dipendente FROM turni", conn)
            if not df_ore.empty:
                df_ore['Ore'] = df_ore.apply(lambda x: calcola_ore(x['inizio'], x['fine']), axis=1)
                st.table(df_ore.groupby('dipendente')['Ore'].sum().reset_index())
