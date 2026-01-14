import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SCOPUS_API_KEY")

def teste_vip():
    print("--- 📡 TESTE DE CONEXÃO: REDE UnB ---")
    
    headers = {
        "X-ELS-APIKey": API_KEY,
        "Accept": "application/json"
    }

    # Tenta acessar a visão COMPLETE (que falhou antes)
    # Pegamos um artigo qualquer da UnB para testar
    params = {
        "query": "AF-ID(60024989)", 
        "count": 1,
        "view": "COMPLETE" # <--- O motivo do erro anterior
    }

    try:
        r = requests.get("https://api.elsevier.com/content/search/scopus", headers=headers, params=params)
        
        if r.status_code == 200:
            print("\n✅ SUCESSO TOTAL! A rede da UnB liberou o acesso.")
            print("Agora você pode usar o script 'Detail Hunter' para pegar todos os autores!")
            print(f"Status: {r.status_code}")
        elif r.status_code == 401:
            print("\n⛔ Acesso Negado (401).")
            print("Diagnóstico: Mesmo na rede, a chave precisa de um 'Token Institucional' ou a VPN não está tunelando o tráfego corretamente.")
        else:
            print(f"\n⚠️ Outro resultado: {r.status_code}")
            
    except Exception as e:
        print(f"Erro de conexão: {e}")

if __name__ == "__main__":
    teste_vip()