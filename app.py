import streamlit as st
import random
import json
import time
import os
from google import genai
from google.genai import types

# --- CONFIGURAZIONE INTERFACCIA E STILE CSS ---
st.set_page_config(page_title="⚽ Lobby Impostori", page_icon="⚽", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    .campo-calcio {
        background-color: #1b4314;
        background-image: 
            radial-gradient(circle at 50% 50%, transparent 0%, transparent 20%, rgba(255,255,255,0.15) 20%, rgba(255,255,255,0.15) 21%, transparent 21%),
            linear-gradient(to right, rgba(255,255,255,0.1) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255,255,255,0.1) 1px, transparent 1px);
        background-size: 100% 100%, 50px 50px, 50px 50px;
        border: 4px solid #ffffff;
        border-radius: 20px;
        padding: 30px;
        box-shadow: inset 0 0 30px rgba(0,0,0,0.6);
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    .box-scelta {
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    .scelta-vivo { border: 3px solid #3b82f6; background-color: #161b22; }
    .scelta-remoto { border: 3px solid #ef4444; background-color: #161b22; }
    
    .card-fedele-default {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 25px; border-radius: 15px; border: 3px solid #00ffcc;
        text-align: center; box-shadow: 0px 4px 15px rgba(0, 255, 204, 0.3);
        margin-top: 15px;
    }
    .card-impostore-default {
        background: linear-gradient(135deg, #3a0d0d 0%, #6b1111 100%);
        padding: 25px; border-radius: 15px; border: 3px solid #ff3333;
        text-align: center; box-shadow: 0px 4px 15px rgba(255, 51, 51, 0.3);
        margin-top: 15px;
    }
    
    div.stButton > button {
        width: 100%; background-color: #1f293d; color: #ffffff;
        border: 2px solid #3b82f6; border-radius: 12px; padding: 14px;
        font-weight: bold; font-size: 16px; transition: all 0.3s ease;
    }
    div.stButton > button:hover { background-color: #3b82f6; border-color: #00ffcc; transform: scale(1.02); }
    .lobby-box { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px dashed #30363d; margin-bottom: 15px; }
    
    .chat-box { background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 15px; max-height: 300px; overflow-y: auto; }
    .msg-line { margin-bottom: 8px; font-size: 15px; padding: 6px 10px; border-radius: 6px; }
    .msg-g1 { background-color: #21262d; border-left: 4px solid #58a6ff; }
    .msg-g2 { background-color: #1f242c; border-left: 4px solid #bc8cff; }
    </style>
""", unsafe_allow_html=True)

# --- FUNZIONI DI PERSISTENZA FILE PER CALCIATORI VIETATI ---
NOME_FILE_MEMORIA = "STORICO_CALCIATORI.json"

def carica_calciatori_salvati():
    """Legge la lista dei vecchi giocatori dal file locale del server se esiste."""
    if os.path.exists(NOME_FILE_MEMORIA):
        try:
            with open(NOME_FILE_MEMORIA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salva_calciatori_su_file(lista_calciatori):
    """Salva fisicamente la lista sul server per non perderla ai riavvii."""
    try:
        with open(NOME_FILE_MEMORIA, "w", encoding="utf-8") as f:
            json.dump(lista_calciatori, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# --- MEMORIA GLOBALE CONDIVISA (SERVER-SIDE) ---
@st.cache_resource
def ottieni_memoria_condivisa():
    return {
        "giocatori_connessi": [],
        "partita_in_corso": False,
        "modalita_scelta": None,  # "VIVO" o "REMOTO"
        "assegnazioni": {},
        "calciatore_segreto": None,
        "ultimi_calciatori": carica_calciatori_salvati(), # Recupera lo storico reale salvato!
        
        # Variabili esclusive per il Remoto
        "pronti_remoto": [],
        "ordine_turni": [],
        "indice_turno_attuale": 0,
        "numero_giro_attuale": 1,
        "chat_parole": [],  
        "voti_espressi": {},  
        "scelte_bivio": {},  
        "fase_remoto": "PRESA_VISIONE",  
        "eliminati": [],
        "risultato_voto_pubblico": "",
        "vincitore_partita": None,  
        "tentativo_impostore_indovinato": None
    }

stato_globale = ottieni_memoria_condivisa()

# --- CONFIGURAZIONE CLIENT GEMINI SICURA ---
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
else:
    try:
        client = genai.Client()
    except Exception:
        st.warning("⚠️ Configura la chiave API di Gemini nei Secrets di Streamlit.")

# --- FUNZIONE GENERAZIONE CALCIATORE CON GEMINI (CON CODA PERSISTENTE A 300 ELEMENTI E INSTRUCTIONS AGGIORNATE) ---
def genera_calciatore_con_ia():
    modello_stabile = "gemini-2.5-flash"
    
    lettere = ["A", "B", "C", "D", "E", "F", "G", "I", "L", "M", "N", "O", "P", "R", "S", "T", "V", "Z"]
    ruoli = ["Attaccante", "Centrocampista", "Difensore", "Portiere", "Leggenda del calcio"]
    
    lettera_scelta = random.choice(lettere)
    ruolo_scelto = random.choice(ruoli)
    seed_casuale = random.randint(1, 999999)
    timestamp_unico = int(time.time() * 1000)
    
    # Estrazione casuale dei dadi con Python per forzare la massima varietà ed evitare la pigrizia dell'IA
    tipo_id = random.randint(1, 4)
    tipo_aneddoto = random.randint(1, 5)
    
    tracce_identita = {
        1: "FOCALIZZATI SU: Il NOME E COGNOME di un allenatore importante che lo ha allenato storicamente.",
        2: "FOCALIZZATI SU: Un monumento, un simbolo, un animale dello stemma della squadra storica in cui ha giocato.",
        3: "FOCALIZZATI SU: Un trofeo di squadra di altissimo livello unico o un record collettivo (es. se ha vinto il Triplete scrivi 'Triplete', oppure 'Champions', 'Scudetto', ecc.).",
        4: "FOCALIZZATI SU: La Nazione di nascita. ATTENZIONE: Se la nazione ha pochissimi calciatori famosi (es. Macedonia, Giordania), NON nominarla, ma usa associazioni mentali o la capitale (es. Macedonia -> 'Frutta', Giordania -> 'Amman'). Usala direttamente (es. 'Argentina') solo se ha tantissimi campioni."
    }
    
    tracce_aneddoto = {
        1: "FOCALIZZATI SU: Una sua caratteristica estetica o fisica iconica (es. Rasta, Cresta, Occhiali, Cicatrice, Gigante, Pelato, Mancino, ecc.).",
        2: "FOCALIZZATI SU: Un aneddoto ironico, una rima fonetica o un'onomatopea del suo celebre soprannome (es. Belotti -> 'Chicchirichì').",
        3: "FOCALIZZATI SU: Il suo anno di nascita esatto.",
        4: "FOCALIZZATI SU: Un titolo individuale importante vinto nella sua carriera (es. Scarpa d'oro, Pallone d'oro, Capocannoniere, MVP, Copa America, Mondiale).",
        5: "FOCALIZZATI SU: Una parola secca sul suo ruolo o stile di gioco."
    }
    
    traccia_id_scelta = tracce_identita[tipo_id]
    traccia_aneddoto_scelta = tracce_aneddoto[tipo_aneddoto]
    
    # Recuperiamo la memoria storica dal nostro archivio reale
    vietati_stringa = ", ".join(stato_globale['ultimi_calciatori']) if stato_globale['ultimi_calciatori'] else "Nessuno"
    
    prompt_scelta = f"""
    Scegli il nome di un calciatore famoso mondiale, attuale o una leggenda del passato. Principalmente scegliendo tra giocatori che hanno giocato almeno una 
    o più stagioni in Serie A, anche giocatori di Premier League, del Real Madrid, Barcellona o famosi in generale vanno bene.
 
    🚫 REGOLE DI ESCLUSIONE TOTALI (MAI SELEZIONARE QUESTI NOMI):
    È SEVERAMENTE VIETATO scegliere uno di questi calciatori già usciti nelle partite precedenti: [{vietati_stringa}].
    Inoltre non scegliere Cristiano Ronaldo o Lionel Messi. Sii originale, pesca nel passato o tra giocatori diversi!

    Rispondi SOLO con il nome e cognome, senza nient'altro. No punti, no frasi.
    ID casuale: {seed_casuale} - Timestamp: {timestamp_unico}
    """
    
    try:
        res_scelta = client.models.generate_content(model=modello_stabile, contents=prompt_scelta)
        calciatore_scelto = res_scelta.text.strip().replace(".", "")
    except Exception:
        calciatore_scelto = "Kylian Mbappé" 
        
    system_instruction = f"""
    Sei il motore di un gioco d'ingegno sui calciatori in lingua italiana. Il gioco è quello dell'impostore: tutti sanno il nome tranne due persone. Gli indizi devono essere originali, stimolanti e mai scontati.
    
    🔥 REGOLA CRUCIALI PER IL JSON (NON INVERTIRE MAI LE CHIAVI):
    - Nella chiave "nome" DEVI inserire ESCLUSIVAMENTE il nome del calciatore di questo turno, ovvero: {calciatore_scelto}. Non metterci allenatori o indizi!
    - Nella chiave "indizio_identita" metti l'indizio richiesto dalla Traccia 1.
    - Nella chiave "indizio_tecnico_aneddoto" metti l'indizio richiesto dalla Traccia 2.
    
    🚫 REGOLE DI SICUREZZA ASSOLUTE:
    - È SEVERAMENTE VIETATO includere il nome, il cognome, il soprannome storico testuale o parti del nome del calciatore {calciatore_scelto} dentro gli indizi.
    - Non usare i colori sociali letterali della maglia (es. no 'Rossonero', no 'Bianconero').
    - Sii STORICAMENTE PRECISO ed EVITA ASSOLUTAMENTE soprannomi o aneddoti appartenenti ad altri calciatori. L'indizio deve essere vero e verificabile solo per il calciatore corrente.
    
    🎯 DIRETTIVA DI GENERAZIONE MANDATORIA (LA TUA GUIDA PER QUESTO TURNO):
    Per evitare ripetizioni e garantire la massima imprevedibilità, per questo specifico turno DEVI attenerti a queste linee guida estratte dal sistema:
    1. Per 'indizio_identita': {traccia_id_scelta}
    2. Per 'indizio_tecnico_aneddoto': {traccia_aneddoto_scelta}
    
    ⚠️ NOTA DI SALVAGUARDIA: Se la traccia estratta non si applica al 100% alla storia reale e verificabile di {calciatore_scelto}, o se hai dubbi storici, NON INVENTARE. Ripiega immediatamente su un suo titolo vinto, sul suo anno di nascita reale o su un sinonimo originale del suo ruolo (es. 'Regista', 'Muro', 'Bomber').
    
    Rispondi ESCLUSIVAMENTE con un oggetto JSON con questa struttura precisa (compila i valori con 1-3 parole):
    {{
        "nome": "{calciatore_scelto}",
        "indizio_identita": "inserisci qui l'indizio basato sulla traccia 1",
        "indizio_tecnico_aneddoto": "inserisci qui l'indizio basato sulla traccia 2"
    }}
    
    REGOLE DI STILE: massimo 1-3 parole secche, no frasi, no parentesi. Sii criptico ma storicamente inattaccabile.
    """

    try:
        # Chiamata nativa Gemini forzata in JSON strutturato
        completion = client.models.generate_content(
            model=modello_stabile,
            contents=f"Genera l'oggetto JSON richiesto per il calciatore: {calciatore_scelto}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=1.0,
                response_mime_type="application/json"
            )
        )
        
        dati = json.loads(completion.text)
        nome = dati.get('nome', calciatore_scelto)
        indizio_id = dati.get('indizio_identita') or "Campione"
        indizio_tec = dati.get('indizio_tecnico_aneddoto') or "Fulmine"
        
        # Aggiorna la memoria in tempo reale aumentata a 300 elementi
        if nome not in stato_globale['ultimi_calciatori']:
            stato_globale['ultimi_calciatori'].append(nome)
        if len(stato_globale['ultimi_calciatori']) > 300:
            stato_globale['ultimi_calciatori'].pop(0)
            
        # BLINDATURA: Salva immediatamente la lista aggiornata su file locale
        salva_calciatori_su_file(stato_globale['ultimi_calciatori'])
            
        return {"nome": nome, "indizio_identita": indizio_id, "indizio_tecnico_aneddoto": indizio_tec}
    except Exception as e:
        return {"nome": calciatore_scelto, "indizio_identita": "Torre", "indizio_tecnico_aneddoto": "Velocità"}
# --- STATO LOCALE DISPOSITIVO ---
if 'mio_nome' not in st.session_state: st.session_state['mio_nome'] = None
if 'identita_bloccata' not in st.session_state: st.session_state['identita_bloccata'] = False

st.title("⚽ Il Gioco degli Impostori")

# --- FASE 1: LOBBY D'ATTESA ---
if not stato_globale["partita_in_corso"]:
    st.subheader("🎮 Fase 1: Entra nella Lobby")
    
    if not st.session_state['mio_nome']:
        nuovo_nome = st.text_input("Inserisci il tuo nome per partecipare:", key="input_nome_singolo").strip()
        if st.button("✅ Entra nella Stanza"):
            if nuovo_nome and nuovo_nome not in stato_globale["giocatori_connessi"]:
                stato_globale["giocatori_connessi"].append(nuovo_nome)
                st.session_state['mio_nome'] = nuovo_nome
                st.rerun()
            elif nuovo_nome in stato_globale["giocatori_connessi"]:
                st.error("Questo nome è già occupato nella stanza!")
    else:
        st.success(f"Sei dentro la stanza come: **{st.session_state['mio_nome']}**")
        if st.button("❌ Esci dalla Stanza"):
            if st.session_state['mio_nome'] in stato_globale["giocatori_connessi"]:
                stato_globale["giocatori_connessi"].remove(st.session_state['mio_nome'])
            st.session_state['mio_nome'] = None
            st.rerun()

    st.markdown("<div class='lobby-box'>", unsafe_allow_html=True)
    st.write(f"👥 **Giocatori pronti ({len(stato_globale['giocatori_connessi'])}):**")
    if stato_globale["giocatori_connessi"]: st.write(", ".join(stato_globale["giocatori_connessi"]))
    else: st.italic("In attesa che i giocatori si colleghino...")
    st.markdown("</div>", unsafe_allow_html=True)

    forza_due = True
    if len(stato_globale["giocatori_connessi"]) >= 6:
        forza_due = st.checkbox("⚽ Forza 2 Impostori per questo turno (consigliato)", value=True)

    if len(stato_globale["giocatori_connessi"]) >= 3:
        if st.button("🚀 AVVIA PARTITA PER TUTTI", type="primary"):
            with st.spinner("L'IA sta estraendo il calciatore misterioso..."):
                calciatore = genera_calciatore_con_ia()
                lista_amici = stato_globale["giocatori_connessi"].copy()
                random.shuffle(lista_amici)
                
                assegnazioni = {}
                imp_da_mettere = 2 if (len(lista_amici) >= 6 and forza_due) else 1
                
                if imp_da_mettere == 1:
                    ind_casuale = random.choice([calciatore['indizio_identita'], calciatore['indizio_tecnico_aneddoto']])
                    assegnazioni[lista_amici.pop()] = {"ruolo": "IMPOSTORE", "dettaglio": ind_casuale}
                else:
                    assegnazioni[lista_amici.pop()] = {"ruolo": "IMPOSTORE 1", "dettaglio": calciatore['indizio_identita']}
                    assegnazioni[lista_amici.pop()] = {"ruolo": "IMPOSTORE 2", "dettaglio": calciatore['indizio_tecnico_aneddoto']}
                
                for fedele in lista_amici:
                    assegnazioni[fedele] = {"ruolo": "FEDELE", "dettaglio": calciatore['nome']}
                
                # Setup stato remoto iniziale
                ordine_p = stato_globale["giocatori_connessi"].copy()
                random.shuffle(ordine_p)
                
                # Reset completo dello stato di gioco
                stato_globale["calciatore_segreto"] = calciatore
                stato_globale["assegnazioni"] = assegnazioni
                stato_globale["modalita_scelta"] = None  # Resetta la scelta iniziale
                st.session_state['identita_bloccata'] = False
                
                # Pulizia totale variabili remoto
                stato_globale["pronti_remoto"] = []
                stato_globale["ordine_turni"] = ordine_p
                stato_globale["indice_turno_attuale"] = 0
                stato_globale["numero_giro_attuale"] = 1
                stato_globale["chat_parole"] = []
                stato_globale["voti_espressi"] = {}
                stato_globale["scelte_bivio"] = {}
                stato_globale["fase_remoto"] = "PRESA_VISIONE"
                stato_globale["eliminati"] = []
                stato_globale["risultato_voto_pubblico"] = ""
                stato_globale["vincitore_partita"] = None
                stato_globale["tentativo_impostore_indovinato"] = None
                
                stato_globale["partita_in_corso"] = True
                st.rerun()
    else:
        st.info("Servono almeno 3 giocatori connessi per poter avviare la partita.")
        if st.button("🔄 Aggiorna Lista"): st.rerun()

# --- FASE 2: SELEZIONE MODALITÀ O MATCH CORRENTE ---
else:
    # Se il Master non ha ancora impostato una scelta globale per il tipo di partita
    if stato_globale["modalita_scelta"] is None:
        st.subheader("🏟️ Scegli la modalità per questa partita:")
        
        col_v, col_r = st.columns(2)
        with col_v:
            st.markdown("<div class='box-scelta scelta-vivo'><h3>📍 MODALITÀ DAL VIVO</h3></div>", unsafe_allow_html=True)
            if st.button("Seleziona la tua Card", key="btn_scegli_vivo"):
                stato_globale["modalita_scelta"] = "VIVO"
                st.rerun()
                
        with col_r:
            st.markdown("<div class='box-scelta scelta-remoto'><h3>🌐 MODALITÀ IN REMOTO</h3></div>", unsafe_allow_html=True)
            if st.button("Visualizza la tua Card", key="btn_scegli_remoto"):
                stato_globale["modalita_scelta"] = "REMOTO"
                st.rerun()
                
        if st.button("🔄 Aggiorna Schermata"): st.rerun()

    # ==================== A) FLUSSO DAL VIVO (INVARIATO) ====================
    elif stato_globale["modalita_scelta"] == "VIVO":
        if not st.session_state['identita_bloccata']:
            st.subheader("🏟️ Seleziona il tuo mattoncino sul campo!")
            nomi_disponibili = stato_globale["giocatori_connessi"]
            
            st.markdown("<div class='campo-calcio'>", unsafe_allow_html=True)
            for i in range(0, len(nomi_disponibili), 2):
                if i + 1 < len(nomi_disponibili):
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"🏃‍♂️ {nomi_disponibili[i]}", key=f"f2_{nomi_disponibili[i]}"):
                            st.session_state['mio_nome'] = nomi_disponibili[i]; st.session_state['identita_bloccata'] = True; st.rerun()
                    with col2:
                        if st.button(f"🏃‍♂️ {nomi_disponibili[i+1]}", key=f"f2_{nomi_disponibili[i+1]}"):
                            st.session_state['mio_nome'] = nomi_disponibili[i+1]; st.session_state['identita_bloccata'] = True; st.rerun()
                else:
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c2:
                        if st.button(f"🏃‍♂️ {nomi_disponibili[i]}", key=f"f2_{nomi_disponibili[i]}"):
                            st.session_state['mio_nome'] = nomi_disponibili[i]; st.session_state['identita_bloccata'] = True; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        else:
            mio_nome = st.session_state['mio_nome']
            mio_ruolo = stato_globale["assegnazioni"].get(mio_nome)
            
            if mio_ruolo:
                st.write(f"### 📱 Schermo bloccato su: **{mio_nome}**")
                if "IMPOSTORE" in mio_ruolo['ruolo']:
                    st.image("impostore.png", use_container_width=True)
                    st.markdown(f'<div class="card-impostore-default"><h2 style="color: #ff3333; margin: 0;">🕵️‍♂️ {mio_ruolo["ruolo"]}</h2><p style="font-size: 16px; margin-top: 10px; color: #ffcccc;">Il tuo indizio segreto è:</p><h1 style="color: #ffffff; font-size: 34px; margin: 5px 0;">{mio_ruolo["dettaglio"]}</h1><p style="font-size: 14px; color: #ffa3a3; font-style: italic;">Infiltrati, bluffa e non farti scoprire!</p></div>', unsafe_allow_html=True)
                else:
                    st.image("fedele.png", use_container_width=True)
                    st.markdown(f'<div class="card-fedele-default"><h2 style="color: #00ffcc; margin: 0;">🟩 FEDELE</h2><p style="font-size: 16px; margin-top: 10px; color: #ccfffa;">Il calciatore misterioso è:</p><h1 style="color: #ffffff; font-size: 34px; margin: 5px 0;">{mio_ruolo["dettaglio"]}</h1><p style="font-size: 14px; color: #a3fff2; font-style: italic;">Fai domande mirate per scovare gli impostori!</p></div>', unsafe_allow_html=True)
            
            st.write("---")
            if st.button("🛑 FINE PARTITA (Prossimo Giro)"):
                stato_globale["partita_in_corso"] = False
                st.rerun()

    # ==================== B) FLUSSO AUTOMATICO IN REMOTO ====================
    elif stato_globale["modalita_scelta"] == "REMOTO":
        mio_nome = st.session_state['mio_nome']
        
        if not mio_nome:
            st.warning("⚠️ Non risulti registrato in questa lobby. Attendi la fine del turno o inserisci il nome al prossimo giro.")
        else:
            mio_ruolo = stato_globale["assegnazioni"].get(mio_nome)
            fase = stato_globale["fase_remoto"]
            
            # --- SOTTO-FASE 1: PRESA VISIONE DELLA CARTA ---
            if fase == "PRESA_VISIONE":
                st.subheader("👁️ Guarda la tua identità segreta")
                if mio_ruolo:
                    if "IMPOSTORE" in mio_ruolo['ruolo']:
                        st.image("impostore.png", use_container_width=True)
                        st.markdown(f'<div class="card-impostore-default"><h2 style="color: #ff3333; margin: 0;">🕵️‍♂️ {mio_ruolo["ruolo"]}</h2><p style="font-size: 16px; margin-top: 10px; color: #ffcccc;">Il tuo indizio segreto è:</p><h1 style="color: #ffffff; font-size: 34px;">{mio_ruolo["dettaglio"]}</h1></div>', unsafe_allow_html=True)
                    else:
                        st.image("fedele.png", use_container_width=True)
                        st.markdown(f'<div class="card-fedele-default"><h2 style="color: #00ffcc; margin: 0;">🟩 FEDELE</h2><p style="font-size: 16px; margin-top: 10px; color: #ccfffa;">Il calciatore misterioso è:</p><h1 style="color: #ffffff; font-size: 34px;">{mio_ruolo["dettaglio"]}</h1></div>', unsafe_allow_html=True)
                
                st.write("---")
                if mio_nome not in stato_globale["pronti_remoto"]:
                    if st.button("🚀 Compreso! Entra in Campo", key="btn_pronto_rem"):
                        stato_globale["pronti_remoto"].append(mio_nome)
                        st.rerun()
                else:
                    st.success("Sei pronto! Attesa degli altri giocatori...")
                
                # Controllo sblocco fase di chat (se tutti i partecipanti registrati confermano)
                tutti_pronti = all(p in stato_globale["pronti_remoto"] for p in stato_globale["giocatori_connessi"])
                if tutti_pronti:
                    stato_globale["fase_remoto"] = "CHAT"
                    st.rerun()
                else:
                    st.caption(f"Pronti: {len(stato_globale['pronti_remoto'])} su {len(stato_globale['giocatori_connessi'])}")
                    if st.button("🔄 Aggiorna Stato"): st.rerun()

            # --- SOTTO-FASE 2: CHAT A TURNI IN TEMPO REALE ---
            elif fase == "CHAT":
                st.subheader(f"💬 Campo da Gioco - Giro {stato_globale['numero_giro_attuale']}")
                
                # Tabellone visualizzazione parole inserite
                st.markdown("<div class='chat-box'>", unsafe_allow_html=True)
                if stato_globale["chat_parole"]:
                    for item in stato_globale["chat_parole"]:
                        cls = "msg-g1" if item["giro"] == 1 else "msg-g2"
                        st.markdown(f'<div class="msg-line {cls}"><b>🏃‍♂️ {item["giocatore"]}</b> (Giro {item["giro"]}): <span style="font-size:17px; font-weight:bold;">{item["parola"]}</span></div>', unsafe_allow_html=True)
                else:
                    st.write("Il tabellone delle parole è vuoto. In attesa del primo giocatore...")
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Calcolo del turno attuale considerando solo chi non è eliminato
                ordine_attivi = [p for p in stato_globale["ordine_turni"] if p not in stato_globale["eliminati"]]
                idx = stato_globale["indice_turno_attuale"]
                
                if idx >= len(ordine_attivi):
                    # Finito il giro di parole di tutti
                    stato_globale["scelte_bivio"] = {} # Svuota scelte precedenti
                    stato_globale["fase_remoto"] = "BIVIO"
                    st.rerun()
                else:
                    giocatore_di_turno = ordine_attivi[idx]
                    st.info(f"👉 È il turno di: **{giocatore_di_turno}**")
                    
                    if mio_nome == giocatore_di_turno:
                        parola_inserita = st.text_input("Digita la tua parola singola per questo turno:", key=f"inp_par_{idx}").strip()
                        if st.button("✉️ Invia Parola"):
                            if parola_inserita:
                                stato_globale["chat_parole"].append({
                                    "giocatore": mio_nome,
                                    "parola": parola_inserita,
                                    "giro": stato_globale["numero_giro_attuale"]
                                })
                                stato_globale["indice_turno_attuale"] += 1
                                st.rerun()
                    else:
                        st.caption("Attendi che il giocatore di turno scriva la sua parola...")
                        if st.button("🔄 Aggiorna Tabellone"): st.rerun()

            # --- SOTTO-FASE 3: BIVIO DECISIONALE (GIRO 2 o VOTO) ---
            elif fase == "BIVIO":
                st.subheader("⚖️ Decisione Strategica: Cosa facciamo?")
                st.write("Scegli se procedere con la votazione dell'impostore o fare un ulteriore giro di parole.")
                
                if mio_nome not in stato_globale["scelte_bivio"]:
                    c_giro, c_voto = st.columns(2)
                    with c_giro:
                        if st.button("🔄 Fai un altro Giro"):
                            stato_globale["scelte_bivio"][mio_nome] = "GIRO"
                            st.rerun()
                    with c_voto:
                        if st.button("🗳️ Vai al Voto"):
                            stato_globale["scelte_bivio"][mio_nome] = "VOTO"
                            st.rerun()
                else:
                    st.success(f"Hai espresso la tua preferenza: **{stato_globale['scelte_bivio'][mio_nome]}**")
                
                vivi = [p for p in stato_globale["giocatori_connessi"] if p not in stato_globale["eliminati"]]
                tutti_votato_bivio = all(p in stato_globale["scelte_bivio"] for p in vivi)
                
                if tutti_votato_bivio:
                    conteggi = list(stato_globale["scelte_bivio"].values())
                    voti_giro = conteggi.count("GIRO")
                    voti_voto = conteggi.count("VOTO")
                    
                    # Logica: Vince chi ha più voti; in caso di parità si sceglie il nuovo giro
                    if voti_giro >= voti_voto:
                        stato_globale["numero_giro_attuale"] += 1
                        stato_globale["indice_turno_attuale"] = 0
                        stato_globale["fase_remoto"] = "CHAT"
                    else:
                        stato_globale["voti_espressi"] = {}
                        stato_globale["fase_remoto"] = "VOTAZIONE"
                    st.rerun()
                else:
                    st.caption(f"Preferenze raccolte: {len(stato_globale['scelte_bivio'])} su {len(vivi)}")
                    if st.button("🔄 Aggiorna Voti"): st.rerun()

            # --- SOTTO-FASE 4: VOTAZIONE SEGRETA ---
            elif fase == "VOTAZIONE":
                st.subheader("🗳️ Votazione Segreta dell'Impostore")
                vivi = [p for p in stato_globale["giocatori_connessi"] if p not in stato_globale["eliminati"]]
                
                if mio_nome in stato_globale["eliminati"]:
                    st.info("Sei stato eliminato, attendi la fine delle votazioni.")
                else:
                    if mio_nome not in stato_globale["voti_espressi"]:
                        opzioni_voto = [p for p in vivi if p != mio_nome]
                        scelta_voto = st.radio("Chi pensi che sia l'impostore?", opzioni_voto, key="radio_voto")
                        if st.button("🗳️ Conferma Voto"):
                            stato_globale["voti_espressi"][mio_nome] = scelta_voto
                            st.rerun()
                    else:
                        st.success(f"Hai votato per: **{stato_globale['voti_espressi'][mio_nome]}**")
                
                if len(stato_globale["voti_espressi"]) >= len(vivi):
                    # Calcolo del giocatore più votato
                    voti_ricevuti = {}
                    for bersaglio in stato_globale["voti_espressi"].values():
                        voti_ricevuti[bersaglio] = voti_ricevuti.get(bersaglio, 0) + 1
                    
                    piu_votato = max(voti_ricevuti, key=voti_ricevuti.get)
                    stato_globale["risultato_voto_pubblico"] = piu_votato
                    
                    # Determina ruoli attivi rimasti nella partita
                    ruolo_votato = stato_globale["assegnazioni"][piu_votato]["ruolo"]
                    tutti_impostori = [k for k, v in stato_globale["assegnazioni"].items() if "IMPOSTORE" in v["ruolo"]]
                    
                    if len(tutti_impostori) == 1:
                        # --- SCENARIO 1 IMPOSTORE ---
                        stato_globale["fase_remoto"] = "RIVELAZIONE"
                    else:
                        # --- SCENARIO 2 IMPOSTORI ---
                        if "IMPOSTORE" in ruolo_votato:
                            # Trovato uno dei due impostori! Fa subito il suo tentativo
                            stato_globale["fase_remoto"] = "RIVELAZIONE"
                        else:
                            # Eliminato un fedele con due impostori ancora in gioco
                            stato_globale["eliminati"].append(piu_votato)
                            fedeli_vivi = [k for k, v in stato_globale["assegnazioni"].items() if "FEDELE" in v["ruolo"] and k not in stato_globale["eliminati"]]
                            imp_vivi = [k for k, v in stato_globale["assegnazioni"].items() if "IMPOSTORE" in v["ruolo"] and k not in stato_globale["eliminati"]]
                            
                            if len(fedele_vivi) <= 1:
                                # Rimane solo 1 fedele contro 2 impostori -> Vittoria automatica Impostori
                                stato_globale["vincitore_partita"] = "IMPOSTORI"
                                stato_globale["fase_remoto"] = "RIVELAZIONE"
                            else:
                                # La partita continua, si pulisce il bivio e si fa un nuovo giro
                                stato_globale["scelte_bivio"] = {}
                                stato_globale["indice_turno_attuale"] = 0
                                stato_globale["fase_remoto"] = "CHAT"
                    st.rerun()
                else:
                    if st.button("🔄 Aggiorna Scrutinio"): st.rerun()

            # --- SOTTO-FASE 5: RIVELAZIONE E TENTATIVO IMPOSTORE ---
            elif fase == "RIVELAZIONE":
                st.subheader("🚨 Resoconto dello Scrutinio Pubblico")
                piu_votato = stato_globale["risultato_voto_pubblico"]
                ruolo_votato = stato_globale["assegnazioni"][piu_votato]["ruolo"]
                tutti_impostori = [k for k, v in stato_globale["assegnazioni"].items() if "IMPOSTORE" in v["ruolo"]]
                
                # Controllo se è lo scenario finale automatico per sovrannumero impostori
                if stato_globale["vincitore_partita"] == "IMPOSTORI" and len(tutti_impostori) == 2:
                    st.error(f"Il villaggio ha eliminato troppi fedeli. Rimane un solo fedele contro due impostori: gli IMPOSTORI hanno vinto per superiorità numerica!")
                    st.image("impostore.png", use_container_width=True)
                    
                    st.write("---")
                    if st.button("🛑 RESETTA LOBBY (Nuovo Turno)"):
                        stato_globale["partita_in_corso"] = False
                        st.rerun()
                    st.stop()

                # LOGICA RIVELAZIONE STANDARD
                if "IMPOSTORE" in ruolo_votato:
                    st.warning(f"🎯 Il villaggio ha votato correttamente: **{piu_votato}** era l'IMPOSTORE!")
                    impostore_di_turno = piu_votato
                else:
                    st.error(f"❌ Il villaggio ha sbagliato: **{piu_votato}** è un FEDELE! La caccia è finita.")
                    # Rivela pubblicamente chi era il vero impostore (Prende il primo in partita singola)
                    vero_impostore = [k for k, v in stato_globale["assegnazioni"].items() if "IMPOSTORE" in v["ruolo"]][0]
                    st.info(f"🕵️‍♂️ Il VERO Impostore nascosto era: **{vero_impostore}**")
                    impostore_di_turno = vero_impostore

                st.write("---")
                st.write(f"🤔 Adesso l'impostore (**{impostore_di_turno}**) sta scrivendo la sua risposta sul suo telefono per provare ad indovinare il calciatore misterioso...")
                
                if mio_nome == impostore_di_turno:
                    st.markdown("### 🤫 Campo segreto dell'Impostore")
                    st.write("I Fedeli ti hanno scoperto o la partita si è conclusa! Hai un'ultima possibilità per rubare la coppa: indovina il calciatore misterioso.")
                    tentativo = st.text_input("Scrivi NOME E COGNOME del calciatore:", key="input_impostore_final").strip()
                    
                    if st.button("🏆 Invia Risposta Finale"):
                        nome_corretto = stato_globale["calciatore_segreto"]["nome"].lower()
                        if tentativo.lower() == nome_corretto or tentativo.lower() in nome_corretto:
                            stato_globale["vincitore_partita"] = "IMPOSTORI"
                        else:
                            if len(tutti_impostori) == 1:
                                stato_globale["vincitore_partita"] = "FEDELI"
                                stato_globale["fase_remoto"] = "FINALE_IMPOSTORE"
                            else:
                                # Caso 2 impostori: se il primo sbaglia, viene eliminato
                                stato_globale["eliminati"].append(impostore_di_turno)
                                imp_vivi = [k for k, v in stato_globale["assegnazioni"].items() if "IMPOSTORE" in v["ruolo"] and k not in stato_globale["eliminati"]]
                                
                                if len(imp_vivi) == 0:
                                    stato_globale["vincitore_partita"] = "FEDELI"
                                    stato_globale["fase_remoto"] = "FINALE_IMPOSTORE"
                                else:
                                    # C'è ancora il secondo impostore in gioco! La partita prosegue
                                    stato_globale["scelte_bivio"] = {}
                                    stato_globale["indice_turno_attuale"] = 0
                                    stato_globale["fase_remoto"] = "CHAT"
                        st.rerun()
                else:
                    if stato_globale["fase_remoto"] == "FINALE_IMPOSTORE" or stato_globale["vincitore_partita"] is not None:
                        st.rerun()
                    if st.button("🔄 Controlla se l'Impostore ha risposto"): st.rerun()

            # --- SOTTO-FASE 6: SCHERMATA FINALE VINCITORE ---
            elif fase == "FINALE_IMPOSTORE" or stato_globale["vincitore_partita"] is not None:
                st.subheader("🏁 Risultato della Partita!")
                
                st.write(f"⚽ Il calciatore misterioso scelto dall'IA era: **{stato_globale['calciatore_segreto']['nome']}**")
                
                if stato_globale["vincitore_partita"] == "IMPOSTORI":
                    st.image("impostore.png", use_container_width=True)
                    st.markdown('<div class="card-impostore-default"><h1 style="color: #ffffff; font-size: 38px;">HA VINTO L\'IMPOSTORE!</h1><p style="font-size:16px;">Ha camuffato alla perfezione o ha indovinato il calciatore!</p></div>', unsafe_allow_html=True)
                else:
                    st.image("fedele.png", use_container_width=True)
                    st.markdown('<div class="card-fedele-default"><h1 style="color: #ffffff; font-size: 38px;">HANNO VINTO I FEDELI!</h1><p style="font-size:16px;">Gli impostori sono stati smascherati e non sono riusciti ad indovinare il giocatore!</p></div>', unsafe_allow_html=True)
                
                st.write("---")
                if st.button("🛑 FINE PARTITA (Torna alla Lobby)"):
                    stato_globale["partita_in_corso"] = False
                    st.rerun()

# --- 🤫 ACCESSO ULTRA-NASCOSTO AL PANNELLO MASTER ---
st.write("---")
codice_admin = st.text_input("⚙️", type="password", help="Pannello di controllo").strip()
if codice_admin.lower() == "show" and stato_globale["calciatore_segreto"]:
    st.markdown("### 👁️ Dati Segreti del Turno Corrente")
    st.write(f"**Calciatore Scelto:** {stato_globale['calciatore_segreto']['nome']}")
    st.write(f"**Indizio 1:** {stato_globale['calciatore_segreto']['indizio_identita']}")
    st.write(f"**Indizio 2:** {stato_globale['calciatore_segreto']['indizio_tecnico_aneddoto']}")
    st.caption(f"Memoria bloccati attuali: {len(stato_globale['ultimi_calciatori'])}/150")
