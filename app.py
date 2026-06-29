import streamlit as st
import random
import json
import time
from groq import Groq

# --- CONFIGURAZIONE PAGINA STREAMLIT ---
st.set_page_config(page_title="Il Gioco degli Impostori", page_icon="⚽", layout="centered")

st.title("⚽ Il Gioco degli Impostori")
st.write("Inserisci i giocatori, genera il calciatore segreto e scopri chi sono gli impostori!")

# --- INIZIALIZZAZIONE MEMORIA DI STREAMLIT (SESSION STATE) ---
# Usiamo st.session_state così i dati non si azzerano quando si cliccano i bottoni
if 'ULTIMI_CALCIATORI' not in st.session_state:
    st.session_state['ULTIMI_CALCIATORI'] = []

if 'partita_generata' not in st.session_state:
    st.session_state['partita_generata'] = False
    st.session_state['calciatore_segreto'] = None
    st.session_state['assegnazioni'] = {}

# --- CONFIGURAZIONE CLIENT GROQ SICURA ---
# Cerca la chiave prima nei segreti di Streamlit (per il cloud) o usa le variabili d'ambiente
if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    try:
        client = Groq()
    except Exception:
        st.warning("⚠️ Configura la chiave API di Groq nei Secrets di Streamlit.")

# --- FUNZIONE GENERAZIONE CALCIATORE (IL TUO PROMPT BLINDATO) ---
def genera_calciatore_con_ia():
    modello_stabile = "llama-3.3-70b-versatile"
    
    lettere = ["A", "B", "C", "D", "E", "F", "G", "I", "L", "M", "N", "O", "P", "R", "S", "T", "V", "Z"]
    ruoli = ["Attaccante", "Centrocampista", "Difensore", "Portiere", "Leggenda del calcio"]
    
    lettera_scelta = random.choice(lettere)
    ruolo_scelto = random.choice(ruoli)
    seed_casuale = random.randint(1, 999999)
    timestamp_unico = int(time.time() * 1000)
    
    # Recuperiamo la memoria storica dei 150 elementi dallo stato di Streamlit
    vietati_stringa = ", ".join(st.session_state['ULTIMI_CALCIATORI']) if st.session_state['ULTIMI_CALCIATORI'] else "Nessuno"
    
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
    - È SEVERAMENTE VIETATO includere il nome, il cognome o parti del nome del calciatore dentro gli indizi. 
    - Non usare i colori sociali della maglia (es. no 'Rossonero', no 'Bianconero' ma per Juve ad esempio Zebra).
    - Sii storicamente preciso ed EVITA soprannomi di altri calciatori.

    Ad esempio se la nazionalità è Macedonia, dato che ci sono pochi giocatori macedoni, puoi dare un indizio in cui bisogna ragionare per capire che si tratta di quella nazione
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
        
        # Aggiorna la memoria storica dei 150 elementi
        if nome not in st.session_state['ULTIMI_CALCIATORI']:
            st.session_state['ULTIMI_CALCIATORI'].append(nome)
        if len(st.session_state['ULTIMI_CALCIATORI']) > 150:
            st.session_state['ULTIMI_CALCIATORI'].pop(0)
            
        return {"nome": nome, "indizio_identita": indizio_id, "indizio_tecnico_aneddoto": indizio_tec}
    except Exception as e:
        return {"nome": calciatore_scelto, "indizio_identita": "Torre", "indizio_tecnico_aneddoto": "Velocità"}

# --- INTERFACCIA UTENTE STREAMLIT ---
# 1. Input della lista di amici
nomi_inseriti = st.text_input("Inserisci i nomi dei giocatori separati da una virgola", "Elena, Alessandro, Matteo, Marco, Davide, Luca")
lista_amici = [n.strip() for n in nomi_inseriti.split(",") if n.strip()]

# 2. Selezione opzioni partita
forza_due = st.checkbox("Forza 2 Impostori (richiede almeno 6 giocatori)", value=True)

# 3. Bottone per avviare la partita
if st.button("🚀 GENERA NUOVA PARTITA", type="primary"):
    if len(lista_amici) < 3:
        st.error("Servono almeno 3 giocatori per avviare il gioco!")
    else:
        with st.spinner("L'IA sta scegliendo un calciatore misterioso..."):
            calciatore = genera_calciatore_con_ia()
            
            num_giocatori = len(lista_amici)
            impostori_da_inserire = 2 if (num_giocatori >= 6 and forza_due) else 1
            
            giocatori_casuali = lista_amici.copy()
            random.shuffle(giocatori_casuali)
            assegnazioni = {}
            
            if impostori_da_inserire == 1:
                indizio_casuale = random.choice([calciatore['indizio_identita'], calciatore['indizio_tecnico_aneddoto']])
                imp1 = giocatori_casuali.pop()
                assegnazioni[imp1] = f"🕵️‍♂️ Sei l'IMPOSTORE! Il tuo indizio è: **{indizio_casuale}**"
            elif impostori_da_inserire == 2:
                imp1 = giocatori_casuali.pop()
                assegnazioni[imp1] = f"🕵️‍♂️ Sei l'IMPOSTORE 1! Indizio Base: **{calciatore['indizio_identita']}**"
                imp2 = giocatori_casuali.pop()
                assegnazioni[imp2] = f"🕵️‍♂️ Sei l'IMPOSTORE 2! Indizio Dettaglio: **{calciatore['indizio_tecnico_aneddoto']}**"
                
            for fedele in giocatori_casuali:
                assegnazioni[fedele] = f"🟩 Sei un FEDELE. Il calciatore segreto è: **{calciatore['nome']}**"
            
            # Salviamo tutto nello stato sessione per non perderlo
            st.session_state['calciatore_segreto'] = calciatore
            st.session_state['assegnazioni'] = assegnazioni
            st.session_state['partita_generata'] = True

# --- VISUALIZZAZIONE RISULTATI ---
if st.session_state['partita_generata']:
    calc = st.session_state['calciatore_segreto']
    
    # Pannello di Controllo Master (Visibile solo a chi gestisce lo schermo)
    with st.expander("👁️ PANNELLO MASTER (Nascondi agli altri giocatori)"):
        st.write(f"**Calciatore Scelto:** {calc['nome']}")
        st.write(f"**Indizio Identità:** {calc['indizio_identita']}")
        st.write(f"**Indizio Tecnico:** {calc['indizio_tecnico_aneddoto']}")
        st.caption(f"Memoria bloccati ({len(st.session_state['ULTIMI_CALCIATORI'])}/150): {st.session_state['ULTIMI_CALCIATORI'][-5:]}")

    st.subheader("📱 Schermate dei Singoli Giocatori")
    st.write("Passatevi il computer/telefono a turno. Clicca sul tuo nome per vedere la tua identità segreta senza farla vedere agli altri!")
    
    # Creiamo dei menu a tendina singoli (Expander) per ogni giocatore
    for giocatore in lista_amici:
        if giocatore in st.session_state['assegnazioni']:
            with st.expander(f"👤 Schermata per: {giocatore}"):
                st.large_text = st.markdown(f"### {st.session_state['assegnazioni'][giocatore]}")