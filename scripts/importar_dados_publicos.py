import os
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

import pandas as pd
import mysql.connector
import numpy as np

# Conecte ao seu banco de dados (coloque a sua palavra-passe)
conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "localhost"), 
    user=os.getenv("MYSQL_USER", "root"), 
    password=os.getenv("MYSQL_PASSWORD", ""), 
    database="db_analise_publica"
)
cursor = conn.cursor()

def inserir_dados(tabela, csv_file, query_insert):
    print(f"A ler o ficheiro {csv_file}...")
    df = pd.read_csv(PROCESSED_DIR / csv_file, sep=";")
    # Substituir possíveis NaNs do Pandas por None (NULL no MySQL)
    df = df.replace({np.nan: None}) 
    
    # Converter o DataFrame numa lista de tuplos
    dados = [tuple(x) for x in df.to_numpy()]
    
    print(f"A inserir {len(dados)} registos na tabela {tabela}...")
    cursor.executemany(query_insert, dados)
    conn.commit()
    print("Sucesso!\n")

# 1. Importar Venda em Balcão
query_vb = """INSERT INTO conab_venda_balcao 
              (num_ano_gravacao, num_mes_gravacao, municipio_armazem_venda, uf, qtd_produto_kg, valor_comercializado, numero_atendimentos, clientes_atendidos) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
inserir_dados("conab_venda_balcao", "venda_balcao_limpo.csv", query_vb)

# 2. Importar Oferta e Demanda
query_od = """INSERT INTO conab_oferta_demanda 
              (produto, id_produto, dsc_safra, estoque_inicial_1000t, producao_1000t, importacao_1000t, consumo_1000t, exportacao_1000t, estoque_final_1000t) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
inserir_dados("conab_oferta_demanda", "oferta_demanda_limpo.csv", query_od)

# 3. Importar CNPO
query_cnpo = """INSERT INTO cnpo_produtores 
                (tipo_entidade, entidade, pais, uf, cidade, situacao, cnpf_cnpj_nif, nome_produtor, escopo, atividade, contato, ano, mes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
inserir_dados("cnpo_produtores", "cnpo_limpo.csv", query_cnpo)

cursor.close()
conn.close()
print("Todas as tabelas foram carregadas. O seu dashboard já deve apresentar os gráficos!")
