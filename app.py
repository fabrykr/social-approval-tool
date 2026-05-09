import streamlit as st
import cloudinary
import cloudinary.uploader
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURAZIONE SICURA ---
# Ora il codice non contiene più i tuoi segreti!
cloudinary.config( 
  cloud_name = st.secrets["CLOUD_NAME"], 
  api_key = st.secrets["API_KEY"], 
  api_secret = st.secrets["API_SECRET"],
  secure = True
)
URL_FOGLIO = st.secrets["URL_FOGLIO"]

st.set_page_config(page_title="Tool Approvazione", layout="centered")

# --- CONNESSIONE AL DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Funzione per caricare i dati dal foglio
def load_data():
    return conn.read(spreadsheet=URL_FOGLIO, usecols=[0,1,2])

# Proviamo a caricare i dati esistenti
try:
    df = load_data()
except:
    # Se il foglio è vuoto, creiamo una tabella base
    df = pd.DataFrame(columns=["url_foto", "descrizione", "stato"])

# --- SIDEBAR PER CARICARE ---
with st.sidebar:
    st.header("Nuovo Post")
    file = st.file_uploader("Scegli immagine", type=['jpg', 'png', 'jpeg'])
    desc = st.text_area("Scrivi la caption")
    
    if st.button("Invia al Feed"):
        if file and desc:
            with st.spinner("Caricamento in corso..."):
                # 1. Carica su Cloudinary
                res = cloudinary.uploader.upload(file)
                img_url = res['secure_url']
                
                # 2. Aggiorna il Foglio Google
                new_row = pd.DataFrame([{"url_foto": img_url, "descrizione": desc, "stato": "In attesa"}])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=URL_FOGLIO, data=df)
                st.success("Inviato con successo!")
                st.rerun()

# --- FEED PRINCIPALE ---
st.title("Feed Revisione Instagram")

if df.empty:
    st.write("Non ci sono ancora post da revisionare.")
else:
    # Mostriamo i post dal più recente al più vecchio
    for index, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            st.image(row['url_foto'], use_container_width=True)
            st.markdown(f"**Caption:** {row['descrizione']}")
            st.info(f"Stato: {row['stato']}")
            
            c1, c2 = st.columns(2)
            if c1.button("✅ Approva", key=f"ok_{index}"):
                df.at[index, 'stato'] = "APPROVATO"
                conn.update(spreadsheet=URL_FOGLIO, data=df)
                st.rerun()
            if c2.button("❌ Boccia", key=f"no_{index}"):
                df.at[index, 'stato'] = "BOCCIATO"
                conn.update(spreadsheet=URL_FOGLIO, data=df)
                st.rerun()
