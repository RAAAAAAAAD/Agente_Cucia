import streamlit as st
from agent import RecipeAgent
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Chef Agent Pro", layout="wide")

if "agent" not in st.session_state:
    st.session_state.agent = RecipeAgent()
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: PROGRESSO CONOSCENZA ---
with st.sidebar:
    st.title("👤 Profilo & Dispensa")
    state = st.session_state.agent.state
    
    # Sezione Allergie (Evidenziata)
    if not state.profilo.allergie:
        st.error("⚠️ Allergie non specificate")
    else:
        st.success(f"🛡️ Allergie: {', '.join(state.profilo.allergie)}")

    # Sezione Esperienza e Persone
    col1, col2 = st.columns(2)
    col1.metric("Persone", state.numero_persone)
    col2.metric("Livello", state.profilo.esperienza)

    st.divider()
    
    # Inventario
    st.subheader("🛒 Ingredienti Rilevati")
    for ing in state.ingredienti:
        with st.expander(f"{ing.nome.upper()}"):
            st.write(f"Q.tà: {ing.quantita}")
            if "Scaduto" in ing.info_scadenza: st.error(ing.info_scadenza)
            else: st.info(ing.info_scadenza)

    st.divider()
    st.subheader("🎨 Gusti e Occasione")
    st.write(f"**Occasione:** {state.profilo.occasione}")
    st.write(f"**Cucina:** {state.profilo.stile_cucina}")
    if state.profilo.gusti_odio:
        st.write(f"**Odia:** {', '.join(state.profilo.gusti_odio)}")

# --- CHAT ---
st.title("👨‍🍳 AI Chef Agent: Conversazione Gourmet")

for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

if prompt := st.chat_input("Es: Sono un principiante, siamo in 2, nessuna allergia. Ho del salmone..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.chat_message("user").markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Lo Chef sta analizzando il tuo profilo..."):
            res = st.session_state.agent.get_response(prompt, st.session_state.messages[:-1])
            st.markdown(res)
            st.session_state.messages.append(AIMessage(content=res))
            st.rerun()
