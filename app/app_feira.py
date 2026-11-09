import os
import streamlit as st
import mysql.connector
import pandas as pd
from produtores import (
    CERTIFICACOES, SITUACOES, buscar_produtores, normalizar_documento, salvar_produtor,
)

st.set_page_config(page_title="Feira Online Sustentável - RN", layout="wide")

# A configuração informada na tela fica apenas na sessão do navegador.
def configuracao_mysql():
    return st.session_state.get("mysql_config", {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    })


def get_connection(database_name):
    return mysql.connector.connect(
        **configuracao_mysql(), database=database_name, connection_timeout=5
    )


def mensagem_conexao(erro):
    if erro.errno == 1045:
        return "O MySQL recusou o usuário ou a senha. Informe os dados de acesso ao seu banco abaixo."
    if erro.errno == 1049:
        return "O banco solicitado não foi encontrado nesse servidor. Confira se é o servidor correto."
    return "Não foi possível acessar o MySQL. Confira o servidor, as permissões e se o serviço está em execução."


def verificar_conexao():
    try:
        conn = get_connection("db_feira_online")
        conn.close()
        return
    except mysql.connector.Error as erro:
        st.warning(mensagem_conexao(erro))

    st.subheader("Conectar ao banco de dados")
    st.caption("Use a senha existente do MySQL. Ela ficará somente nesta sessão e não será salva em arquivo. Nenhuma tabela será criada ou removida.")
    config = configuracao_mysql()
    with st.form("configurar_mysql"):
        host = st.text_input("Servidor MySQL", value=config["host"])
        usuario = st.text_input("Usuário MySQL", value=config["user"])
        senha = st.text_input("Senha do MySQL", type="password")
        conectar = st.form_submit_button("Conectar e abrir dashboard")
    if conectar:
        if not host.strip() or not usuario.strip():
            st.error("Preencha o servidor e o usuário.")
        else:
            nova_config = {"host": host.strip(), "user": usuario.strip(), "password": senha}
            try:
                conn = mysql.connector.connect(
                    **nova_config, database="db_feira_online", connection_timeout=5
                )
                conn.close()
            except mysql.connector.Error as erro:
                st.error(mensagem_conexao(erro))
            else:
                st.session_state["mysql_config"] = nova_config
                st.rerun()
    st.stop()


def query_df(sql, db="db_feira_online", params=None):
    conn = None
    try:
        conn = get_connection(db)
        return pd.read_sql(sql, conn, params=params)
    except (mysql.connector.Error, pd.errors.DatabaseError):
        st.error(f"Não foi possível consultar o banco {db}. Confira o acesso e a existência das tabelas necessárias.")
        st.stop()
    finally:
        if conn is not None:
            conn.close()

def execute_sql(sql, params=None, db="db_feira_online"):
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    cursor.close()
    conn.close()

st.title("🌱 Feira Online Sustentável — Gestão e Inteligência de Mercado")
st.markdown("Plataforma integrada de comercialização da agricultura familiar e análise do abastecimento regional no Rio Grande do Norte.")

