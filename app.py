import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, time, date
import calendar

# --- TENTA CONNESSIONE GOOGLE SHEETS ---
cloud_mode = False
try:
    if "g_credentials" in st.secrets:
        gc = gspread.service_account_from_dict(st.secrets["g_credentials"])
        # Cerca di aprire il foglio
        try:
            sh = gc.open("DB_Gestionale_Turni")
            s_turni = sh.worksheet("turni")
            s_ferie = sh.worksheet("ferie")
            s_timb = sh.worksheet("timbrature")
            cloud_mode = True
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ ERRORE: Foglio 'DB_Gestionale_Turni' non trovato su Google Drive!")
        except gspread.exceptions.WorksheetNotFound:
            st.error("❌ ERRORE: Controlla le linguette in basso (turni, ferie, timbrature)!")
        except Exception as e:
            st.error(f"❌ ERRORE CONDIVISIONE: Hai aggiunto l'email dell'account di servizio agli editor del foglio? Errore: {e}")
    else:
        st.error("❌ ERRORE: I 'Secrets' (g_credentials) non sono stati configurati su Streamlit!")
except Exception as e:
    st.error(f"❌ ERRORE CHIAVI JSON: Formato dei Secrets non valido! {e}")

# ... (Il resto del codice rimane uguale)