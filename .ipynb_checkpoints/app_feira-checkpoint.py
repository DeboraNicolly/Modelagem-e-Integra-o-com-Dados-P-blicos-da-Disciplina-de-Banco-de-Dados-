import streamlit as st
import mysql.connector
import pandas as pd

st.set_page_config(page_title="Feira Online Sustentável - RN", layout="wide")

# conexão com o banco de dados
def get_connection(database_name):
    return mysql.connector.connect(
        host="localhost",
        user="debora",
        password="abacaxi123",
        database=database_name
    )

def query_df(sql, db="db_feira_online", params=None):
    conn = get_connection(db)
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df

def execute_sql(sql, params=None, db="db_feira_online"):
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    cursor.close()
    conn.close()

st.title("🌱 Feira Online Sustentável — Gestão e Inteligência de Mercado")
st.markdown("Plataforma integrada de comercialização da agricultura familiar e análise do abastecimento regional no Rio Grande do Norte.")

aba_catalogo, aba_crud_prod, aba_crud_produtor, aba_analise = st.tabs([
    "🛒 Catálogo e Faturamento",
    "📦 Gestão de Produtos",
    "👩‍🌾 Rede de Produtores",
    "📊 Inteligência de Mercado (RN)"
])

# ==============================================================================
# ABA 1: CATÁLOGO E DESEMPENHO FINANCEIRO
# ==============================================================================
with aba_catalogo:
    st.subheader("Catálogo de Alimentos Frescos Disponíveis")
    df_cat = query_df("SELECT * FROM vw_catalogo_feira")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        cidades = ["Todas"] + sorted(df_cat["cidade_origem"].unique().tolist())
        filtro_cidade = st.selectbox("Filtrar por Município de Origem:", cidades)
    with col_f2:
        categorias = ["Todas"] + sorted(df_cat["nome_categoria"].unique().tolist())
        filtro_cat = st.selectbox("Filtrar por Categoria:", categorias)

    if filtro_cidade != "Todas":
        df_cat = df_cat[df_cat["cidade_origem"] == filtro_cidade]
    if filtro_cat != "Todas":
        df_cat = df_cat[df_cat["nome_categoria"] == filtro_cat]

    df_cat_exibicao = df_cat.rename(columns={
        "id_produto": "Código",
        "nome_produto": "Produto",
        "nome_categoria": "Categoria",
        "unidade_medida": "Unidade",
        "preco_unitario": "Preço Unitário (R$)",
        "estoque_disponivel": "Estoque Disponível",
        "id_produtor": "Cód. Produtor",
        "nome_produtor": "Produtor",
        "tipo_certificacao": "Certificação",
        "cidade_origem": "Município",
        "uf_origem": "UF",
        "status_produtor": "Situação"
    })
    st.dataframe(df_cat_exibicao, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Desempenho de Vendas por Produtor")
    df_fat = query_df("SELECT * FROM vw_faturamento_produtor ORDER BY receita_total_reais DESC")
    df_fat_exibicao = df_fat.rename(columns={
        "id_produtor": "Código",
        "nome_produtor": "Produtor",
        "cidade": "Município",
        "tipo_certificacao": "Modalidade",
        "total_pedidos": "Pedidos Realizados",
        "volume_itens_vendidos": "Itens Vendidos",
        "receita_total_reais": "Receita Total (R$)"
    })
    st.dataframe(df_fat_exibicao, use_container_width=True, hide_index=True)

# ==============================================================================
# ABA 2: GESTÃO DE PRODUTOS
# ==============================================================================
with aba_crud_prod:
    col_ins, col_upd, col_del = st.columns(3)

    produtores_df = query_df("SELECT id_produtor, nome_produtor, cidade FROM tb_produtor WHERE situacao='ATIVO'")
    categorias_df = query_df("SELECT id_categoria, nome_categoria FROM tb_categoria")
    produtos_df = query_df("SELECT id_produto, nome_produto, preco_unitario, estoque_disponivel FROM tb_produto")

    # --- CADASTRAR PRODUTO ---
    with col_ins:
        st.markdown("### ➕ Novo Produto")
        with st.form("form_insert_produto"):
            prod_opcoes = {f"{r['nome_produtor']} ({r['cidade']})": r["id_produtor"] for _, r in produtores_df.iterrows()}
            cat_opcoes = {r["nome_categoria"]: r["id_categoria"] for _, r in categorias_df.iterrows()}

            produtor_sel = st.selectbox("Produtor Responsável", list(prod_opcoes.keys()))
            categoria_sel = st.selectbox("Categoria", list(cat_opcoes.keys()))
            nome_prod = st.text_input("Nome do Alimento / Produto")
            unidade = st.selectbox("Unidade de Comercialização", ["kg", "unidade", "maco", "bandeja", "duzia", "litro"])
            preco = st.number_input("Preço Unitário (R$)", min_value=0.50, value=5.00, step=0.50)
            estoque = st.number_input("Quantidade em Estoque", min_value=0.0, value=20.0, step=1.0)
            organico = st.checkbox("Produto Orgânico Certificado", value=True)

            if st.form_submit_button("Salvar Produto"):
                sql_ins = """
                    INSERT INTO tb_produto 
                    (id_produtor, id_categoria, nome_produto, unidade_medida, preco_unitario, estoque_disponivel, organico_certificado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                execute_sql(sql_ins, (prod_opcoes[produtor_sel], cat_opcoes[categoria_sel], nome_prod, unidade, preco, estoque, organico))
                st.success(f"Produto '{nome_prod}' adicionado ao catálogo!")
                st.rerun()

    # --- ATUALIZAR PRODUTO ---
    with col_upd:
        st.markdown("### ✏️ Ajustar Preço e Estoque")
        with st.form("form_update_produto"):
            mapa_prod = {f"#{r['id_produto']} - {r['nome_produto']}": r for _, r in produtos_df.iterrows()}
            prod_chave = st.selectbox("Selecione o Item", list(mapa_prod.keys()))
            registro_atual = mapa_prod[prod_chave]

            novo_preco = st.number_input("Novo Preço Unitário (R$)", min_value=0.50, value=float(registro_atual["preco_unitario"]), step=0.50)
            novo_estoque = st.number_input("Novo Saldo de Estoque", min_value=0.0, value=float(registro_atual["estoque_disponivel"]), step=1.0)

            if st.form_submit_button("Salvar Alterações"):
                sql_upd = "UPDATE tb_produto SET preco_unitario = %s, estoque_disponivel = %s WHERE id_produto = %s"
                execute_sql(sql_upd, (novo_preco, novo_estoque, int(registro_atual["id_produto"])))
                st.info("Dados do produto atualizados com sucesso!")
                st.rerun()

    # --- REMOVER PRODUTO ---
    with col_del:
        st.markdown("### 🗑️ Retirar do Catálogo")
        with st.form("form_delete_produto"):
            prod_del_chave = st.selectbox("Selecione o Item para Remoção", list(mapa_prod.keys()))
            id_del = int(mapa_prod[prod_del_chave]["id_produto"])

            if st.form_submit_button("Confirmar Remoção"):
                try:
                    execute_sql("DELETE FROM tb_produto WHERE id_produto = %s", (id_del,))
                    st.warning(f"Item #{id_del} removido do catálogo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não é possível remover um item que já possui pedidos vinculados: {e}")

# ==============================================================================
# ABA 3: REDE DE PRODUTORES
# ==============================================================================
with aba_crud_produtor:
    st.subheader("Credenciamento de Produtor Familiar / Orgânico")
    with st.form("form_novo_produtor"):
        c1, c2, c3 = st.columns(3)
        nome_p = c1.text_input("Nome Completo do Produtor")
        doc_p = c2.text_input("CPF ou CNPJ")
        cert_p = c3.selectbox("Modalidade de Certificação", ["OCS", "OPAC", "CERTIFICADORA", "AGRICULTURA_FAMILIAR"])
        ent_p = c1.text_input("Associação / Organização de Controle Social")
        cid_p = c2.text_input("Município", value="NATAL")
        uf_p = c3.text_input("Estado (UF)", value="RN", max_chars=2)

        if st.form_submit_button("Cadastrar Produtor"):
            sql_p = """
                INSERT INTO tb_produtor (nome_produtor, cpf_cnpj, tipo_certificacao, entidade_certificadora, cidade, uf)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            execute_sql(sql_p, (nome_p, doc_p, cert_p, ent_p, cid_p.upper(), uf_p.upper()))
            st.success(f"Produtor {nome_p} credenciado com sucesso!")
            st.rerun()

    st.subheader("Produtores Credenciados na Plataforma")
    df_produtores = query_df("SELECT id_produtor, nome_produtor, cpf_cnpj, tipo_certificacao, entidade_certificadora, cidade, uf, situacao FROM tb_produtor")
    df_produtores_exib = df_produtores.rename(columns={
        "id_produtor": "Código",
        "nome_produtor": "Produtor",
        "cpf_cnpj": "Documento",
        "tipo_certificacao": "Certificação",
        "entidade_certificadora": "Entidade / Associação",
        "cidade": "Município",
        "uf": "UF",
        "situacao": "Situação"
    })
    st.dataframe(df_produtores_exib, use_container_width=True, hide_index=True)

# ==============================================================================
# ABA 4: INTELIGÊNCIA DE MERCADO E DADOS PÚBLICOS
# ==============================================================================
with aba_analise:
    st.subheader("Desempenho Regional — Polos de Abastecimento no Rio Grande do Norte")
    st.caption("Fonte: Programa de Vendas em Balcão (CONAB) e Cadastro Nacional de Produtores Orgânicos (MAPA).")

    sql_vb_rn = """
        SELECT municipio_armazem_venda AS Polo_RN,
               SUM(qtd_produto_kg) AS Total_kg,
               ROUND(AVG(qtd_produto_kg), 2) AS Media_Mensal_kg,
               MIN(qtd_produto_kg) AS Min_kg,
               MAX(qtd_produto_kg) AS Max_kg,
               ROUND(SUM(valor_comercializado), 2) AS Total_Reais,
               SUM(clientes_atendidos) AS Clientes_Atendidos
        FROM conab_venda_balcao
        WHERE uf = 'RN'
        GROUP BY municipio_armazem_venda
        ORDER BY Total_kg DESC
    """
    df_rn = query_df(sql_vb_rn, db="db_analise_publica")

    # Renomeando as colunas para apresentação executiva na tabela
    df_rn_exibicao = df_rn.rename(columns={
        "Polo_RN": "Polo Regional (RN)",
        "Total_kg": "Volume Total (kg)",
        "Media_Mensal_kg": "Média Mensal (kg)",
        "Min_kg": "Menor Volume Mensal (kg)",
        "Max_kg": "Maior Volume Mensal (kg)",
        "Total_Reais": "Valor Movimentado (R$)",
        "Clientes_Atendidos": "Pequenos Produtores Atendidos"
    })
    st.dataframe(df_rn_exibicao, use_container_width=True, hide_index=True)

    st.divider()

    # gráfico interativo
    opcoes_metricas = {
        "Volume Total Comercializado (kg)": {"coluna": "Total_kg", "cor": "#10b981"}, # Verde
        "Média Mensal Comercializada (kg)": {"coluna": "Media_Mensal_kg", "cor": "#3b82f6"}, # Azul
        "Maior Volume Registrado no Mês (kg)": {"coluna": "Max_kg", "cor": "#f59e0b"}, # Laranja
        "Menor Volume Registrado no Mês (kg)": {"coluna": "Min_kg", "cor": "#ec4899"}, # Rosa
        "Valor Total Movimentado (R$)": {"coluna": "Total_Reais", "cor": "#8b5cf6"},  # Roxo
        "Total de Produtores / Clientes Atendidos": {"coluna": "Clientes_Atendidos", "cor": "#06b6d4") # Azul claro
    }

    col_sel, col_info = st.columns([2, 1])
    with col_sel:
        metrica_escolhida = st.selectbox(
            "Selecione o indicador para visualização gráfica:",
            list(opcoes_metricas.keys())
        )

    config_atual = opcoes_metricas[metrica_escolhida]
    coluna_dados = config_atual["coluna"]
    cor_grafico = config_atual["cor"]

    with col_info:
        valor_destaque = df_rn[coluna_dados].max()
        polo_lider = df_rn.loc[df_rn[coluna_dados].idxmax(), "Polo_RN"]
        st.metric(
            label=f"Destaque Estadual ({polo_lider})",
            value=f"{valor_destaque:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    st.markdown(f"#### Comparativo entre Polos — {metrica_escolhida}")
    st.bar_chart(
        data=df_rn.set_index("Polo_RN")[coluna_dados],
        color=cor_grafico,
        use_container_width=True
    )
