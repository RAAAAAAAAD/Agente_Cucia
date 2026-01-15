import pytest
from app.agent import RecipeAgent
from dotenv import load_dotenv

load_dotenv()

def test_agent_state_logic():
    agent = RecipeAgent()
    # Test 1: Fornire solo un ingrediente senza quantità
    response = agent.get_response("Ho della pasta", [])
    # L'agente dovrebbe chiedere la quantità o altri ingredienti
    assert agent.state.info_sufficienti == False
    assert len(agent.state.ingredienti) > 0
    print("✅ Test Stato Incompleto superato")

if __name__ == "__main__":
    test_agent_state_logic()
