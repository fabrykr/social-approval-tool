import streamlit as st
import cloudinary
import cloudinary.uploader
from pyairtable import Api

# --- Configurazione Pagina ---
st.set_page_config(
    page_title="Approvazione Post Social", 
    page_icon="📱", 
    layout="centered"
)

# --- Inizializzazione Servizi tramite st.secrets ---
# 1. Cloudinary
cloudinary.config(
    cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key=st.secrets["CLOUDINARY_API_KEY"],
    api_secret=st.secrets["CLOUDINARY_API_SECRET"],
    secure=True
)

# 2. Airtable
api = Api(st.secrets["AIRTABLE_API_KEY"])
table = api.table(
    st.secrets["AIRTABLE_BASE_ID"], 
    st.secrets["AIRTABLE_TABLE_NAME"]
)

# --- Funzioni di Supporto ---
def aggiorna_stato(record_id, nuovo_stato):
    """Aggiorna lo stato del record su Airtable e forza il ricaricamento della UI."""
    try:
        table.update(record_id, {"stato": nuovo_stato})
        st.rerun()
    except Exception as e:
        st.error(f"Si è verificato un errore durante l'aggiornamento: {e}")

# --- Sidebar: Caricamento Post ---
st.sidebar.header("📝 Inserimento Nuovo Post")
with st.sidebar.form("upload_form", clear_on_submit=True):
    uploaded_file = st.file_uploader("Carica l'immagine del post", type=["png", "jpg", "jpeg"])
    caption = st.text_area("Inserisci la caption")
    submit_button = st.form_submit_button("Invia per l'approvazione")

    if submit_button:
        if uploaded_file is not None and caption.strip() != "":
            try:
                with st.spinner("Caricamento immagine su Cloudinary in corso..."):
                    # Caricamento immagine (Cloudinary accetta file-like objects nativamente)
                    upload_result = cloudinary.uploader.upload(uploaded_file)
                    img_url = upload_result.get("secure_url")

                with st.spinner("Registrazione post sul database..."):
                    # Scrittura su Airtable
                    table.create({
                        "url_foto": img_url,
                        "descrizione": caption,
                        "stato": "In attesa"
                    })
                
                st.success("✅ Post inviato con successo!")
            except Exception as e:
                st.error(f"Errore durante il caricamento o salvataggio: {e}")
        else:
            st.warning("⚠️ Inserisci sia un'immagine che una caption prima di inviare.")

# --- Feed Principale: Post da Approvare ---
st.title("📱 Post in attesa di approvazione")

try:
    # Fetching solo dei record che necessitano di un'azione
    records = table.all(formula="{stato}='In attesa'")
except Exception as e:
    st.error(f"Errore di connessione al database Airtable: {e}")
    records = []

if not records:
    st.info("Tutto pulito! Nessun post in attesa di approvazione al momento. 🎉")
else:
    for record in records:
        # Estrazione dati Airtable
        fields = record.get("fields", {})
        record_id = record.get("id")
        
        img_url = fields.get("url_foto", "")
        descrizione = fields.get("descrizione", "")
        
        # UI Card per il Post
        with st.container():
            st.markdown("---")
            
            # Mostra Immagine
            if img_url:
                st.image(img_url, use_container_width=True)
                
            # Mostra Caption
            st.markdown(f"**Caption:**")
            st.info(descrizione)
            
            # Bottoni di Azione
            col1, col2 = st.columns(2)
            
            # Utilizziamo delle chiavi dinamiche per non far accavallare i bottoni
            if col1.button("✅ Approva", key=f"approva_{record_id}", use_container_width=True):
                aggiorna_stato(record_id, "Approvato")
                
            if col2.button("❌ Boccia", key=f"boccia_{record_id}", use_container_width=True):
                aggiorna_stato(record_id, "Bocciato")
