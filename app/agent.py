import os
import re
import urllib.parse
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# --- STATE MANAGEMENT (MODIFICATO) ---
class Ingredient(BaseModel):
    nome: str
    quantita: str = "non specificata"
    info_scadenza: str = "Scadenza non nota"
    giorni_residui: int = 999 

class KitchenState(BaseModel):
    ingredienti: List[Ingredient] = []
    preferenze: List[str] = []
    numero_persone: int = Field(0, description="Numero di commensali")
    info_sufficienti: bool = False

# --- LOGICA AGENTE ---
class RecipeAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=self.api_key, temperature=0.1)
        self.search = TavilySearchResults(max_results=1)
        self.state = KitchenState()

    def _tavily_search(self, query: str) -> str:
        try:
            results = self.search.invoke(query)
            return results[0]['url'] if results else "#"
        except:
            return "#"

    def update_state(self, user_input: str):
        oggi = date.today().strftime("%Y-%m-%d")
        state_json = self.state.model_dump_json().replace("{", "{{").replace("}", "}}")
        
        extraction_prompt = f"""
        Oggi è il {oggi}. Estrai dati per aggiornare lo stato.
        
        LOGICA SCADENZA (MM/AAAA):
        - Se l'utente scrive MM/AAAA (es. 02/2026), interpretalo come l'ultimo giorno di quel mese.
        - Calcola i giorni residui rispetto a oggi ({oggi}).
        - Se mancano mesi, scrivi: 'Scade tra X mesi (MM/AAAA)'.
        
        LOGICA PERSONE:
        - Cerca riferimenti al numero di persone (es. "siamo in 4", "per due").
        
        LOGICA SUFFICIENZA:
        info_sufficienti = True SOLO SE:
        1. Hai 3+ ingredienti con quantità.
        2. Hai il numero_persone (maggiore di 0).
        
        INPUT: "{user_input}"
        STATO ATTUALE: {state_json}
        Rispondi SOLO in JSON.
        """
        structured_llm = self.llm.with_structured_output(KitchenState)
        self.state = structured_llm.invoke(extraction_prompt)

    def get_response(self, user_input: str, chat_history: List[BaseMessage]):
        self.update_state(user_input)
        state_json = self.state.model_dump_json().replace("{", "{{").replace("}", "}}")
        
        system_msg = f"""
        Sei un AI Chef Expert. 
        STATO ATTUALE: {state_json}
        
        RAGIONAMENTO:
        - Se numero_persone == 0: Chiedi gentilmente "Per quante persone devo preparare?".
        - Se ingredienti < 3 o senza quantità: Chiedi i dettagli mancanti.
        - Se info_sufficienti è True: Proponi 3 ricette dosate per {self.state.numero_persone} persone.
        
        REGOLE RICETTE:
        - Priorità assoluta alle scadenze vicine.
        - Descrizione STEP-BY-STEP obbligatoria.
        - Inserisci SEMPRE:
          [IMG: food photography of dish name]
          [VIDEO: ricetta nome piatto youtube]
          [LINK: ricetta originale nome piatto]
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        chain = prompt | self.llm
        raw_res = chain.invoke({"input": user_input, "history": chat_history}).content
        
        # POST-PROCESSING
        res = raw_res
        def fix_img(m):
            q = urllib.parse.quote(m.group(1).strip())
            return f"\n\n![Ricetta](https://pollinations.ai/p/{q}?width=600&height=400&nologo=true)\n"
        res = re.sub(r"\[IMG:\s*(.*?)\]", fix_img, res, flags=re.IGNORECASE)

        def fix_video(m):
            u = self._tavily_search(m.group(1).strip())
            return f"\n\n[▶️ Video-Ricetta su YouTube]({u})\n"
        res = re.sub(r"\[VIDEO:\s*(.*?)\]", fix_video, res, flags=re.IGNORECASE)

        def fix_link(m):
            u = self._tavily_search(m.group(1).strip())
            return f"\n[📖 Ricetta dettagliata online]({u})\n"
        res = re.sub(r"\[LINK:\s*(.*?)\]", fix_link, res, flags=re.IGNORECASE)

        return res
