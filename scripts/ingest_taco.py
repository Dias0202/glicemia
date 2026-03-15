# scripts/ingest_taco.py
import sys
import os
import pandas as pd
import logging

# Adiciona o diretório raiz ao path para importar os módulos locais
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import supabase_db

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_ingestion(csv_path: str):
    """
    Lê o arquivo CSV da tabela TACO, transforma os dados para o formato
    da tabela food_reference e realiza a inserção no Supabase em lotes (batches).
    """
    try:
        logging.info(f"Lendo o arquivo {csv_path}...")
        
        # O separador definido é ';' com base no cabeçalho fornecido.
        # Caso ocorra erro de leitura de caracteres com acentos, altere o encoding para 'latin1' ou 'cp1252'.
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        
        # Mapeamento exato das colunas do seu arquivo
        coluna_nome = 'Descrição dos alimentos' 
        coluna_carbo = 'Carboidrato (g)'

        if coluna_nome not in df.columns or coluna_carbo not in df.columns:
            raise ValueError(f"Colunas '{coluna_nome}' ou '{coluna_carbo}' não encontradas. Verifique o CSV.")

        # Limpeza de dados
        # 1. Remove linhas onde a descrição do alimento está vazia
        df = df.dropna(subset=[coluna_nome]).copy()
        
        # 2. Trata marcações textuais comuns na TACO que não são numéricas
        df[coluna_carbo] = df[coluna_carbo].replace(['NA', 'Tr', '*'], 0)
        
        # 3. Preenche valores nulos com 0
        df[coluna_carbo] = df[coluna_carbo].fillna(0)
        
        # 4. Converte vírgulas decimais para pontos e força a conversão para numérico (float)
        df[coluna_carbo] = df[coluna_carbo].astype(str).str.replace(',', '.')
        df[coluna_carbo] = pd.to_numeric(df[coluna_carbo], errors='coerce').fillna(0)

        # Preparação da lista de dicionários para inserção
        records_to_insert = []
        for _, row in df.iterrows():
            nome_alimento = str(row[coluna_nome]).strip()
            
            # Ignora eventuais linhas de categoria vazias
            if not nome_alimento or nome_alimento.lower() == 'nan':
                continue

            record = {
                "food_name": nome_alimento,
                "portion_size": 100.0,
                "unit": "g",
                "carbs_per_portion": round(float(row[coluna_carbo]), 2)
            }
            records_to_insert.append(record)

        # Inserção em lotes (Batch Insert)
        batch_size = 100
        total_inserted = 0
        
        logging.info(f"Iniciando inserção de {len(records_to_insert)} registros no Supabase...")
        
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i + batch_size]
            response = supabase_db.table("food_reference").insert(batch).execute()
            total_inserted += len(response.data)
            logging.info(f"Lote inserido. Progresso: {total_inserted}/{len(records_to_insert)}")

        logging.info("Ingestão concluída com sucesso.")

    except UnicodeDecodeError:
        logging.error("Erro de codificação lendo o arquivo. Altere o parâmetro encoding na linha 25 para 'latin1'.")
    except Exception as e:
        logging.error(f"Erro durante a ingestão de dados: {e}")

if __name__ == "__main__":
    # Caminho absoluto fornecido do arquivo CSV
    caminho_csv = r"C:\projetos\glycemic_bot\taco\tabelas\alimentos.csv"
    
    if not os.path.exists(caminho_csv):
        logging.error(f"O arquivo não foi encontrado no caminho especificado: {caminho_csv}")
    else:
        run_ingestion(caminho_csv)