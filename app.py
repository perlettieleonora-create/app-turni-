import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, time, date
import calendar

# --- CONNESSIONE GOOGLE ---
try:
    gc = gspread.service_account_from_dict(st.secrets["g_credentials"])
    sh = gc.open("DB_Gestionale_Turni")
    s_turni = sh.worksheet("turni")
    s_timb = sh.worksheet("timbrature")
    s_ferie = sh.worksheet("ferie")
    cloud_online = True
except Exception as e:
    cloud_online = False
    st.error(f"Errore di connessione a Google: {e}")

# --- CONFIGURAZIONE ---
COLORI = {"Marco": "#3498db", "Francesco": "#2ecc71", "Martina": "#f39c12", "Suman": "#9b59b6", "Ferie": "#e74c3c", "Malattia": "#95a5a6"}
DIP = ["Marco", "Francesco", "Martina", "Suman"]

st.set_page_config(page_title="Gestione Turni Cloud", layout="wide")

# --- LOGIN ---
st.sidebar.title("🔐 Login")
if cloud_online: st.sidebar.success("✅ Cloud Online")
else: st.sidebar.error("❌ Cloud Offline")

utente = st.sidebar.selectbox("Chi sei?", ["---", "Eleonora (Admin)"] + DIP)

auth = False
if utente == "Eleonora (Admin)":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == "admin123": auth = True
    elif pwd != "": st.sidebar.error("Sbagliata")
elif utente != "---": auth = True

if auth and cloud_online:
    st.title(f"🗓️ Portale di {utente}")
    
    # 1. VISUALIZZAZIONE CALENDARIO
    col1, col2 = st.columns(2)
    mese_nom = list(calendar.month_name)[1:]
    m_sel = col1.selectbox("Mese", mese_nom, index=datetime.now().month-1)
    a_sel = col2.number_input("Anno", 2024, 2026, 2024)
    m_idx = mese_nom.index(m_sel) + 1

    df_t = pd.DataFrame(s_turni.get_all_records())

    with st.expander("👁️ Vedi Calendario Completo", expanded=True):
        cal = calendar.Calendar(firstweekday=0)
        for settimana in cal.monthdatescalendar(a_sel, m_idx):
            cols = st.columns(7)
            for i, giorno in enumerate(settimana):
                with cols[i]:
                    bg = "#ffffff" if giorno.month == m_idx else "#f0f2f6"
                    st.markdown(f"<div style='border:1px solid #ddd;padding:5px;height:120px;background:{bg};border-radius:5px;'><b>{giorno.day}</b>", unsafe_allow_html=True)
                    if not df_t.empty and 'data' in df_t.columns:
                        g_t = df_t[df_t['data'] == str(giorno)]
                        for _, r in g_t.iterrows():
                            st.markdown(f"<div style='background:{COLORI.get(r['dipendente'])};color:white;font-size:10px;padding:2px;margin-bottom:2px;border-radius:3px;'>{r['dipendente'][:1]}. {r['inizio'][:5]}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # 2. AZIONI ADMIN
    if utente == "Eleonora (Admin)":
        t1, t2 = st.tabs(["📝 Inserisci Turno", "🕒 Timbrature"])
        with t1:
            with st.form("t"):
                d_s = st.selectbox("Dipendente", DIP)
                g_s = st.date_input("Giorno")
                h1 = st.time_input("Inizio", time(9,0))
                h2 = st.time_input("Fine", time(18,0))
                if st.form_submit_button("Salva nel Foglio Google"):
                    s_turni.append_row([str(datetime.now()), str(g_s), str(h1), str(h2), d_s, ""])
                    st.success("✅ Salvato nel Cloud!")
                    st.rerun()
        with t2:
            st.write("Registro Timbrature (da Google Sheets)")
            st.dataframe(pd.DataFrame(s_timb.get_all_records()))

    # 3. AZIONI DIPENDENTE
    else:
        st.subheader("Segna la tua presenza oggi")
        if st.button("🔴 Timbra Inizio/Fine", use_container_width=True):
            s_timb.append_row([str(datetime.now()), utente, str(date.today()), datetime.now().strftime("%H:%M"), ""])
            st.success("✅ Timbrata registrata nel Cloud!")
