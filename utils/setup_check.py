import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def verify():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("❌ Errore: GROQ_API_KEY non trovata nel file .env")
        return
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=key)
        res = llm.invoke("Test connection")
        print(f"✅ Connessione Groq riuscita con llama-3.3-70b-versatile")
    except Exception as e:
        print(f"❌ Errore API: {e}")

if __name__ == "__main__":
    verify()
