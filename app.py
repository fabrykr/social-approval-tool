import requests
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

def aggiorna_record(record_id, nuovi_dati):
    """Aggiorna i campi del record su Airtable."""
    try:
        table.update(record_id, nuovi_dati)
        st.rerun()
    except Exception as e:
        st.error(f"Errore durante l'aggiornamento: {e}")

def invia_notifica_telegram(messaggio):
    """Invia un messaggio al gruppo Telegram tramite Bot."""
    token = st.secrets["TELEGRAM_BOT_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": messaggio, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        st.error(f"Errore invio notifica: {e}")

# --- Sidebar: Caricamento Post ---
st.sidebar.header("📝 Inserimento Nuovo Post")
with st.sidebar.form("upload_form", clear_on_submit=True):
    uploaded_file = st.file_uploader("Carica l'immagine del post", type=["png", "jpg", "jpeg"])
    caption = st.text_area("Inserisci la caption")
    submit_button = st.form_submit_button("Invia per l'approvazione")

    if submit_button:
        if uploaded_file is not None and caption.strip() != "":
            try:
                with st.spinner("Caricamento immagine..."):
                    upload_result = cloudinary.uploader.upload(uploaded_file)
                    img_url = upload_result.get("secure_url")

                with st.spinner("Salvataggio..."):
                    table.create({
                        "url_foto": img_url,
                        "descrizione": caption,
                        "stato": "In attesa"
                    })
                
                st.success("✅ Post caricato correttamente!") # Niente notifica qui
                
            except Exception as e:
                st.error(f"Errore: {e}")


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

# --- Bottone per Notifica Manuale ---
st.sidebar.markdown("---")
st.sidebar.subheader("📢 Notifiche")

if st.sidebar.button("🔔 Avvisa il Cliente", use_container_width=True):
    # Conta quanti post sono in attesa per dare un'info precisa
    post_in_attesa = [r for r in table.all() if r['fields'].get('stato') == "In attesa"]
    quantita = len(post_in_attesa)
    
    if quantita > 0:
        testo_notifica = f"ir_bot 🚀 *Nuovi post pronti!*\n\nCiao! Ho caricato *{quantita} nuovi post* nell'app. Quando hai un attimo puoi revisionarli?\n\n🔗 [Apri l'App](https://tua-app.streamlit.app)"
        invia_notifica_telegram(testo_notifica)
        st.sidebar.success(f"Notifica inviata per {quantita} post!")
    else:
        st.sidebar.info("Non ci sono post in attesa di approvazione.")

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

def mostra_card(record, mostra_bottoni=False):
    fields = record.get("fields", {})
    record_id = record.get("id")
    img_url = fields.get("url_foto", "")
    descrizione = fields.get("descrizione", "")
    note = fields.get("note_revisione", "")
    
    with st.container():
        st.markdown("---")
        if img_url:
            st.image(img_url, use_container_width=True)
        
        # Visualizzazione Caption e Note
        st.info(f"**Caption:**\n\n{descrizione}")
        if note:
            st.warning(f"**💡 Accorgimenti:** {note}")
        
        if mostra_bottoni:
            col1, col2, col3 = st.columns(3)
            
            if col1.button("✅ Approva", key=f"app_{record_id}", use_container_width=True):
                aggiorna_record(record_id, {"stato": "Approvato"})
            
            if col2.button("❌ Boccia", key=f"boc_{record_id}", use_container_width=True):
                aggiorna_record(record_id, {"stato": "Bocciato"})
            
            # NUOVO: Bottone per Modifica e Commenti (usa uno st.expander o st.popover)
            with col3:
                with st.popover("📝 Modifica", use_container_width=True):
                    nuova_desc = st.text_area("Modifica Caption", value=descrizione, key=f"edit_desc_{record_id}")
                    nuove_note = st.text_area("Aggiungi Accorgimenti", value=note, key=f"edit_note_{record_id}")
                    if st.button("Salva Modifiche", key=f"save_{record_id}"):
                        aggiorna_record(record_id, {
                            "descrizione": nuova_desc,
                            "note_revisione": nuove_note
                        })

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
