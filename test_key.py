import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()
key = os.getenv("GROQ_API_KEY")

try:
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=key)
    res = llm.invoke("Ciao, rispondi con la parola 'OK' se mi senti.")
    print(f"✅ Test riuscito! Risposta: {res.content}")
except Exception as e:
    print(f"❌ Test fallito. Errore: {e}")
