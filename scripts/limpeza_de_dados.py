from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd

# 1. Leitura correta dos 3 datasets
xls = pd.ExcelFile(RAW_DIR / "Cadastro Nacional de Produtores Orgânicos (CNPO).xlsx")
cnpo = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
venda_balcao = pd.read_csv(RAW_DIR / "Venda_Balcao.csv", sep=";")
oferta_demanda = pd.read_csv(RAW_DIR / "Oferta_Demanda.csv", sep=";")

# 2. Limpeza do CNPO
for col in cnpo.select_dtypes(include="object").columns:
    cnpo[col] = cnpo[col].fillna("NAO_INFORMADO").astype(str).str.strip()

cnpo.columns = [
    "tipo_entidade", "entidade", "pais", "uf", "cidade", "situacao",
    "cnpf_cnpj_nif", "nome_produtor", "escopo", "atividade", "contato", "ano", "mes"
]
cnpo.to_csv(PROCESSED_DIR / "cnpo_limpo.csv", index=False, sep=";", encoding="utf-8")

# 3. Limpeza de Venda_Balcao
# A fonte original contém um erro de grafia; padronizar apenas no arquivo tratado.
venda_balcao = venda_balcao.rename(columns={
    "munipio_armazem_venda": "municipio_armazem_venda"
})
venda_balcao["municipio_armazem_venda"] = venda_balcao["municipio_armazem_venda"].astype(str).str.strip()
venda_balcao["uf"] = venda_balcao["uf"].astype(str).str.strip()
venda_balcao["valor_comercializado"] = (
    venda_balcao["valor_comercializado"].astype(str).str.replace(",", ".").astype(float).round(2)
)
venda_balcao.to_csv(PROCESSED_DIR / "venda_balcao_limpo.csv", index=False, sep=";", encoding="utf-8")

# 4. Limpeza de Oferta_Demanda
oferta_demanda["produto"] = oferta_demanda["produto"].astype(str).str.strip()
oferta_demanda["dsc_safra"] = oferta_demanda["dsc_safra"].astype(str).str.strip()
colunas_num_od = [
    "estoque_inicial_1000t", "producao_1000t", "importacao_1000t",
    "consumo_1000t", "exportacao_1000t", "estoque_final_1000t"
]
for col in colunas_num_od:
    oferta_demanda[col] = oferta_demanda[col].astype(str).str.replace(",", ".").astype(float).round(2)

oferta_demanda.to_csv(PROCESSED_DIR / "oferta_demanda_limpo.csv", index=False, sep=";", encoding="utf-8")
print("Arquivos CSV higienizados e exportados com sucesso!")