verificar_conexao()

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

            ### CORREÇÃO: Verificação adicionada para evitar erro (KeyError) se não houver produtores ou categorias cadastradas
            if prod_opcoes and cat_opcoes:
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
            else:
                st.warning("Cadastre produtores e categorias antes de adicionar produtos.")
                # Botão dummy apenas para manter o layout do st.form que exige um submit_button
                st.form_submit_button("Salvar Produto", disabled=True) 

    # --- ATUALIZAR PRODUTO ---
    with col_upd:
        st.markdown("### ✏️ Ajustar Preço e Estoque")
        with st.form("form_update_produto"):
            mapa_prod = {f"#{r['id_produto']} - {r['nome_produto']}": r for _, r in produtos_df.iterrows()}
            
            ### CORREÇÃO: Verificação adicionada para evitar erro (KeyError) se não houver produtos cadastrados
            if mapa_prod:
                prod_chave = st.selectbox("Selecione o Item", list(mapa_prod.keys()))
                registro_atual = mapa_prod[prod_chave]

                novo_preco = st.number_input("Novo Preço Unitário (R$)", min_value=0.50, value=float(registro_atual["preco_unitario"]), step=0.50)
                novo_estoque = st.number_input("Novo Saldo de Estoque", min_value=0.0, value=float(registro_atual["estoque_disponivel"]), step=1.0)

                if st.form_submit_button("Salvar Alterações"):
                    sql_upd = "UPDATE tb_produto SET preco_unitario = %s, estoque_disponivel = %s WHERE id_produto = %s"
                    execute_sql(sql_upd, (novo_preco, novo_estoque, int(registro_atual["id_produto"])))
                    st.info("Dados do produto atualizados com sucesso!")
                    st.rerun()
            else:
                st.info("Nenhum produto disponível para edição.")
                st.form_submit_button("Salvar Alterações", disabled=True)

    # --- REMOVER PRODUTO ---
    with col_del:
        st.markdown("### 🗑️ Retirar do Catálogo")
        with st.form("form_delete_produto"):
            ### CORREÇÃO: Reaproveita a verificação 'mapa_prod' para evitar erro (KeyError) aqui também
            if mapa_prod:
                prod_del_chave = st.selectbox("Selecione o Item para Remoção", list(mapa_prod.keys()))
                id_del = int(mapa_prod[prod_del_chave]["id_produto"])

                if st.form_submit_button("Confirmar Remoção"):
                    try:
                        execute_sql("DELETE FROM tb_produto WHERE id_produto = %s", (id_del,))
                        st.warning(f"Item #{id_del} removido do catálogo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Não é possível remover um item que já possui pedidos vinculados: {e}")
            else:
                st.info("Nenhum produto disponível para remoção.")
                st.form_submit_button("Confirmar Remoção", disabled=True)

