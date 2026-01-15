import os
import re
import urllib.parse
from datetime import datetime, date
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# --- DATA MODELS (STATE MANAGEMENT) ---

class Ingredient(BaseModel):
    nome: str
    quantita: str = "non specificata"
    info_scadenza: str = "Scadenza non nota"
    giorni_residui: int = 999 

class UserProfile(BaseModel):
    esperienza: str = "non specificata"
    allergie: List[str] = []
    restrizioni: List[str] = []
    gusti_odio: List[str] = []
    gusti_amo: List[str] = []
    piccante: str = "medio"
    stile_cucina: str = "tradizionale"
    occasione: str = "pasto quotidiano"
    porzioni: str = "normali"

class KitchenState(BaseModel):
    ingredienti: List[Ingredient] = []
    profilo: UserProfile = UserProfile()
    numero_persone: int = 0
    info_sufficienti: bool = False

# --- AGENTE CHEF ---

class RecipeAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        # Usiamo il modello 8B per l'estrazione (veloce e risparmia token)
        self.llm_fast = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=self.api_key, temperature=0)
        # Usiamo Mixtral o Llama 70B per la risposta finale (ragionamento complesso)
        self.llm_reasoning = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=self.api_key, temperature=0.2)
        
        self.search = TavilySearchResults(max_results=1)
        self.state = KitchenState()

    def _tavily_search(self, query: str) -> str:
        try:
            results = self.search.invoke(query)
            return results[0]['url'] if results else "#"
        except: return "#"

    def update_state(self, user_input: str):
        oggi = date.today().strftime("%Y-%m-%d")
        state_json = self.state.model_dump_json().replace("{", "{{").replace("}", "}}")
        
        extraction_prompt = f"""
        Oggi è il {oggi}. Analizza l'input per aggiornare lo STATO.
        REGOLE ESTRAZIONE:
        1. Allergie/Restrizioni: Fondamentali.
        2. Scadenze: MM/AAAA = fine mese. Calcola giorni rispetto a {oggi}.
        3. Profilo: Estrai esperienza, gusti, occasione e porzioni.
        
        SUFFICIENZA: True solo se hai 3+ ingredienti con quantità, numero persone, esperienza e allergie dichiarate.
        
        INPUT: "{user_input}"
        STATO ATTUALE: {state_json}
        Rispondi SOLO in JSON.
        """
        # Usiamo il modello veloce per non bloccare il Rate Limit
        structured_llm = self.llm_fast.with_structured_output(KitchenState)
        self.state = structured_llm.invoke(extraction_prompt)

    def get_response(self, user_input: str, chat_history: List[BaseMessage]):
        # Se siamo vicini al limite, questa chiamata potrebbe fallire. 
        # In caso di errore 429 persistente, cambieremo anche questo in llama-3.1-8b-instant.
        try:
            self.update_state(user_input)
            state_json = self.state.model_dump_json().replace("{", "{{").replace("}", "}}")
            
            system_msg = f"""
            Sei un Senior Chef AI Expert. 
            STATO ATTUALE: {state_json}
            
            PROTOCOLLO:
            1. SICUREZZA: Chiedi allergie se non note.
            2. RACCOLTA: Chiedi ingredienti, persone o esperienza se mancano.
            3. PROPOSTA: Se info_sufficienti è True, genera 3 ricette dosate per {self.state.numero_persone} persone.
               - Includi PREPARAZIONE DETTAGLIATA.
               - Tag obbligatori: [IMG: ...], [VIDEO: ...], [LINK: ...].
            """
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_msg),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}")
            ])
            
            chain = prompt | self.llm_reasoning
            raw_res = chain.invoke({"input": user_input, "history": chat_history}).content
        except Exception as e:
            if "rate_limit" in str(e).lower():
                return "⚠️ Ho esaurito i miei 'gettoni' giornalieri per il ragionamento avanzato. Riprova tra qualche minuto o chiedimi qualcosa di più semplice."
            return f"Errore: {e}"
        
        # Post-Processing
        res = raw_res
        def fix_img(m):
            q = urllib.parse.quote(m.group(1).strip() + " food photography")
            return f"\n\n![Piatto](https://pollinations.ai/p/{q}?width=600&height=400&nologo=true)\n"
        res = re.sub(r"\[IMG:\s*(.*?)\]", fix_img, res, flags=re.IGNORECASE)

        def fix_video(m):
            u = self._tavily_search(f"video ricetta {m.group(1).strip()} youtube")
            return f"\n\n[▶️ Video Ricetta su YouTube]({u})\n"
        res = re.sub(r"\[VIDEO:\s*(.*?)\]", fix_video, res, flags=re.IGNORECASE)

        def fix_link(m):
            u = self._tavily_search(f"ricetta originale {m.group(1).strip()}")
            return f"\n[📖 Ricetta Originale Online]({u})\n"
        res = re.sub(r"\[LINK:\s*(.*?)\]", fix_link, res, flags=re.IGNORECASE)

        return res
