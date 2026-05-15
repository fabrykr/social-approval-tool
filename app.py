import requests
import streamlit as st
import cloudinary
import cloudinary.uploader
import pandas as pd
from io import BytesIO
from pyairtable import Api

# --- Configurazione Pagina ---
st.set_page_config(
    page_title="Approvazione Post Social", 
    page_icon="📱", 
    layout="centered"
)

# --- Inizializzazione Servizi tramite st.secrets ---
cloudinary.config(
    cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key=st.secrets["CLOUDINARY_API_KEY"],
    api_secret=st.secrets["CLOUDINARY_API_SECRET"],
    secure=True
)

api = Api(st.secrets["AIRTABLE_API_KEY"])
table = api.table(
    st.secrets["AIRTABLE_BASE_ID"], 
    st.secrets["AIRTABLE_TABLE_NAME"]
)

# --- Funzioni di Servizio ---

def aggiorna_record(record_id, nuovi_dati):
    try:
        table.update(record_id, nuovi_dati)
        st.rerun()
    except Exception as e:
        st.error(f"Errore durante l'aggiornamento: {e}")

def invia_notifica_telegram(messaggio):
    token = st.secrets["TELEGRAM_BOT_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": messaggio, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            st.sidebar.success("Notifica inviata!")
        else:
            st.error(f"Errore Telegram: {response.text}")
    except Exception as e:
        st.error(f"Errore connessione Telegram: {e}")

def mostra_card(record, mostra_bottoni=False):
    fields = record.get("fields", {})
    record_id = record.get("id")
    
    nome_post = fields.get("nome_post", "Senza Nome")
    url_string = fields.get("url_foto", "")
    img_urls = url_string.split(",") if url_string else []
    descrizione = fields.get("descrizione", "")
    note = fields.get("note_revisione", "")
    
    with st.container():
        st.markdown(f"### 📌 {nome_post}")
        
        # --- Visualizzazione Immagini (Carosello con Tab) ---
        if img_urls:
            if len(img_urls) > 1:
                # Creiamo dei tab per scorrere le foto nello stesso spazio
                tabs = st.tabs([f"Foto {i+1}" for i in range(len(img_urls))])
                for i, tab in enumerate(tabs):
                    with tab:
                        st.image(img_urls[i], use_container_width=True)
            else:
                st.image(img_urls[0], use_container_width=True)
        
        st.info(f"**Caption:**\n\n{descrizione}")
        if note:
            st.warning(f"**💡 Accorgimenti:** {note}")
        
        if mostra_bottoni:
            col1, col2, col3 = st.columns(3)
            if col1.button("✅ Approva", key=f"app_{record_id}", use_container_width=True):
                aggiorna_record(record_id, {"stato": "Approvato"})
            if col2.button("❌ Boccia", key=f"boc_{record_id}", use_container_width=True):
                aggiorna_record(record_id, {"stato": "Bocciato"})
            with col3:
                with st.popover("📝 Modifica", use_container_width=True):
                    nuovo_nome = st.text_input("Nome Post", value=nome_post, key=f"ed_nom_{record_id}")
                    nuova_desc = st.text_area("Modifica Caption", value=descrizione, key=f"ed_cap_{record_id}")
                    nuove_note = st.text_area("Accorgimenti", value=note, key=f"ed_not_{record_id}")
                    if st.button("Salva", key=f"save_{record_id}"):
                        aggiorna_record(record_id, {
                            "nome_post": nuovo_nome,
                            "descrizione": nuova_desc, 
                            "note_revisione": nuove_note
                        })
        st.markdown("---")

# --- Sidebar: Inserimento ---
st.sidebar.header("📝 Nuovo Post")
with st.sidebar.form("upload_form", clear_on_submit=True):
    nome_input = st.text_input("Nome di riferimento del post (es. Lancio Prodotto)")
    uploaded_files = st.file_uploader("Foto (singola o carosello)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    caption = st.text_area("Caption")
    submit_button = st.form_submit_button("Carica in coda")

    if submit_button:
        if uploaded_files and caption.strip() and nome_input.strip():
            try:
                urls = []
                with st.spinner(f"Caricamento {len(uploaded_files)} immagini..."):
                    for file in uploaded_files:
                        res = cloudinary.uploader.upload(file)
                        urls.append(res.get("secure_url"))
                
                table.create({
                    "nome_post": nome_input,
                    "url_foto": ",".join(urls),
                    "descrizione": caption,
                    "stato": "In attesa"
                })
                st.success("✅ Post caricato!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("⚠️ Compila tutti i campi (Nome, Foto e Caption).")

# --- Sidebar: Report & Notifiche ---
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Report & Notifiche")

if st.sidebar.button("🔔 Avvisa il Cliente", use_container_width=True):
    attesa = [r for r in table.all() if r['fields'].get('stato') == "In attesa"]
    if attesa:
        testo = (
            f"🚀 <b>Nuovi post pronti!</b>\n\n"
            f"Ciao! Ho caricato <b>{len(attesa)} nuovi post</b> da revisionare.\n"
            f"👉 <a href='https://social-approval-tool-5gyxgx7scpm5iutbzn4zhz.streamlit.app/'>Apri l'App qui</a>"
        )
        invia_notifica_telegram(testo)
    else:
        st.sidebar.info("Nessun post in attesa.")

approvati_records = [r for r in table.all() if r['fields'].get('stato') == "Approvato"]
if approvati_records:
    data_report = [{
        "Nome Post": r['fields'].get("nome_post", "N/A"),
        "Data": r['fields'].get("data_creazione", "N/A"),
        "Caption": r['fields'].get("descrizione", ""),
        "Note": r['fields'].get("note_revisione", ""),
        "Tipo": "Carosello" if "," in str(r['fields'].get("url_foto", "")) else "Singolo"
    } for r in approvati_records]
    
    df = pd.DataFrame(data_report)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    st.sidebar.download_button(
        "📥 Scarica Report Approvati",
        data=output.getvalue(),
        file_name="report_approvati.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Svuota Approvati/Bocciati"):
    to_del = [r["id"] for r in table.all() if r["fields"].get("stato") in ["Approvato", "Bocciato"]]
    if to_del:
        table.batch_delete(to_del)
        st.rerun()

# --- Feed Principale ---
st.title("📱 Gestione Post")
tab_attesa, tab_approvati, tab_bocciati = st.tabs(["⏳ In attesa", "✅ Approvati", "❌ Bocciati"])

all_records = table.all()

with tab_attesa:
    attesa = [r for r in all_records if r['fields'].get('stato') == "In attesa"]
    for r in attesa: mostra_card(r, mostra_bottoni=True)

with tab_approvati:
    approvati = [r for r in all_records if r['fields'].get('stato') == "Approvato"]
    for r in approvati: mostra_card(r, mostra_bottoni=False)

with tab_bocciati:
    bocciati = [r for r in all_records if r['fields'].get('stato') == "Bocciato"]
    for r in bocciati: mostra_card(r, mostra_bottoni=False)