# ==============================================================================
# ABA 3: REDE DE PRODUTORES
# ==============================================================================
with aba_crud_produtor:
    st.subheader("Cadastro e edição de produtores")
    st.caption("Busque pelo CPF/CNPJ para editar. A inativação preserva o cadastro e seu histórico.")
    mensagem = st.session_state.pop("produtor_mensagem", None)
    if mensagem:
        st.success(mensagem)

    with st.form("buscar_produtor"):
        documento_busca = st.text_input("Buscar por CPF ou CNPJ", help="Digite com ou sem pontuação.")
        buscar = st.form_submit_button("Buscar produtor")
    if buscar:
        st.session_state.pop("produtor_resultados", None)
        st.session_state["produtor_versao"] = st.session_state.get("produtor_versao", 0) + 1
        try:
            encontrados = buscar_produtores(get_connection, documento_busca)
            st.session_state["produtor_resultados"] = encontrados
            if not encontrados:
                st.info("Nenhum produtor encontrado. Use o cadastro abaixo.")
        except ValueError as erro:
            st.error(str(erro))
        except mysql.connector.Error:
            st.error("Não foi possível consultar o banco. Verifique a conexão e tente novamente.")

    encontrados = st.session_state.get("produtor_resultados", [])
    original = None
    if encontrados:
        if len(encontrados) > 1:
            st.warning("Há cadastros antigos com o mesmo documento. Selecione pelo código; nenhum será removido.")
        codigo = st.selectbox(
            "Produtor encontrado — selecione para editar",
            [r["id_produtor"] for r in encontrados],
            format_func=lambda codigo: next(
                f"#{r['id_produtor']} — {r['nome_produtor']} ({r['situacao']})"
                for r in encontrados if r["id_produtor"] == codigo
            ),
            key=f"selecionar_produtor_{st.session_state.get('produtor_versao', 0)}",
        )
        original = next(r for r in encontrados if r["id_produtor"] == codigo)
        if st.button("Cancelar edição / Novo produtor"):
            st.session_state.pop("produtor_resultados", None)
            st.session_state["produtor_versao"] = st.session_state.get("produtor_versao", 0) + 1
            st.rerun()

    registro = original or {}
    st.markdown("### Editar produtor" if original else "### Cadastrar produtor")
    st.caption("Campos com * são obrigatórios. Entidade/associação e contato são opcionais.")
    if original and len(normalizar_documento(original["cpf_cnpj"])) not in (11, 14):
        st.warning("Documento antigo incompleto: confira e corrija o CPF/CNPJ. Você pode atualizar os demais dados sem alterá-lo.")
    chave_form = f"produtor_{registro.get('id_produtor', 'novo')}_{st.session_state.get('produtor_versao', 0)}"
    with st.form(chave_form):
        c1, c2, c3 = st.columns(3)
        dados = {}
        dados["nome_produtor"] = c1.text_input("Nome completo do produtor *", value=registro.get("nome_produtor", ""), max_chars=150)
        dados["cpf_cnpj"] = c2.text_input("CPF ou CNPJ *", value=registro.get("cpf_cnpj", ""), max_chars=20)
        dados["tipo_certificacao"] = c3.selectbox("Modalidade de certificação *", CERTIFICACOES, index=CERTIFICACOES.index(registro.get("tipo_certificacao", "OCS")))
        dados["entidade_certificadora"] = c1.text_input("Entidade / Associação (opcional)", value=registro.get("entidade_certificadora") or "", max_chars=200)
        dados["cidade"] = c2.text_input("Município *", value=registro.get("cidade", "NATAL"), max_chars=100)
        dados["uf"] = c3.text_input("Estado (UF) *", value=registro.get("uf", "RN"), max_chars=2)
        dados["escopo_producao"] = c1.text_input("Escopo de produção *", value=registro.get("escopo_producao", "PRODUCAO PRIMARIA VEGETAL"), max_chars=150)
        dados["contato"] = c2.text_input("Contato (opcional)", value=registro.get("contato") or "", max_chars=120)
        dados["situacao"] = c3.selectbox("Situação *", SITUACOES, index=SITUACOES.index(registro.get("situacao", "ATIVO")))
        salvar = st.form_submit_button("Salvar alterações" if original else "Cadastrar produtor")
        if salvar:
            try:
                salvar_produtor(get_connection, dados, original)
            except ValueError as erro:
                st.error(str(erro))
            except mysql.connector.IntegrityError:
                st.error("Documento já cadastrado ou conflito de dados. Busque o produtor pelo CPF/CNPJ para editar.")
            except mysql.connector.Error:
                st.error("Não foi possível salvar. Verifique a conexão com o banco e tente novamente.")
            else:
                st.session_state["produtor_mensagem"] = "Produtor atualizado com sucesso!" if original else "Produtor cadastrado com sucesso!"
                st.session_state.pop("produtor_resultados", None)
                st.session_state["produtor_versao"] = st.session_state.get("produtor_versao", 0) + 1
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

    ### CORREÇÃO: Erro de sintaxe (parêntese no final do dicionário) foi corrigido para chave '}' 
    opcoes_metricas = {
        "Volume Total Comercializado (kg)": {"coluna": "Total_kg", "cor": "#10b981"}, # Verde
        "Média Mensal Comercializada (kg)": {"coluna": "Media_Mensal_kg", "cor": "#3b82f6"}, # Azul
        "Maior Volume Registrado no Mês (kg)": {"coluna": "Max_kg", "cor": "#f59e0b"}, # Laranja
        "Menor Volume Registrado no Mês (kg)": {"coluna": "Min_kg", "cor": "#ec4899"}, # Rosa
        "Valor Total Movimentado (R$)": {"coluna": "Total_Reais", "cor": "#8b5cf6"},  # Roxo
        "Total de Produtores / Clientes Atendidos": {"coluna": "Clientes_Atendidos", "cor": "#06b6d4"} # Azul claro (ERRO CORRIGIDO AQUI)
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
