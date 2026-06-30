import streamlit as st
import random
import json
import time
from groq import Groq

# --- CONFIGURAZIONE INTERFACCIA E STILE CSS (CON CAMPO DA CALCIO) ---
st.set_page_config(page_title="⚽ Lobby Impostori", page_icon="⚽", layout="centered")

st.markdown("""
    <style>
    /* Sfondo generale scuro */
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    /* Rettangolo che simula il campo da calcio per la griglia dei giocatori */
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
    
    /* Stile per le Card dei Ruoli sotto le immagini */
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
    
    /* Mattoncini dei giocatori arrotondati */
    div.stButton > button {
        width: 100%; background-color: #1f293d; color: #ffffff;
        border: 2px solid #3b82f6; border-radius: 12px; padding: 14px;
        font-weight: bold; font-size: 16px; transition: all 0.3s ease;
    }
    div.stButton > button:hover { background-color: #3b82f6; border-color: #00ffcc; transform: scale(1.02); }
    .lobby-box { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px dashed #30363d; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- MEMORIA GLOBALE CONDIVISA (SERVER-SIDE) ---
@st.cache_resource
def ottieni_memoria_condivisa():
    return {
        "giocatori_connessi": [],
        "partita_in_corso": False,
        "assegnazioni": {},
        "calciatore_segreto": None,
        "ultimi_calciatori": [] # La memoria globale dei 150 calciatori usciti
    }

stato_globale = ottieni_memoria_condivisa()

# --- CONFIGURAZIONE CLIENT GROQ SICURA ---
if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    try:
        client = Groq()
    except Exception:
        st.warning("⚠️ Configura la chiave API di Groq nei Secrets di Streamlit.")

# --- FUNZIONE GENERAZIONE CALCIATORE ---
def genera_calciatore_con_ia():
    modello_stabile = "llama-3.3-70b-versatile"
    
    lettere = ["A", "B", "C", "D", "E", "F", "G", "I", "L", "M", "N", "O", "P", "R", "S", "T", "V", "Z"]
    ruoli = ["Attaccante", "Centrocampista", "Difensore", "Portiere", "Leggenda del calcio"]
    
    lettera_scelta = random.choice(lettere)
    ruolo_scelto = random.choice(ruoli)
    seed_casuale = random.randint(1, 999999)
    timestamp_unico = int(time.time() * 1000)
    
    # Recuperiamo la memoria storica dei 150 elementi dallo STATO GLOBALE CONDIVISO
    vietati_stringa = ", ".join(stato_globale['ultimi_calciatori']) if stato_globale['ultimi_calciatori'] else "Nessuno"
    
    prompt_scelta = f"""
    Scegli il nome di un calciatore famoso mondiale, attuale o una leggenda del passato. Principalmente scegliendo tra giocatori che hanno giocato almeno una 
    o più stagioni in Serie A, anche giocatori di Premier League, del Real Madrid, Barcellona o famosi in generale vanno bene.
 
    🚫 REGOLE DI ESCLUSIONE TOTALI (MAI SELEZIONARE QUESTI NOMI):
    È SEVERAMENTE VIETATO scegliere uno di questi calciatori già usciti: [{vietati_stringa}].
    Inoltre non scegliere Cristiano Ronaldo o Lionel Messi. Sii originale, pesca nel passato o tra giocatori diversi!

    Rispondi SOLO con il nome e cognome, senza nient'altro. No punti, no frasi.
    ID casuale: {seed_casuale} - Timestamp: {timestamp_unico}
    """
    
    try:
        res_scelta = client.chat.completions.create(
            model=modello_stabile,
            messages=[{"role": "user", "content": prompt_scelta}],
            temperature=1.3 
        )
        calciatore_scelto = res_scelta.choices[0].message.content.strip().replace(".", "")
    except Exception as e:
        calciatore_scelto = "Kylian Mbappé" 
        
    system_instruction = f"""
    Sei il motore di un gioco d'ingegno sui calciatori in lingua italiana. 
    Genera due indizi CORTISSIMI (da 1 a 3 parole al massimo) per il calciatore assegnato.
    Rispondi SOLO in italiano.
    
    Calciatore di questo turno: {calciatore_scelto}
    
    REGOLA DI SICUREZZA ASSOLUTA E VITALI:
    - È SEVERAMENTE VIETATO INCLUDE il nome, il cognome o parti del nome del calciatore dentro gli indizi. 
    - Non usare i colori sociali della maglia (es. no 'Rossonero', no 'Bianconero' ma per Juve ad esempio Zebra).
    - Sii storicamente preciso ed EVITA soprannomi di altri calciatori.

    Ad esempio se la nazionalità è Macedonia, dato che ci sono pochi giocatori macedoni, puoi dare un indizio in cui bisogna ragionare per capire che si trata di quella nazione
    come ad esempio "frutta" dato che è famosa la macedonia di frutta.
    
    Rispondi ESCLUSIVAMENTE con un oggetto JSON con queste tre chiavi precise:
    {{
        "nome": "{calciatore_scelto}",
        "indizio_identita": "una parola sulla nazione o città storica in cui ha giocato (es. Tango, Torre, Colosseo, Vesuvio) usa simboli famosi, balli tradizionali, animali dello stemma della squadra, il motivo per cui la squadra è famosa o se è un giocatore che ha vinto il Triplete con una squadra puoi scrivere Triplete",
        "indizio_tecnico_aneddoto": "una parola secca, un'associazione d'idee VERITIERA, un contrario o un aneddoto ironico, l'anno di nascita esatto, un suo celebre record o esatto soprannome reale (Senza mai usare il suo nome!)"
    }}
    
    REGOLE DI STILE: massimo 1-3 parole secche, no frasi, no parentesi. Puoi usare parole singole, rime fonetiche, onomatopee (ad esempio per Andrea Belotti che viene chiamato Gallo puoi usare "Chicchirichì") o associazioni dirette.
    """

    try:
        completion = client.chat.completions.create(
            model=modello_stabile,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Genera il JSON per {calciatore_scelto}."}
            ],
            temperature=1.1, 
            response_format={"type": "json_object"}
        )
        
        dati = json.loads(completion.choices[0].message.content)
        nome = dati.get('nome', calciatore_scelto)
        indizio_id = dati.get('indizio_identita') or list(dati.values())[1] if len(dati) > 1 else "Campione"
        indizio_tec = dati.get('indizio_tecnico_aneddoto') or list(dati.values())[2] if len(dati) > 2 else "Fulmine"
        
        # Aggiorna la memoria storica dei 150 elementi NELLO STATO GLOBALE CONDIVISO
        if nome not in stato_globale['ultimi_calciatori']:
            stato_globale['ultimi_calciatori'].append(nome)
        if len(stato_globale['ultimi_calciatori']) > 150:
            stato_globale['ultimi_calciatori'].pop(0)
            
        return {"nome": nome, "indizio_identita": indizio_id, "indizio_tecnico_aneddoto": indizio_tec}
    except Exception as e:
        return {"nome": calciatore_scelto, "indizio_identita": "Torre", "indizio_tecnico_aneddoto": "Velocità"}

# --- STATO LOCALE DISPOSITIVO ---
if 'mio_nome' not in st.session_state: st.session_state['mio_nome'] = None
if 'identita_bloccata' not in st.session_state: st.session_state['identita_bloccata'] = False

st.title("⚽ Il Gioco degli Impostori")

# --- FASE 1: LOBBY D'ATTESA (Se la partita non è ancora iniziata) ---
if not stato_globale["partita_in_corso"]:
    st.subheader("🎮 Fase 1: Entra nella Lobby")
    
    # Inserimento nome del singolo giocatore (Stato locale del dispositivo)
    if not st.session_state['mio_nome']:
        nuovo_nome = st.text_input("Inserisci il tuo nome per partecipare:", key="input_nome_singolo").strip()
        if st.button("✅ Entra nella Stanza"):
            # Aggiunge il nome alla lista globale condivisa sul server
            if nuovo_nome and nuovo_nome not in stato_globale["giocatori_connessi"]:
                stato_globale["giocatori_connessi"].append(nuovo_nome)
                st.session_state['mio_nome'] = nuovo_nome
                st.rerun()
            elif nuovo_nome in stato_globale["giocatori_connessi"]:
                st.error("Questo nome è già occupato nella stanza!")
    else:
        # Mostra il nome confermato e il tasto per uscire
        st.success(f"Sei dentro la stanza come: **{st.session_state['mio_nome']}**")
        if st.button("❌ Esci dalla Stanza"):
            stato_globale["giocatori_connessi"].remove(st.session_state['mio_nome'])
            st.session_state['mio_nome'] = None
            st.rerun()

    # Visualizzazione lista giocatori connessi in tempo reale (Condivisa)
    st.markdown("<div class='lobby-box'>", unsafe_allow_html=True)
    st.write(f"👥 **Giocatori pronti ({len(stato_globale['giocatori_connessi'])}):**")
    if stato_globale["giocatori_connessi"]:
        st.write(", ".join(stato_globale["giocatori_connessi"]))
    else:
        st.italic("In attesa che i giocatori si colleghino...")
    st.markdown("</div>", unsafe_allow_html=True)

    # --- AGGIUNTA: OPZIONE SELEZIONE IMPOSTORI (Compare solo se siete almeno in 6) ---
    forza_due = True # Valore di default se siete in meno di 6
    if len(stato_globale["giocatori_connessi"]) >= 6:
        st.write("---")
        forza_due = st.checkbox("⚽ Forza 2 Impostori per questo turno (consigliato)", value=True)

    # Bottone di avvio (Visibile a tutti, basta che ci siano almeno 3 giocatori)
    if len(stato_globale["giocatori_connessi"]) >= 3:
        if st.button("🚀 AVVIA PARTITA PER TUTTI", type="primary"):
            with st.spinner("L'IA sta estraendo il calciatore misterioso..."):
                calciatore = genera_calciatore_con_ia()
                lista_amici = stato_globale["giocatori_connessi"].copy()
                random.shuffle(lista_amici)
                
                assegnazioni = {}
                # Applica la scelta della casella se siete in 6 o più, altrimenti 1 solo
                imp_da_mettere = 2 if (len(lista_amici) >= 6 and forza_due) else 1
                
                if imp_da_mettere == 1:
                    # Assegna 1 Impostore con un indizio casuale
                    ind_casuale = random.choice([calciatore['indizio_identita'], calciatore['indizio_tecnico_aneddoto']])
                    assegnazioni[lista_amici.pop()] = {"ruolo": "IMPOSTORE", "dettaglio": ind_casuale}
                else:
                    # Assegna 2 Impostori con indizi diversi (Base e Dettaglio)
                    assegnazioni[lista_amici.pop()] = {"ruolo": "IMPOSTORE 1", "dettaglio": calciatore['indizio_identita']}
                    assegnazioni[lista_amici.pop()] = {"ruolo": "IMPOSTORE 2", "dettaglio": calciatore['indizio_tecnico_aneddoto']}
                
                # Assegna il ruolo di Fedele a tutti gli altri
                for fedele in lista_amici:
                    assegnazioni[fedele] = {"ruolo": "FEDELE", "dettaglio": calciatore['nome']}
                
                # Aggiorna lo stato globale per far partire la partita su tutti i telefoni
                stato_globale["calciatore_segreto"] = calciatore
                stato_globale["assegnazioni"] = assegnazioni
                stato_globale["partita_in_corso"] = True
                st.rerun()
    else:
        st.info("Servono almeno 3 giocatori connessi per poter avviare la partita.")
        if st.button("🔄 Aggiorna Lista"):
            st.rerun()

# --- FASE 2: GRIGLIA SUL CAMPO DA CALCIO & CARTE ---
else:
    if not st.session_state['identita_bloccata']:
        st.subheader("🏟️ Seleziona il tuo mattoncino sul campo!")
        
        nomi_disponibili = stato_globale["giocatori_connessi"]
        
        # Apertura del contenitore grafico stile CAMPO DA CALCIO
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
                        
        st.markdown("</div>", unsafe_allow_html=True) # Chiusura campo da calcio
        
    else:
        # --- SCHERMATA COMPLETA E BLOCCATA SULLA CARD PERSONALE ---
        mio_nome = st.session_state['mio_nome']
        mio_ruolo = stato_globale["assegnazioni"].get(mio_nome)
        
        if mio_ruolo:
            st.write(f"### 📱 Schermo bloccato su: **{mio_nome}**")
            
            if "IMPOSTORE" in mio_ruolo['ruolo']:
                # Mostra direttamente l'immagine dell'impostore caricata su GitHub
                st.image("impostore.png", use_container_width=True)
                
                # Testo e indizio sotto l'immagine
                st.markdown(f"""
                    <div class="card-impostore-default">
                        <h2 style='color: #ff3333; margin: 0;'>🕵️‍♂️ {mio_ruolo['ruolo']}</h2>
                        <p style='font-size: 16px; margin-top: 10px; color: #ffcccc;'>Il tuo indizio segreto è:</p>
                        <h1 style='color: #ffffff; font-size: 34px; margin: 5px 0;'>{mio_ruolo['dettaglio']}</h1>
                        <p style='font-size: 14px; color: #ffa3a3; font-style: italic;'>Infiltrati, bluffa e non farti scoprire!</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                # Mostra direttamente l'immagine del fedele caricata su GitHub
                st.image("fedele.png", use_container_width=True)
                
                # Testo e calciatore sotto l'immagine
                st.markdown(f"""
                    <div class="card-fedele-default">
                        <h2 style='color: #00ffcc; margin: 0;'>🟩 FEDELE</h2>
                        <p style='font-size: 16px; margin-top: 10px; color: #ccfffa;'>Il calciatore misterioso è:</p>
                        <h1 style='color: #ffffff; font-size: 34px; margin: 5px 0;'>{mio_ruolo['dettaglio']}</h1>
                        <p style='font-size: 14px; color: #a3fff2; font-style: italic;'>Fai domande mirate per scovare gli impostori!</p>
                    </div>
                """, unsafe_allow_html=True)
        
        st.write("---")
        if st.button("🛑 FINE PARTITA (Prossimo Giro)"):
            stato_globale["partita_in_corso"] = False
            stato_globale["assegnazioni"] = {}
            stato_globale["calciatore_segreto"] = None
            st.session_state['identita_bloccata'] = False
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
