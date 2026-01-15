import streamlit as st
from agent import RecipeAgent
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI Kitchen Agent", layout="wide")

if "agent" not in st.session_state:
    st.session_state.agent = RecipeAgent()
if "messages" not in st.session_state:
    st.session_state.messages = []

# SIDEBAR
with st.sidebar:
    st.header("📋 Inventario Real-Time")
    for ing in st.session_state.agent.state.ingredienti:
        with st.container(border=True):
            st.markdown(f"**{ing.nome.upper()}**")
            st.write(f"Quantità: {ing.quantita}")
            if "Scaduto" in ing.info_scadenza:
                st.error(ing.info_scadenza)
            elif "Scade oggi" in ing.info_scadenza or "1 giorni" in ing.info_scadenza:
                st.warning(ing.info_scadenza)
            else:
                st.success(ing.info_scadenza)

# CHAT
st.title("👨‍🍳 AI Chef: Ricette dalle tue scadenze")

for msg in st.session_state.messages:
    with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
        st.markdown(msg.content)

if prompt := st.chat_input("Es: Ho 500g di carne scaduta da 1 giorno e 2 uova..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.chat_message("user").markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Cercando video e link ufficiali..."):
            res = st.session_state.agent.get_response(prompt, st.session_state.messages[:-1])
            st.markdown(res)
            st.session_state.messages.append(AIMessage(content=res))
            st.rerun()
