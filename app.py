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

# --- Bottone per Svuotare l'Archivio ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Manutenzione")

if st.sidebar.button("🗑️ Svuota Approvati e Bocciati"):
    try:
        # Recupera tutti i record che NON sono "In attesa"
        records_da_eliminare = [
            r["id"] for r in table.all() 
            if r["fields"].get("stato") in ["Approvato", "Bocciato"]
        ]
        
        if records_da_eliminare:
            with st.spinner(f"Eliminazione di {len(records_da_eliminare)} post..."):
                table.batch_delete(records_da_eliminare)
            st.sidebar.success("Archivio svuotato!")
            st.rerun()
        else:
            st.sidebar.info("L'archivio è già vuoto.")
    except Exception as e:
        st.sidebar.error(f"Errore durante la pulizia: {e}")

# --- Feed Principale con Tab ---
st.title("📱 Gestione Post")

# Creiamo 3 Tab per categorizzare i post
tab_attesa, tab_approvati, tab_bocciati = st.tabs([
    "⏳ In attesa", 
    "✅ Approvati", 
    "❌ Bocciati"
])

# Recuperiamo TUTTI i record per popolare i tab
try:
    all_records = table.all()
except Exception as e:
    st.error(f"Errore di connessione: {e}")
    all_records = []

# Funzione interna per disegnare la card del post
def mostra_card(record, mostra_bottoni=False):
    fields = record.get("fields", {})
    record_id = record.get("id")
    img_url = fields.get("url_foto", "")
    descrizione = fields.get("descrizione", "")
    
    with st.container():
        st.markdown("---")
        if img_url:
            st.image(img_url, use_container_width=True)
        st.info(descrizione)
        
        if mostra_bottoni:
            col1, col2 = st.columns(2)
            if col1.button("✅ Approva", key=f"app_{record_id}", use_container_width=True):
                aggiorna_stato(record_id, "Approvato")
            if col2.button("❌ Boccia", key=f"boc_{record_id}", use_container_width=True):
                aggiorna_stato(record_id, "Bocciato")

# --- LOGICA DEI TAB ---

with tab_attesa:
    attesa = [r for r in all_records if r['fields'].get('stato') == "In attesa"]
    if not attesa:
        st.write("Nessun post da revisionare.")
    for r in attesa:
        mostra_card(r, mostra_bottoni=True)

with tab_approvati:
    approvati = [r for r in all_records if r['fields'].get('stato') == "Approvato"]
    if not approvati:
        st.write("Ancora nessun post approvato.")
    for r in approvati:
        mostra_card(r, mostra_bottoni=False)

with tab_bocciati:
    bocciati = [r for r in all_records if r['fields'].get('stato') == "Bocciato"]
    if not bocciati:
        st.write("Nessun post bocciato.")
    for r in bocciati:
        mostra_card(r, mostra_bottoni=False)
