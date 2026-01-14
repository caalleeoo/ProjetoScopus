import os
import requests
import pandas as pd
import json
from dotenv import load_dotenv
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
load_dotenv()
API_KEY = os.getenv("SCOPUS_API_KEY")
BASE_URL = "https://api.elsevier.com/content/search/scopus"
ID_UNB = "60024989"

# --- 2. MOTOR DE BUSCA (Com Filtro de Data) ---
def buscar_scopus_por_periodo(query, ano_inicio, ano_fim, max_items=50):
    print(f"--- Buscando produção da UnB entre {ano_inicio} e {ano_fim} ---")
    
    headers = {
        "X-ELS-APIKey": API_KEY,
        "Accept": "application/json"
    }
    
    documentos = []
    
    # Formata o intervalo de datas para a API (ex: "2023-2024")
    intervalo_data = f"{ano_inicio}-{ano_fim}"
    
    for start in range(0, max_items, 25):
        count = min(25, max_items - len(documentos))
        if count <= 0: break

        params = {
            "query": query,
            "date": intervalo_data, # <--- O FILTRO DE TEMPO ENTRA AQUI
            "count": count, 
            "start": start, 
            "view": "COMPLETE" # Essencial para pegar os IDs dos autores
        }

        try:
            r = requests.get(BASE_URL, headers=headers, params=params)
            
            if r.status_code == 401:
                print("⛔ ERRO 401: Falha de permissão (View Complete). Verifique a VPN.")
                break
            elif r.status_code != 200:
                print(f"⚠️ Erro: {r.status_code} - {r.text}")
                break
            
            dados = r.json()
            novos = dados.get("search-results", {}).get("entry", [])
            
            if not novos: break
            
            documentos.extend(novos)
            print(f"   -> Baixados {len(documentos)} documentos...")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Erro crítico: {e}")
            break
            
    return documentos

# --- 3. EXTRATOR DE IDs (Ouro para o SciVal) ---
def garantir_lista(objeto):
    if not objeto: return []
    if isinstance(objeto, list): return objeto
    return [objeto]

def analisar_autores_detalhado(doc):
    """
    Retorna:
    1. String legível: "Nome (ID)"
    2. String pura de IDs da UnB: "12345; 67890" (Perfeito para colar no SciVal)
    """
    autores_raw = garantir_lista(doc.get("author", []))
    
    lista_unb_formatada = [] # Ex: "Maria Silva (558899)"
    lista_unb_ids_puros = [] # Ex: "558899"
    lista_todos_nomes = []
    
    for aut in autores_raw:
        nome = aut.get("authname", "Desconhecido")
        # O Scopus ID é o ID que o SciVal usa
        auth_id = aut.get("authid", "") 
        
        lista_todos_nomes.append(nome)
        
        # Verifica afiliação
        afids_raw = garantir_lista(aut.get("afid", []))
        ids_afiliacao = [str(af.get("$", "")) for af in afids_raw if "$" in af]
        
        if ID_UNB in ids_afiliacao:
            # Encontramos um autor da UnB!
            lista_unb_formatada.append(f"{nome} [{auth_id}]")
            if auth_id:
                lista_unb_ids_puros.append(auth_id)
            
    return (
        "; ".join(lista_todos_nomes), 
        "; ".join(lista_unb_formatada), 
        "; ".join(lista_unb_ids_puros)
    )

# --- 4. LAPIDADOR E SALVAMENTO ---
def salvar_dados(docs):
    agora = datetime.now()
    timestamp = agora.strftime("%Y-%m-%d_%H-%M-%S")
    
    lista_limpa = []
    
    for d in docs:
        todos_nomes, unb_formatado, unb_ids = analisar_autores_detalhado(d)
        
        item = {
            "titulo": d.get("dc:title", "N/A"),
            "ano": d.get("prism:coverDate", "")[:4],
            
            # --- DADOS PARA O SCIVAL ---
            "autores_unb_detalhado": unb_formatado,
            "autores_unb_ids": unb_ids,
            # ---------------------------
            
            "todos_autores": todos_nomes,
            "revista": d.get("prism:publicationName", "N/A"),
            "citacoes": d.get("citedby-count", "0"),
            "doi": d.get("prism:doi", ""),
            "link": next((L['@href'] for L in d.get('link', []) if L['@ref'] == 'scopus'), "")
        }
        lista_limpa.append(item)
    
    # 1. SALVAR CSV (Excel)
    nome_csv = f"scopus_unb_autores_{timestamp}.csv"
    df = pd.DataFrame(lista_limpa)
    df.to_csv(nome_csv, index=False, sep=';', encoding='utf-8-sig')
    
    # 2. SALVAR JSON (NOVO!)
    nome_json = f"scopus_unb_autores_{timestamp}.json"
    with open(nome_json, 'w', encoding='utf-8') as f:
        # indent=4 deixa o arquivo visualmente organizado
        # ensure_ascii=False garante que acentos fiquem corretos
        json.dump(lista_limpa, f, ensure_ascii=False, indent=4)
    
    print(f"\n🎓 SUCESSO! Foram gerados 2 arquivos:")
    print(f"   📄 CSV: {nome_csv}")
    print(f"   📦 JSON: {nome_json}")
    
# --- 5. EXECUÇÃO ---
if __name__ == "__main__":
    
    # --- CONFIGURE O PERÍODO AQUI ---
    ANO_INICIO = 2024
    ANO_FIM = 2025
    
    # --- QUERY: TUDO DA UNB ---
    # Como você quer focar "no que eles publicaram" (geral) e não num tema,
    # usamos apenas o ID da UnB.
    # Se quiser restringir, adicione " AND TITLE-ABS-KEY(tema)"
    QUERY = f"AF-ID({ID_UNB})"
    
    dados = buscar_scopus_por_periodo(QUERY, ANO_INICIO, ANO_FIM, max_items=5000)
    
    if dados:
        salvar_dados(dados)
    else:
        print("🍂 Nenhum dado encontrado neste período.")