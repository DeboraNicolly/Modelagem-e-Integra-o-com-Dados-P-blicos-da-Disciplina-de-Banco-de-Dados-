import os
import re
import streamlit as st
import mysql.connector
import pandas as pd
import altair as alt


st.set_page_config(page_title="Feira Online Sustentável - RN", layout="wide")

# Regras de cadastro, busca e edição de produtores
CERTIFICACOES = ["OCS", "OPAC", "CERTIFICADORA", "AGRICULTURA_FAMILIAR"]
SITUACOES = ["ATIVO", "INATIVO", "SUSPENSO"]
UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
CAMPOS = (
    "nome_produtor", "cpf_cnpj", "tipo_certificacao", "entidade_certificadora",
    "escopo_producao", "cidade", "uf", "contato", "situacao",
)


def normalizar_documento(documento):
    return re.sub(r"[^0-9]", "", str(documento or ""))


def buscar_produtores(conectar, documento, por_codigo=False):
    if por_codigo:
        codigo = str(documento or "").strip()
        if not re.fullmatch(r"[0-9]+", codigo) or int(codigo) <= 0:
            raise ValueError("Informe um código de produtor válido, como o exibido na tabela.")
    else:
        chave = normalizar_documento(documento)
        if not chave:
            raise ValueError("Informe o CPF ou CNPJ para buscar.")
    conn = conectar("db_feira_online")
    try:
        cursor = conn.cursor(dictionary=True)
        try:
            if por_codigo:
                cursor.execute("SELECT * FROM tb_produtor WHERE id_produtor = %s", (int(codigo),))
                return cursor.fetchall()
            cursor.execute("SELECT * FROM tb_produtor ORDER BY id_produtor")
            return [r for r in cursor.fetchall() if normalizar_documento(r["cpf_cnpj"]) == chave]
        finally:
            cursor.close()
    finally:
        conn.close()


def validar_dados(dados, original=None):
    valores = {campo: str(dados.get(campo) or "").strip() for campo in CAMPOS}
    doc = valores["cpf_cnpj"]
    chave = normalizar_documento(doc)
    # Permite corrigir outros dados de cadastros legados com documento incompleto.
    documento_inalterado = original is not None and doc == original["cpf_cnpj"]
    if not documento_inalterado:
        if re.search(r"[^0-9. /-]", doc) or len(chave) not in (11, 14):
            raise ValueError("Informe um CPF com 11 dígitos ou CNPJ com 14 dígitos.")
        valores["cpf_cnpj"] = chave
    for campo, rotulo in (("nome_produtor", "Nome"), ("cidade", "Município"), ("escopo_producao", "Escopo de produção")):
        if not valores[campo]:
            raise ValueError(f"{rotulo} é obrigatório.")
    valores["uf"] = valores["uf"].upper()
    valores["cidade"] = valores["cidade"].upper()
    if valores["uf"] not in UFS:
        raise ValueError("Informe uma UF válida.")
    if valores["tipo_certificacao"] not in CERTIFICACOES:
        raise ValueError("Selecione a modalidade de certificação.")
    if valores["situacao"] not in SITUACOES:
        raise ValueError("Selecione uma situação válida.")
    limites = {"nome_produtor": 150, "cpf_cnpj": 20, "entidade_certificadora": 200,
               "escopo_producao": 150, "cidade": 100, "contato": 120}
    for campo, limite in limites.items():
        if len(valores[campo]) > limite:
            raise ValueError(f"O campo {campo} aceita até {limite} caracteres.")
    for campo in ("entidade_certificadora", "contato"):
        valores[campo] = valores[campo] or None
    return valores


def validar_id_produtor(valor):
    texto = str(valor or "").strip()
    if not re.fullmatch(r"[0-9]+", texto) or not 1 <= int(texto) <= 2147483647:
        raise ValueError("Informe um ID do produtor inteiro entre 1 e 2147483647.")
    return int(texto)


def salvar_produtor(conectar, dados, original=None):
    """Serializa gravações da aplicação e verifica CPF sem máscara antes de salvar."""
    id_informado = validar_id_produtor(dados.get("id_produtor"))
    if original is not None and id_informado != int(original["id_produtor"]):
        raise ValueError("O ID do produtor não pode ser alterado durante a edição.")
    conn = conectar("db_feira_online")
    cursor = None
    bloqueado = False
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT GET_LOCK('db_feira_online.produtores', 10) AS adquirido")
        bloqueado = cursor.fetchone()["adquirido"] == 1
        if not bloqueado:
            raise ValueError("Outro cadastro está sendo salvo. Tente novamente.")
        cursor.execute("SELECT * FROM tb_produtor ORDER BY id_produtor FOR UPDATE")
        registros = cursor.fetchall()
        if original is None and any(int(r["id_produtor"]) == id_informado for r in registros):
            raise ValueError(f"O ID {id_informado} já está sendo utilizado. Informe outro ID ou busque esse produtor para editar.")
        valores = validar_dados(dados, original)
        id_atual = int(original["id_produtor"]) if original is not None else None
        if original is not None:
            atual = next((r for r in registros if r["id_produtor"] == id_atual), None)
            if atual is None or any(atual[c] != original[c] for c in CAMPOS):
                raise ValueError("O cadastro foi alterado em outra sessão. Busque novamente antes de salvar.")
        chave = normalizar_documento(valores["cpf_cnpj"])
        duplicados = [r for r in registros if r["id_produtor"] != id_atual
                      and normalizar_documento(r["cpf_cnpj"]) == chave]
        if duplicados and (original is None or chave != normalizar_documento(original["cpf_cnpj"])):
            raise ValueError("CPF/CNPJ já cadastrado. Use a busca para editar o produtor existente.")
        params = tuple(valores[c] for c in CAMPOS)
        if original is None:
            cursor.execute(
                "INSERT INTO tb_produtor (id_produtor, " + ", ".join(CAMPOS) + ") VALUES (" + ", ".join(["%s"] * (len(CAMPOS) + 1)) + ")",
                (id_informado,) + params,
            )
        else:
            cursor.execute(
                "UPDATE tb_produtor SET " + ", ".join(c + " = %s" for c in CAMPOS) + " WHERE id_produtor = %s",
                params + (id_atual,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            if cursor is not None:
                try:
                    if bloqueado:
                        cursor.execute("SELECT RELEASE_LOCK('db_feira_online.produtores') AS liberado")
                        cursor.fetchone()
                finally:
                    cursor.close()
        finally:
            conn.close()



# Base independente, criada exclusivamente para demonstração com dados fictícios.
import sqlite3
from pathlib import Path

SCHEMA_DEMO = "-- 1. Tabela de Produtores (alinhada à estrutura do CNPO/MAPA)\nCREATE TABLE tb_produtor (\n    id_produtor INTEGER PRIMARY KEY AUTOINCREMENT,\n    nome_produtor VARCHAR(150) NOT NULL,\n    cpf_cnpj VARCHAR(20) NOT NULL UNIQUE,\n    tipo_certificacao TEXT NOT NULL DEFAULT 'OCS',\n    entidade_certificadora VARCHAR(200),\n    escopo_producao VARCHAR(150) NOT NULL DEFAULT 'PRODUCAO PRIMARIA VEGETAL',\n    cidade VARCHAR(100) NOT NULL,\n    uf CHAR(2) NOT NULL DEFAULT 'RN',\n    contato VARCHAR(120),\n    situacao TEXT NOT NULL DEFAULT 'ATIVO',\n    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\n-- 2. Tabela de Categorias\nCREATE TABLE tb_categoria (\n    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,\n    nome_categoria VARCHAR(80) NOT NULL UNIQUE,\n    descricao VARCHAR(255)\n);\n\n-- 3. Tabela de Produtos da Feira Online\nCREATE TABLE tb_produto (\n    id_produto INTEGER PRIMARY KEY AUTOINCREMENT,\n    id_produtor INT NOT NULL,\n    id_categoria INT NOT NULL,\n    nome_produto VARCHAR(120) NOT NULL,\n    unidade_medida TEXT NOT NULL DEFAULT 'kg',\n    preco_unitario DECIMAL(10, 2) NOT NULL CHECK (preco_unitario > 0),\n    estoque_disponivel DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (estoque_disponivel >= 0),\n    organico_certificado BOOLEAN NOT NULL DEFAULT TRUE,\n    CONSTRAINT fk_produto_produtor FOREIGN KEY (id_produtor) \n        REFERENCES tb_produtor(id_produtor) ON DELETE CASCADE ON UPDATE CASCADE,\n    CONSTRAINT fk_produto_categoria FOREIGN KEY (id_categoria) \n        REFERENCES tb_categoria(id_categoria) ON DELETE RESTRICT ON UPDATE CASCADE\n);\n\n-- 4. Tabela de Clientes\nCREATE TABLE tb_cliente (\n    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,\n    nome_cliente VARCHAR(150) NOT NULL,\n    email VARCHAR(120) NOT NULL UNIQUE,\n    telefone VARCHAR(30),\n    cidade VARCHAR(100) NOT NULL DEFAULT 'Natal',\n    uf CHAR(2) NOT NULL DEFAULT 'RN',\n    endereco_entrega VARCHAR(255) NOT NULL\n);\n\n-- 5. Tabela de Pedidos\nCREATE TABLE tb_pedido (\n    id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,\n    id_cliente INT NOT NULL,\n    data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,\n    status_pedido TEXT NOT NULL DEFAULT 'CONFIRMADO',\n    modalidade_entrega TEXT NOT NULL DEFAULT 'ENTREGA_DOMICILIO',\n    CONSTRAINT fk_pedido_cliente FOREIGN KEY (id_cliente) \n        REFERENCES tb_cliente(id_cliente) ON DELETE RESTRICT ON UPDATE CASCADE\n);\n\n-- 6. Tabela Associativa de Itens do Pedido\nCREATE TABLE tb_item_pedido (\n    id_item INTEGER PRIMARY KEY AUTOINCREMENT,\n    id_pedido INT NOT NULL,\n    id_produto INT NOT NULL,\n    quantidade DECIMAL(10, 2) NOT NULL CHECK (quantidade > 0),\n    preco_unitario_venda DECIMAL(10, 2) NOT NULL CHECK (preco_unitario_venda > 0),\n    CONSTRAINT fk_item_pedido FOREIGN KEY (id_pedido) \n        REFERENCES tb_pedido(id_pedido) ON DELETE CASCADE ON UPDATE CASCADE,\n    CONSTRAINT fk_item_produto FOREIGN KEY (id_produto) \n        REFERENCES tb_produto(id_produto) ON DELETE RESTRICT ON UPDATE CASCADE\n);\n\n-- VIEW 1: Catálogo Completo da Feira\nCREATE VIEW vw_catalogo_feira AS\nSELECT \n    p.id_produto,\n    p.nome_produto,\n    c.nome_categoria,\n    p.unidade_medida,\n    p.preco_unitario,\n    p.estoque_disponivel,\n    pr.id_produtor,\n    pr.nome_produtor,\n    pr.tipo_certificacao,\n    pr.cidade AS cidade_origem,\n    pr.uf AS uf_origem,\n    pr.situacao AS status_produtor\nFROM tb_produto p\nINNER JOIN tb_produtor pr ON p.id_produtor = pr.id_produtor\nINNER JOIN tb_categoria c ON p.id_categoria = c.id_categoria;\n\n-- VIEW 2: Desempenho Financeiro e Volume de Vendas por Produtor\nCREATE VIEW vw_faturamento_produtor AS\nSELECT \n    pr.id_produtor,\n    pr.nome_produtor,\n    pr.cidade,\n    pr.tipo_certificacao,\n    COUNT(DISTINCT ip.id_pedido) AS total_pedidos,\n    COALESCE(SUM(ip.quantidade), 0) AS volume_itens_vendidos,\n    COALESCE(ROUND(SUM(ip.quantidade * ip.preco_unitario_venda), 2), 0.00) AS receita_total_reais\nFROM tb_produtor pr\nLEFT JOIN tb_produto p ON pr.id_produtor = p.id_produtor\nLEFT JOIN tb_item_pedido ip ON p.id_produto = ip.id_produto\nGROUP BY pr.id_produtor, pr.nome_produtor, pr.cidade, pr.tipo_certificacao;\n\n\nCREATE TABLE conab_venda_balcao (id_venda INTEGER PRIMARY KEY, municipio_armazem_venda TEXT, uf TEXT, qtd_produto_kg INTEGER, valor_comercializado REAL, clientes_atendidos INTEGER);\n"



NOMES_DEMO = [
    "Ana Beatriz Ferreira da Silva", "Bruno Henrique Oliveira Santos", "Clara Maria Souza Ribeiro",
    "Daniel Augusto Costa Lima", "Elisa Cristina Nunes de Almeida", "Fábio Alexandre Pereira Rocha",
    "Gabriela Vitória Martins Alves", "Hugo Leonardo Barbosa Mendes", "Iara Carolina Gomes Duarte",
    "Jonas Miguel Carvalho Araújo", "Lara Patrícia Fernandes Melo", "Marcos Vinícius Batista Freire",
    "Nina Gabriela Monteiro Campos", "Otávio César Rodrigues Lopes", "Paula Renata Teixeira Moura",
    "Rafael Antônio Dias Cavalcante", "Sara Luísa Azevedo Pinheiro", "Tiago José Cardoso Farias",
    "Vera Lúcia Moreira Dantas", "William Eduardo Castro Tavares", "Yara Letícia Machado Bezerra",
    "Zélia Aparecida Ramos Vieira", "Bento Francisco Correia Leite", "Célia Regina Andrade Medeiros",
    "Adriana Helena Freitas Queiroz", "Carlos Alberto Macedo Soares", "Débora Camila Sales Brito",
    "Eduardo Felipe Torres Guimarães", "Fernanda Isabel Cunha Pires", "Gustavo André Paiva Siqueira",
    "Helena Cecília Borges Nascimento", "Igor Samuel Matos Peixoto", "Juliana Priscila Reis Fonseca",
    "Leandro Márcio Viana Assunção", "Márcia Elaine Coelho Amorim", "Nelson Roberto Xavier dos Santos",
]


def cpf_ficticio(indice):
    # Geração matemática para teste; não consulta nem identifica pessoas reais.
    base = str(137285409 + indice * 1739207)
    for peso in (10, 11):
        resto = sum(int(d) * (peso - i) for i, d in enumerate(base)) % 11
        base += str(0 if resto < 2 else 11 - resto)
    return f"{base[:3]}.{base[3:6]}.{base[6:9]}-{base[9:]}"


def ampliar_dados_demo(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS demo_versoes (versao INTEGER PRIMARY KEY)")
    if conn.execute("SELECT 1 FROM demo_versoes WHERE versao=2").fetchone():
        return
    cidades = ['NATAL', 'MOSSORO', 'APODI', 'CAICO', 'CURRAIS NOVOS', 'SAO PAULO DO POTENGI']
    for i, nome in enumerate(NOMES_DEMO, 1):
        atual = conn.execute("SELECT nome_produtor,cpf_cnpj FROM tb_produtor WHERE id_produtor=?",(i,)).fetchone()
        if atual is not None:
            if ' Exemplo ' in atual[0]:
                conn.execute("UPDATE tb_produtor SET nome_produtor=? WHERE id_produtor=?",(nome,i))
                if atual[1] in ('',f'{i:011d}'):
                    conn.execute("UPDATE tb_produtor SET cpf_cnpj=? WHERE id_produtor=?",(cpf_ficticio(i),i))
        else:
            conn.execute("INSERT INTO tb_produtor(id_produtor,nome_produtor,cpf_cnpj,tipo_certificacao,entidade_certificadora,escopo_producao,cidade,uf,contato,situacao) VALUES (?,?,?,?,?,?,?,?,?,?)",(
                i,nome,cpf_ficticio(i),CERTIFICACOES[(i-1)%4],None if i%3==0 else f'Associação Fictícia {1+i%4}',
                'PRODUCAO PRIMARIA VEGETAL',cidades[(i-1)%6],'RN',f'produtor{i}@example.invalid','INATIVO' if i%7==0 else 'ATIVO'))
    novos = [('Rúcula',1,'maco',4.5),('Tomate cereja',1,'kg',12.0),('Manga',2,'kg',6.0),('Acerola',2,'kg',9.0),('Jerimum',3,'kg',5.5),('Polpa de acerola',5,'kg',17.0)]
    for i in range(24):
        nome,cat,unidade,preco = novos[i%6]
        conn.execute("INSERT INTO tb_produto(id_produtor,id_categoria,nome_produto,unidade_medida,preco_unitario,estoque_disponivel,organico_certificado) VALUES (?,?,?,?,?,?,?)",(25+i%12,cat,f'{nome} — lote {i+49:02d}',unidade,preco+(i%4)*.5,30+i*3,i%4!=3))
    for i in range(48):
        pedido=conn.execute("INSERT INTO tb_pedido(id_cliente,data_pedido,status_pedido,modalidade_entrega) VALUES (?,?,?,?)",(1+i%24,f'2026-{9+i%2:02d}-{1+i%28:02d} 09:30:00','ENTREGUE' if i%3 else 'CONFIRMADO','RETIRADA_PONTO_FEIRA' if i%2 else 'ENTREGA_DOMICILIO')).lastrowid
        itens=conn.execute("SELECT id_produto,preco_unitario FROM tb_produto ORDER BY id_produto DESC LIMIT 24").fetchall()
        for j in range(2):
            prod,preco=itens[(i*2+j)%len(itens)]
            conn.execute("INSERT INTO tb_item_pedido(id_pedido,id_produto,quantidade,preco_unitario_venda) VALUES (?,?,?,?)",(pedido,prod,2+(i+j)%7,preco))
    conn.execute("INSERT INTO demo_versoes VALUES (2)")


def ampliar_paineis_demo(conn):
    if conn.execute("SELECT 1 FROM demo_versoes WHERE versao=3").fetchone():
        return
    nomes = ["Alessandra Cristina Lopes de Souza", "Antônio Carlos Oliveira Fernandes", "Bianca Raquel Pereira da Costa", "Diego Henrique Alves Monteiro", "Emanuela Vitória Santos Ribeiro", "Francisco José Medeiros da Silva", "Isabela Maria Nunes Carvalho", "João Pedro Batista de Lima", "Luciana Regina Ferreira Duarte", "Paulo Roberto Araújo Martins", "Renata Cristina Barbosa Freitas", "Sérgio Luiz Gomes de Andrade"]
    cidades_rn = ['NATAL','MOSSORO','APODI','CAICO','CURRAIS NOVOS','SAO PAULO DO POTENGI','CEARA-MIRIM','MACAIBA','ASSU','TOUROS','PARNAMIRIM','SANTA CRUZ']
    novos_ids=[]
    for j,nome in enumerate(nomes,37):
        if conn.execute('SELECT 1 FROM tb_produtor WHERE id_produtor=?',(j,)).fetchone():
            continue
        conn.execute("INSERT INTO tb_produtor(id_produtor,nome_produtor,cpf_cnpj,tipo_certificacao,entidade_certificadora,escopo_producao,cidade,uf,contato,situacao) VALUES (?,?,?,?,?,?,?,?,?,?)",(j,nome,cpf_ficticio(j),CERTIFICACOES[j%4],None if j%3==0 else 'Cooperativa Rural de Demonstração','PRODUCAO PRIMARIA VEGETAL',cidades_rn[(j-37)%12],'RN',f'produtor{j}@example.invalid','ATIVO' if j%5 else 'INATIVO'))
        novos_ids.append(j)
    alimentos=[('Abóbora',3,'kg',5.5),('Goiaba',2,'kg',7.5),('Cebolinha',1,'maco',3.0),('Polpa de goiaba',5,'kg',16.0),('Laranja',2,'kg',5.0),('Beterraba',3,'kg',6.2)]
    for i in range(len(novos_ids)*2):
        nome,cat,unidade,preco=alimentos[i%6]
        conn.execute('INSERT INTO tb_produto(id_produtor,id_categoria,nome_produto,unidade_medida,preco_unitario,estoque_disponivel,organico_certificado) VALUES (?,?,?,?,?,?,?)',(novos_ids[i%len(novos_ids)],cat,nome,unidade,preco+(i%4)*.4,40+i*5,i%4!=0))
    for i in range(12):
        conn.execute('INSERT INTO tb_cliente(nome_cliente,email,telefone,cidade,uf,endereco_entrega) VALUES (?,?,?,?,?,?)',(nomes[i],f'comprador{i+25}@example.invalid',None,cidades_rn[i],'RN',f'Rua de demonstração, {i+25}'))
    clientes=[r[0] for r in conn.execute('SELECT id_cliente FROM tb_cliente')]
    produtos=conn.execute('SELECT id_produto,preco_unitario FROM tb_produto').fetchall()
    for i in range(60):
        pedido=conn.execute('INSERT INTO tb_pedido(id_cliente,data_pedido,status_pedido,modalidade_entrega) VALUES (?,?,?,?)',(clientes[i%len(clientes)],f'2026-{1+i%10:02d}-{1+i%28:02d} 11:00:00','ENTREGUE' if i%4 else 'CONFIRMADO','ENTREGA_DOMICILIO' if i%2 else 'RETIRADA_PONTO_FEIRA')).lastrowid
        for j in range(3):
            prod,preco=produtos[(i*3+j)%len(produtos)]
            conn.execute('INSERT INTO tb_item_pedido(id_pedido,id_produto,quantidade,preco_unitario_venda) VALUES (?,?,?,?)',(pedido,prod,1+(i+j)%10,preco))
    conn.execute("CREATE TABLE IF NOT EXISTS cnpo_produtores (id_registro INTEGER PRIMARY KEY, pais TEXT, uf TEXT, cidade TEXT, nome_produtor TEXT, tipo_entidade TEXT, entidade TEXT, situacao TEXT)")
    estados={'AC':'RIO BRANCO','AL':'MACEIO','AP':'MACAPA','AM':'MANAUS','BA':'SALVADOR','CE':'FORTALEZA','DF':'BRASILIA','ES':'VITORIA','GO':'GOIANIA','MA':'SAO LUIS','MT':'CUIABA','MS':'CAMPO GRANDE','MG':'BELO HORIZONTE','PA':'BELEM','PB':'JOAO PESSOA','PR':'CURITIBA','PE':'RECIFE','PI':'TERESINA','RJ':'RIO DE JANEIRO','RN':'NATAL','RS':'PORTO ALEGRE','RO':'PORTO VELHO','RR':'BOA VISTA','SC':'FLORIANOPOLIS','SP':'SAO PAULO','SE':'ARACAJU','TO':'PALMAS'}
    for i,(uf,cidade) in enumerate(estados.items()):
        quantidade=35+(i*37)%180 if uf!='RN' else 216
        for j in range(quantidade):
            municipio=cidades_rn[j%12] if uf=='RN' else cidade
            conn.execute('INSERT INTO cnpo_produtores(pais,uf,cidade,nome_produtor,tipo_entidade,entidade,situacao) VALUES (?,?,?,?,?,?,?)',('BRASIL',uf,municipio,(NOMES_DEMO+nomes)[j%48],CERTIFICACOES[j%4],'Entidade de demonstração','ATIVO'))
    cols={r[1] for r in conn.execute('PRAGMA table_info(conab_venda_balcao)')}
    if 'numero_atendimentos' not in cols:
        conn.execute('ALTER TABLE conab_venda_balcao ADD COLUMN numero_atendimentos INTEGER NOT NULL DEFAULT 0')
        conn.execute('UPDATE conab_venda_balcao SET numero_atendimentos=clientes_atendidos*2')
    for i,(uf,cidade) in enumerate(estados.items()):
        polos=cidades_rn[6:] if uf=='RN' else [cidade]
        for k,municipio in enumerate(polos):
            for mes in range(1,11):
                volume=120000+(i+1)*31000+mes*8500+k*4200
                valor=round(volume*(1.15+(i%7)*.12),2)
                conn.execute('INSERT INTO conab_venda_balcao(municipio_armazem_venda,uf,qtd_produto_kg,valor_comercializado,clientes_atendidos,numero_atendimentos) VALUES (?,?,?,?,?,?)',(municipio,uf,volume,valor,120+i*8+mes*3,240+i*14+mes*5))
    conn.execute("CREATE TABLE IF NOT EXISTS conab_oferta_demanda (id_balanco INTEGER PRIMARY KEY,produto TEXT,dsc_safra TEXT,producao_1000t REAL,consumo_1000t REAL,importacao_1000t REAL,exportacao_1000t REAL,estoque_inicial_1000t REAL,estoque_final_1000t REAL)")
    for i,produto in enumerate(['ARROZ','FEIJAO','MILHO','SOJA','TRIGO','ALGODAO','SORGO','AVEIA']):
        for safra in range(2021,2026):
            producao=round((8500+i*5200)*(1+(safra-2021)*.045),2)
            consumo=round(producao*(.68+(i%3)*.08),2)
            importacao=round(producao*.04,2)
            exportacao=round(producao*.18,2)
            inicial=round(producao*.12,2)
            final=round(inicial+producao+importacao-consumo-exportacao,2)
            conn.execute('INSERT INTO conab_oferta_demanda(produto,dsc_safra,producao_1000t,consumo_1000t,importacao_1000t,exportacao_1000t,estoque_inicial_1000t,estoque_final_1000t) VALUES (?,?,?,?,?,?,?,?)',(produto,f'{safra}/{safra+1}',producao,consumo,importacao,exportacao,inicial,final))
    conn.execute('INSERT INTO demo_versoes VALUES (3)')



def ampliar_volume_demo(conn):
    if conn.execute("SELECT 1 FROM demo_versoes WHERE versao=4").fetchone():
        return
    import random
    from datetime import datetime, timedelta
    rng = random.Random(20261111)
    primeiros = ['Ana','Bruno','Carolina','Daniel','Elisa','Fábio','Gabriela','Henrique','Isabela','João','Larissa','Marcos','Natália','Otávio','Paula','Rafael','Sara','Tiago','Valéria','William','Yara','Zélia','Bento','Célia','Adriana','Carlos','Débora','Eduardo','Fernanda','Gustavo','Helena','Igor','Juliana','Leandro','Márcia','Nelson']
    sobrenomes = ['Almeida','Barbosa','Carvalho','Dantas','Ferreira','Gomes','Lima','Medeiros','Nascimento','Oliveira','Pereira','Queiroz','Ribeiro','Santos','Teixeira','Vieira','Araújo','Batista','Costa','Duarte','Freitas','Moura','Rocha','Souza']
    cidades = ['NATAL','MOSSORO','APODI','CAICO','CURRAIS NOVOS','SAO PAULO DO POTENGI','CEARA-MIRIM','MACAIBA','ASSU','TOUROS','PARNAMIRIM','SANTA CRUZ','PAU DOS FERROS','SAO JOSE DE MIPIBU','NOVA CRUZ','JOAO CAMARA','ANGICOS','ACARI','JUCURUTU','BARAUNA','GOIANINHA','EXTREMOZ','SAO GONCALO DO AMARANTE','TANGARA']
    def nome(i):
        return f"{primeiros[i%36]} {sobrenomes[(i//36)%24]} de {sobrenomes[(i//864+7)%24]}"
    def documento(i):
        base=f"{(341827569+i*7919)%1000000000:09d}"
        for peso in (10,11):
            resto=sum(int(d)*(peso-j) for j,d in enumerate(base))%11
            base+=str(0 if resto<2 else 11-resto)
        return f"{base[:3]}.{base[3:6]}.{base[6:9]}-{base[9:]}"
    total=conn.execute('SELECT COUNT(*) FROM tb_produtor').fetchone()[0]
    proximo=conn.execute('SELECT COALESCE(MAX(id_produtor),0)+1 FROM tb_produtor').fetchone()[0]
    documentos={normalizar_documento(r[0]) for r in conn.execute('SELECT cpf_cnpj FROM tb_produtor')}
    rows=[]
    for i in range(max(0,2000-total)):
        codigo=proximo+i
        tentativa=codigo
        doc=documento(tentativa)
        while normalizar_documento(doc) in documentos:
            tentativa+=10000
            doc=documento(tentativa)
        documentos.add(normalizar_documento(doc))
        rows.append((codigo,nome(codigo),doc,CERTIFICACOES[codigo%4],None if codigo%5==0 else f'Associação Rural {sobrenomes[codigo%24]}','PRODUCAO PRIMARIA VEGETAL',cidades[codigo%24],'RN',f'produtor{codigo}@example.invalid','INATIVO' if codigo%10==0 else 'SUSPENSO' if codigo%31==0 else 'ATIVO'))
    conn.executemany('INSERT INTO tb_produtor(id_produtor,nome_produtor,cpf_cnpj,tipo_certificacao,entidade_certificadora,escopo_producao,cidade,uf,contato,situacao) VALUES (?,?,?,?,?,?,?,?,?,?)',rows)
    produtores=[r[0] for r in conn.execute('SELECT id_produtor FROM tb_produtor ORDER BY id_produtor')]
    alimentos=[('Alface crespa',1,'unidade',3.5),('Coentro',1,'maco',2.8),('Rúcula',1,'maco',4.2),('Couve',1,'maco',4.5),('Cebolinha',1,'maco',3.0),('Tomate cereja',1,'kg',12.0),('Banana prata',2,'kg',6.0),('Mamão formosa',2,'kg',5.5),('Manga',2,'kg',7.0),('Goiaba',2,'kg',7.5),('Melancia',2,'kg',3.2),('Acerola',2,'kg',9.0),('Macaxeira',3,'kg',5.5),('Batata-doce',3,'kg',4.5),('Inhame',3,'kg',8.5),('Jerimum',3,'kg',5.0),('Ovos caipiras',4,'duzia',15.0),('Polpa de manga',5,'kg',18.0),('Farinha de mandioca',5,'kg',8.0),('Polpa de acerola',5,'kg',19.0)]
    total=conn.execute('SELECT COUNT(*) FROM tb_produto').fetchone()[0]
    rows=[]
    for i in range(max(0,6000-total)):
        alimento,cat,unidade,preco=alimentos[i%20]
        rows.append((produtores[i%len(produtores)],cat,alimento,unidade,round(preco*rng.uniform(.8,1.35),2),rng.randint(0,500),int(i%4!=0)))
    conn.executemany('INSERT INTO tb_produto(id_produtor,id_categoria,nome_produto,unidade_medida,preco_unitario,estoque_disponivel,organico_certificado) VALUES (?,?,?,?,?,?,?)',rows)
    total=conn.execute('SELECT COUNT(*) FROM tb_cliente').fetchone()[0]
    proximo=conn.execute('SELECT COALESCE(MAX(id_cliente),0)+1 FROM tb_cliente').fetchone()[0]
    conn.executemany('INSERT INTO tb_cliente(id_cliente,nome_cliente,email,cidade,uf,endereco_entrega) VALUES (?,?,?,?,?,?)',[(proximo+i,nome(proximo+i+5000),f'cliente-volume{proximo+i}@example.invalid',cidades[i%24],'RN',f'Rua de Demonstração, {i+1}') for i in range(max(0,3000-total))])
    clientes=[r[0] for r in conn.execute('SELECT id_cliente FROM tb_cliente')]
    produtos=conn.execute('SELECT id_produto,preco_unitario FROM tb_produto').fetchall()
    total=conn.execute('SELECT COUNT(*) FROM tb_pedido').fetchone()[0]
    proximo=conn.execute('SELECT COALESCE(MAX(id_pedido),0)+1 FROM tb_pedido').fetchone()[0]
    pedidos=[]
    itens=[]
    for i in range(max(0,30000-total)):
        codigo=proximo+i
        data=datetime(2024,1,1)+timedelta(days=rng.randrange(1045),hours=rng.randrange(8,19))
        pedidos.append((codigo,rng.choice(clientes),data.strftime('%Y-%m-%d %H:%M:%S'),'ENTREGUE' if i%5 else 'CONFIRMADO','ENTREGA_DOMICILIO' if i%2 else 'RETIRADA_PONTO_FEIRA'))
        for produto,preco in rng.sample(produtos,3):
            itens.append((codigo,produto,rng.randint(1,12),preco))
    conn.executemany('INSERT INTO tb_pedido(id_pedido,id_cliente,data_pedido,status_pedido,modalidade_entrega) VALUES (?,?,?,?,?)',pedidos)
    conn.executemany('INSERT INTO tb_item_pedido(id_pedido,id_produto,quantidade,preco_unitario_venda) VALUES (?,?,?,?)',itens)
    estados=['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
    capitais=['RIO BRANCO','MACEIO','MACAPA','MANAUS','SALVADOR','FORTALEZA','BRASILIA','VITORIA','GOIANIA','SAO LUIS','CUIABA','CAMPO GRANDE','BELO HORIZONTE','BELEM','JOAO PESSOA','CURITIBA','RECIFE','TERESINA','RIO DE JANEIRO','NATAL','PORTO ALEGRE','PORTO VELHO','BOA VISTA','FLORIANOPOLIS','SAO PAULO','ARACAJU','PALMAS']
    total=conn.execute('SELECT COUNT(*) FROM cnpo_produtores').fetchone()[0]
    rows=[]
    for i in range(max(0,100000-total)):
        indice=rng.choices(range(27),weights=[1+(k*7)%13 for k in range(27)])[0]
        uf=estados[indice]
        cidade=rng.choice(cidades) if uf=='RN' else capitais[indice]
        rows.append(('BRASIL',uf,cidade,nome(i+10000),CERTIFICACOES[i%4],'Entidade de demonstração','ATIVO'))
    conn.executemany('INSERT INTO cnpo_produtores(pais,uf,cidade,nome_produtor,tipo_entidade,entidade,situacao) VALUES (?,?,?,?,?,?,?)',rows)
    total=conn.execute('SELECT COUNT(*) FROM conab_venda_balcao').fetchone()[0]
    rows=[]
    for i in range(max(0,15000-total)):
        indice=rng.randrange(27)
        uf=estados[indice]
        cidade=rng.choice(cidades) if uf=='RN' else capitais[indice]
        volume=rng.randint(10000,1800000)
        clientes_atendidos=rng.randint(40,1600)
        rows.append((cidade,uf,volume,round(volume*rng.uniform(.9,2.8),2),clientes_atendidos,clientes_atendidos+rng.randint(20,700)))
    conn.executemany('INSERT INTO conab_venda_balcao(municipio_armazem_venda,uf,qtd_produto_kg,valor_comercializado,clientes_atendidos,numero_atendimentos) VALUES (?,?,?,?,?,?)',rows)
    produtos_oferta=['ARROZ','FEIJAO','MILHO','SOJA','TRIGO','ALGODAO','SORGO','AVEIA','CEVADA','CENTEIO','AMENDOIM','GIRASSOL','CANOLA','TRITICALE','MAMONA','GERGELIM']
    existentes=set(conn.execute('SELECT produto,dsc_safra FROM conab_oferta_demanda').fetchall())
    rows=[]
    for i,produto in enumerate(produtos_oferta):
        for ano in range(2011,2026):
            safra=f'{ano}/{ano+1}'
            if (produto,safra) in existentes:
                continue
            producao=round((4000+i*3000)*(1+(ano-2011)*.03)*rng.uniform(.85,1.15),2)
            consumo=round(producao*rng.uniform(.6,.95),2)
            imp=round(producao*.05,2); exp=round(producao*.12,2); inicial=round(producao*.2,2)
            rows.append((produto,safra,producao,consumo,imp,exp,inicial,round(inicial+producao+imp-consumo-exp,2)))
    conn.executemany('INSERT INTO conab_oferta_demanda(produto,dsc_safra,producao_1000t,consumo_1000t,importacao_1000t,exportacao_1000t,estoque_inicial_1000t,estoque_final_1000t) VALUES (?,?,?,?,?,?,?,?)',rows)
    for comando in ['CREATE INDEX IF NOT EXISTS idx_demo_produtor_produto ON tb_produto(id_produtor)','CREATE INDEX IF NOT EXISTS idx_demo_item_produto ON tb_item_pedido(id_produto)','CREATE INDEX IF NOT EXISTS idx_demo_item_pedido ON tb_item_pedido(id_pedido)','CREATE INDEX IF NOT EXISTS idx_demo_cnpo_uf ON cnpo_produtores(uf)','CREATE INDEX IF NOT EXISTS idx_demo_conab_uf ON conab_venda_balcao(uf)']:
        conn.execute(comando)
    conn.execute('INSERT INTO demo_versoes VALUES (4)')


def preparar_demo(caminho):
    conn = sqlite3.connect(caminho, timeout=15)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        existe = conn.execute("SELECT name FROM sqlite_master WHERE name='tb_produtor'").fetchone()
        if existe:
            ampliar_dados_demo(conn)
            ampliar_paineis_demo(conn)
            ampliar_volume_demo(conn)
            conn.commit()
            return
        # DDL individual mantém a criação e a carga na mesma transação.
        for comando in SCHEMA_DEMO.split(';'):
            if comando.strip():
                conn.execute(comando)
        cidades = ['NATAL', 'MOSSORO', 'APODI', 'CAICO', 'CURRAIS NOVOS', 'SAO PAULO DO POTENGI']
        nomes = ['Ana', 'Bruno', 'Clara', 'Daniel', 'Elisa', 'Fabio', 'Gabriela', 'Hugo', 'Iara', 'Jonas', 'Lara', 'Marcos', 'Nina', 'Otavio', 'Paula', 'Rafael', 'Sara', 'Tiago', 'Vera', 'William', 'Yara', 'Zelia', 'Bento', 'Celia']
        for i, nome in enumerate(nomes, 1):
            doc = f'{i:011d}'  # Identificador sintético; não representa CPF válido.
            if i == 5:
                doc = ''  # Exercita correção de cadastro legado pela busca por ID.
            conn.execute("INSERT INTO tb_produtor (nome_produtor,cpf_cnpj,tipo_certificacao,entidade_certificadora,escopo_producao,cidade,uf,contato,situacao) VALUES (?,?,?,?,?,?,?,?,?)", (
                f'{nome} Exemplo {i:02d}', doc, CERTIFICACOES[(i-1)%4],
                None if i%3 == 0 else f'Associação Fictícia {1+(i%4)}',
                'PRODUCAO PRIMARIA VEGETAL', cidades[(i-1)%6], 'RN',
                f'produtor{i}@example.invalid', 'INATIVO' if i%7==0 else 'SUSPENSO' if i%11==0 else 'ATIVO'))
        categorias = ['Hortaliças e Folhosas', 'Frutas Tropicais', 'Raízes e Tubérculos', 'Ovos e Derivados', 'Processados Artesanais']
        for cat in categorias:
            conn.execute("INSERT INTO tb_categoria(nome_categoria,descricao) VALUES (?,?)",(cat,'Categoria de demonstração'))
        produtos = [('Alface',1,'unidade',3.5),('Coentro',1,'maco',2.5),('Banana',2,'kg',5.9),('Mamão',2,'kg',6.5),('Macaxeira',3,'kg',5.0),('Batata-doce',3,'kg',4.8),('Ovos caipiras',4,'duzia',14.0),('Polpa de manga',5,'kg',18.0),('Couve',1,'maco',4.0),('Melancia',2,'kg',3.5),('Inhame',3,'kg',8.5),('Farinha de mandioca',5,'kg',7.0)]
        precos=[]
        for i in range(48):
            nome,cat,unidade,base=produtos[i%12]
            preco=round(base+(i%5)*0.5,2)
            precos.append(preco)
            conn.execute("INSERT INTO tb_produto(id_produtor,id_categoria,nome_produto,unidade_medida,preco_unitario,estoque_disponivel,organico_certificado) VALUES (?,?,?,?,?,?,?)",(i%24+1,cat,f'{nome} — lote fictício {i+1:02d}',unidade,preco,15+(i*7)%160,i%4!=3))
        for i in range(1,25):
            conn.execute("INSERT INTO tb_cliente(nome_cliente,email,telefone,cidade,uf,endereco_entrega) VALUES (?,?,?,?,?,?)",(f'Cliente Exemplo {i:02d}',f'cliente{i}@example.invalid',None,cidades[i%6],'RN',f'Endereço fictício {i}'))
        for i in range(1,73):
            conn.execute("INSERT INTO tb_pedido(id_cliente,data_pedido,status_pedido,modalidade_entrega) VALUES (?,?,?,?)",(1+(i-1)%24,f'2026-{1+(i-1)%9:02d}-{1+(i-1)%28:02d} 10:00:00','ENTREGUE' if i%3 else 'CONFIRMADO','RETIRADA_PONTO_FEIRA'))
            for j in range(2):
                prod=(2*(i-1)+j)%48+1
                conn.execute("INSERT INTO tb_item_pedido(id_pedido,id_produto,quantidade,preco_unitario_venda) VALUES (?,?,?,?)",(i,prod,1+(i+j)%8,precos[prod-1]))
        for i,cidade in enumerate(cidades):
            for mes in range(1,9):
                volume=8000+i*4200+mes*750
                conn.execute("INSERT INTO conab_venda_balcao(municipio_armazem_venda,uf,qtd_produto_kg,valor_comercializado,clientes_atendidos) VALUES (?,?,?,?,?)",(cidade,'RN',volume,round(volume*(1.2+i*.15),2),40+i*12+mes*3))
        ampliar_dados_demo(conn)
        ampliar_paineis_demo(conn)
        ampliar_volume_demo(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class CursorDemo:
    def __init__(self, conn, dictionary=False):
        self.conn = conn
        self.cursor = conn.cursor()
        self.dictionary = dictionary
        self.resposta = None

    @property
    def description(self):
        return self.cursor.description

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def execute(self, sql, params=None):
        self.resposta = None
        try:
            if 'GET_LOCK(' in sql:
                self.conn.execute('BEGIN IMMEDIATE')
                self.resposta = {'adquirido': 1}
            elif 'RELEASE_LOCK(' in sql:
                self.resposta = {'liberado': 1}
            else:
                self.cursor.execute(sql.replace(' FOR UPDATE','').replace('%s','?'), params or ())
        except sqlite3.IntegrityError as erro:
            raise mysql.connector.IntegrityError(str(erro)) from erro
        except sqlite3.Error as erro:
            raise mysql.connector.Error(str(erro)) from erro
        return self

    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.dictionary:
            return [dict(zip([c[0] for c in self.description], row)) for row in rows]
        return rows

    def fetchone(self):
        if self.resposta is not None:
            return self.resposta
        row = self.cursor.fetchone()
        if row is not None and self.dictionary:
            return dict(zip([c[0] for c in self.description], row))
        return row

    def close(self):
        self.cursor.close()


class ConexaoDemo:
    def __init__(self, caminho):
        self.conn = sqlite3.connect(caminho,timeout=15)
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.create_function('SUBSTRING_INDEX', 3, lambda value, sep, count: sep.join(str(value).split(sep)[:int(count)]) if int(count)>0 else sep.join(str(value).split(sep)[int(count):]))

    def cursor(self,dictionary=False):
        return CursorDemo(self.conn,dictionary)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

# A configuração informada na tela fica apenas na sessão do navegador.
def configuracao_mysql():
    return st.session_state.get("mysql_config", {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    })


def get_connection(database_name):
    caminho = Path(os.getenv("FEIRA_DEMO_DB", str(Path(__file__).with_name("feira_demo.sqlite3"))))
    preparar_demo(caminho)
    return ConexaoDemo(caminho)


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
        return pd.read_sql(sql.replace("%s", "?"), conn.conn, params=params)
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

st.title("🌱 Feira Online Sustentável — Demonstração")
st.info("DEMONSTRAÇÃO — Todos os nomes, documentos, pedidos e indicadores desta base são fictícios. Alterações feitas aqui afetam somente a demonstração.")
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
        "id_produtor": "ID do produtor",
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
    st.caption("Busque pelo ID do produtor. Cada ID é único e permanece fixo após o cadastro.")
    mensagem = st.session_state.pop("produtor_mensagem", None)
    if mensagem:
        st.success(mensagem)

    with st.form("buscar_produtor"):
        documento_busca = st.text_input("Buscar por ID do produtor", help="Informe o ID exibido na tabela de produtores.")
        buscar = st.form_submit_button("Buscar produtor")
    if buscar:
        st.session_state.pop("produtor_resultados", None)
        st.session_state["produtor_versao"] = st.session_state.get("produtor_versao", 0) + 1
        try:
            encontrados = buscar_produtores(get_connection, documento_busca, por_codigo=True)
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
        id_produtor_form = st.text_input(
            "ID do produtor *", value=str(registro.get("id_produtor", "")),
            disabled=original is not None, max_chars=10,
            help="Informe um número inteiro positivo que ainda não esteja em uso. O ID não muda na edição.",
        )
        c1, c2, c3 = st.columns(3)
        dados = {"id_produtor": id_produtor_form}
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
                st.error("ID do produtor ou CPF/CNPJ já está sendo utilizado. Confira os dados e busque pelo ID para editar.")
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
        "id_produtor": "ID do produtor",
        "nome_produtor": "Produtor",
        "cpf_cnpj": "CPF/CNPJ",
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
    st.subheader("Análise de Dados Públicos — CNPO/MAPA e CONAB")
    st.caption(
        "Dados fictícios para testar os painéis CNPO/MAPA e CONAB. Os valores não representam estatísticas oficiais."
    )

    def query_publica(sql, params=None):
        """Consulta o banco de dados públicos aceitando tanto 'db_analise_publica' quanto 'analise_publica_dos_dados'."""
        for nome_db in ("db_analise_publica", "analise_publica_dos_dados"):
            conn = None
            try:
                conn = get_connection(nome_db)
                return pd.read_sql(sql.replace("%s", "?"), conn.conn, params=params)
            except mysql.connector.Error as erro:
                if erro.errno == 1049:
                    continue
                st.error(f"Erro ao consultar o banco {nome_db}: {erro}")
                st.stop()
            except pd.errors.DatabaseError as erro:
                if "1049" in str(erro) or "Unknown database" in str(erro):
                    continue
                st.error(f"Erro na consulta SQL em {nome_db}: {erro}")
                st.stop()
            finally:
                if conn is not None:
                    conn.close()
        st.error(
            "Não foi possível encontrar o banco de dados públicos ('db_analise_publica' ou 'analise_publica_dos_dados'). "
            "Verifique se o banco foi criado e populado no MySQL."
        )
        st.stop()

    def formatar_int(valor):
        return f"{int(round(float(valor))):,}".replace(",", ".")

    def formatar_moeda(valor):
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def formatar_decimal(valor):
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def exibir_metricas_destaque(df_dados, col_valor, col_categoria=None, formato="int"):
        """Exibe os 4 cartões de destaque padronizados: Máximo, Mínimo, Média e Soma (Total)."""
        serie = df_dados[col_valor].astype(float)
        if serie.empty:
            return

        fn_fmt = {
            "int": formatar_int,
            "moeda": formatar_moeda,
            "decimal": formatar_decimal,
        }.get(formato, formatar_decimal)

        idx_max = serie.idxmax()
        idx_min = serie.idxmin()
        val_max = serie.loc[idx_max]
        val_min = serie.loc[idx_min]
        val_media = serie.mean()
        val_soma = serie.sum()

        label_max = f"Máximo ({df_dados.loc[idx_max, col_categoria]})" if col_categoria else "Máximo"
        label_min = f"Mínimo ({df_dados.loc[idx_min, col_categoria]})" if col_categoria else "Mínimo"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(label_max, fn_fmt(val_max))
        m2.metric(label_min, fn_fmt(val_min))
        m3.metric("Média", formatar_moeda(val_media) if formato == "moeda" else formatar_decimal(val_media))
        m4.metric("Soma (Total)", fn_fmt(val_soma))

    def grafico_barras_horizontal(df_plot, col_cat, col_val, titulo, label_x, label_y="", cor="#1b7857"):
        altura = max(380, len(df_plot) * 24)
        chart = (
            alt.Chart(df_plot)
            .mark_bar(color=cor)
            .encode(
                x=alt.X(f"{col_val}:Q", title=label_x),
                y=alt.Y(
                    f"{col_cat}:N",
                    sort=df_plot[col_cat].tolist(),
                    title=label_y,
                    axis=alt.Axis(labelLimit=300)
                ),
                tooltip=[
                    alt.Tooltip(f"{col_cat}:N", title=label_y or "Categoria"),
                    alt.Tooltip(f"{col_val}:Q", title=label_x, format=",.2f"),
                ],
            )
            .properties(title=titulo, height=altura)
        )
        st.altair_chart(chart, use_container_width=True)

    sub_uf, sub_rn, sub_conab_uf, sub_oferta, sub_valor_medio, sub_polos = st.tabs([
        "Produtores por Estado",
        "Produtores no RN",
        "Comercialização (CONAB)",
        "Oferta e Demanda",
        "Valor Médio no RN",
        "Polos Regionais (RN)"
    ])

    # --------------------------------------------------------------------------
    # Distribuição de Produtores Orgânicos por Estado
    # --------------------------------------------------------------------------
    with sub_uf:
        st.markdown("### Distribuição de Produtores Orgânicos por Estado")

        sql_prod_uf = """
            SELECT
                UPPER(TRIM(uf)) AS estado,
                COUNT(*) AS total_produtores
            FROM cnpo_produtores
            WHERE UPPER(TRIM(pais)) = 'BRASIL'
              AND UPPER(TRIM(uf)) IN (
                  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',
                  'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
              )
            GROUP BY UPPER(TRIM(uf))
            ORDER BY total_produtores DESC
        """
        df_uf = query_publica(sql_prod_uf)

        if not df_uf.empty:
            exibir_metricas_destaque(df_uf, "total_produtores", "estado", formato="int")
            st.divider()

            recorte_uf = st.selectbox(
                "Registros exibidos:",
                ["Todos os estados", "10 primeiros e RN", "10 primeiros"],
                key="rec_uf"
            )

            df_uf_ord = df_uf.reset_index(drop=True)
            df_uf_ord["posicao"] = [f"{i}º" for i in range(1, len(df_uf_ord) + 1)]

            if recorte_uf == "10 primeiros e RN":
                df_uf_exib = pd.concat([
                    df_uf_ord.head(10),
                    df_uf_ord[df_uf_ord["estado"] == "RN"]
                ]).drop_duplicates(subset=["estado"]).reset_index(drop=True)
            elif recorte_uf == "10 primeiros":
                df_uf_exib = df_uf_ord.head(10).reset_index(drop=True)
            else:
                df_uf_exib = df_uf_ord

            col_t1, col_g1 = st.columns([1, 1.3])
            with col_t1:
                st.markdown("**Distribuição de produtores orgânicos por estado**")
                df_t1_exib = df_uf_exib[["posicao", "estado", "total_produtores"]].rename(columns={
                    "posicao": "Posição",
                    "estado": "Estado",
                    "total_produtores": "Registros"
                })
                st.dataframe(df_t1_exib, use_container_width=True, hide_index=True)

            with col_g1:
                st.markdown("**Estados por quantidade de registros de produtores orgânicos**")
                grafico_barras_horizontal(
                    df_uf_exib,
                    col_cat="estado",
                    col_val="total_produtores",
                    titulo="Produtores orgânicos cadastrados por estado",
                    label_x="Registros",
                    label_y="Estado",
                    cor="#1b7857"
                )

    # --------------------------------------------------------------------------
    # Análise dos Produtores Orgânicos no Rio Grande do Norte
    # --------------------------------------------------------------------------
    with sub_rn:
        st.markdown("### Produtores Orgânicos no Rio Grande do Norte por Município")

        sql_prod_rn = """
            SELECT
                UPPER(TRIM(cidade)) AS municipio,
                COUNT(*) AS total_produtores
            FROM cnpo_produtores
            WHERE UPPER(TRIM(uf)) = 'RN'
              AND UPPER(TRIM(pais)) = 'BRASIL'
              AND cidade IS NOT NULL
              AND TRIM(cidade) <> ''
            GROUP BY UPPER(TRIM(cidade))
            ORDER BY total_produtores DESC
        """
        df_mun_rn = query_publica(sql_prod_rn)

        if not df_mun_rn.empty:
            exibir_metricas_destaque(df_mun_rn, "total_produtores", "municipio", formato="int")
            st.divider()

            recorte_rn = st.selectbox(
                "Registros exibidos:",
                ["Todos os municípios", "10 primeiros"],
                key="rec_rn"
            )

            df_rn_ord = df_mun_rn.reset_index(drop=True)

            if recorte_rn == "10 primeiros":
                df_rn_exib = df_rn_ord.head(10).reset_index(drop=True)
            else:
                df_rn_exib = df_rn_ord

            col_t2, col_g2 = st.columns([1, 1.3])
            with col_t2:
                st.markdown("**Registros de produtores orgânicos por município (RN)**")
                df_t2_exib = df_rn_exib.rename(columns={
                    "municipio": "Município",
                    "total_produtores": "Registros"
                })
                st.dataframe(df_t2_exib, use_container_width=True, hide_index=True)

            with col_g2:
                st.markdown("**Distribuição de produtores orgânicos por município (RN)**")
                grafico_barras_horizontal(
                    df_rn_exib,
                    col_cat="municipio",
                    col_val="total_produtores",
                    titulo="Produtores orgânicos por município no RN",
                    label_x="Registros",
                    label_y="Município",
                    cor="#1b7857"
                )

    # --------------------------------------------------------------------------
    # Análise dos Dados de Comercialização da CONAB
    # --------------------------------------------------------------------------
    with sub_conab_uf:
        st.markdown("### Comercialização no Programa de Venda em Balcão por Estado (CONAB)")

        sql_conab_uf = """
            SELECT
                uf AS estado,
                COUNT(*) AS total_registros,
                SUM(qtd_produto_kg) AS volume_total_kg,
                ROUND(SUM(valor_comercializado), 2) AS valor_total_reais,
                SUM(numero_atendimentos) AS total_atendimentos,
                SUM(clientes_atendidos) AS total_clientes_atendidos
            FROM conab_venda_balcao
            GROUP BY uf
            ORDER BY volume_total_kg DESC
        """
        df_vb_uf = query_publica(sql_conab_uf)

        if not df_vb_uf.empty:
            df_vb_uf["volume_milhoes_kg"] = (df_vb_uf["volume_total_kg"].astype(float) / 1e6).round(2)

            metricas_vb = {
                "Volume Comercializado (kg)": ("volume_total_kg", "int", "volume_milhoes_kg", "Milhões de kg"),
                "Valor Comercializado (R$)": ("valor_total_reais", "moeda", "valor_total_reais", "Valor (R$)"),
                "Total de Atendimentos": ("total_atendimentos", "int", "total_atendimentos", "Atendimentos"),
                "Clientes Atendidos": ("total_clientes_atendidos", "int", "total_clientes_atendidos", "Clientes Atendidos"),
            }

            c_met, c_rec = st.columns(2)
            with c_met:
                met_vb_nome = st.selectbox("Indicador em destaque:", list(metricas_vb.keys()), key="met_vb_uf")
            with c_rec:
                recorte_vb = st.selectbox("Registros exibidos:", ["Todos os estados", "10 primeiros"], key="rec_vb_uf")

            col_metrica, fmt_metrica, col_grafico_vb, label_eixo_vb = metricas_vb[met_vb_nome]

            exibir_metricas_destaque(df_vb_uf, col_metrica, "estado", formato=fmt_metrica)
            st.divider()

            df_vb_ord = df_vb_uf.sort_values(by=col_metrica, ascending=False).reset_index(drop=True)

            if recorte_vb == "10 primeiros":
                df_vb_exib = df_vb_ord.head(10).reset_index(drop=True)
            else:
                df_vb_exib = df_vb_ord

            col_t3, col_g3 = st.columns([1.15, 1.25])
            with col_t3:
                st.markdown("**Volume e valor comercializado por estado**")
                df_t3_exib = pd.DataFrame({
                    "UF": df_vb_exib["estado"],
                    "Volume (kg)": df_vb_exib["volume_total_kg"].apply(formatar_int),
                    "Valor (R$)": df_vb_exib["valor_total_reais"].apply(formatar_decimal),
                    "Atendimentos": df_vb_exib["total_atendimentos"].apply(formatar_int),
                    "Clientes": df_vb_exib["total_clientes_atendidos"].apply(formatar_int),
                })
                st.dataframe(df_t3_exib, use_container_width=True, hide_index=True)

            with col_g3:
                st.markdown(f"**Comparativo por estado — {met_vb_nome}**")
                grafico_barras_horizontal(
                    df_vb_exib,
                    col_cat="estado",
                    col_val=col_grafico_vb,
                    titulo=f"{met_vb_nome} por estado",
                    label_x=label_eixo_vb,
                    label_y="UF",
                    cor="#1b7857"
                )

    # --------------------------------------------------------------------------
    # Análise dos Indicadores de Oferta e Demanda
    # --------------------------------------------------------------------------
    with sub_oferta:
        st.markdown("### Indicadores de Oferta e Demanda Agrícola (CONAB)")

        sql_od_medias = """
            SELECT
                produto,
                COUNT(dsc_safra) AS safras,
                ROUND(AVG(producao_1000t), 2) AS producao_media,
                ROUND(AVG(consumo_1000t), 2) AS consumo_medio
            FROM conab_oferta_demanda
            GROUP BY produto
            ORDER BY produto
        """
        sql_od_detalhe = """
            SELECT
                produto,
                dsc_safra AS safra,
                producao_1000t AS producao,
                consumo_1000t AS consumo,
                importacao_1000t AS importacao,
                exportacao_1000t AS exportacao,
                estoque_inicial_1000t AS estoque_inicial,
                estoque_final_1000t AS estoque_final,
                ROUND(producao_1000t - consumo_1000t, 2) AS diferenca_producao_consumo
            FROM conab_oferta_demanda
            ORDER BY
                produto,
                CAST(SUBSTRING_INDEX(dsc_safra, '/', 1) AS UNSIGNED)
        """
        df_od_medias = query_publica(sql_od_medias)
        df_od_detalhe = query_publica(sql_od_detalhe)

        if not df_od_medias.empty:
            opcoes_od = {
                "Produção Média (1000t)": "producao_media",
                "Consumo Médio (1000t)": "consumo_medio",
                "Quantidade de Safras": "safras"
            }

            ind_od_nome = st.selectbox("Indicador em destaque:", list(opcoes_od.keys()), key="ind_od")
            col_od_sel = opcoes_od[ind_od_nome]
            fmt_od = "int" if col_od_sel == "safras" else "decimal"

            exibir_metricas_destaque(df_od_medias, col_od_sel, "produto", formato=fmt_od)
            st.divider()

            df_od_ord = df_od_medias.sort_values(by=col_od_sel, ascending=False).reset_index(drop=True)

            col_t4, col_g4 = st.columns([1, 1.3])
            with col_t4:
                st.markdown("**Médias de produção e consumo por produto (milhares de toneladas)**")
                df_t4_exib = pd.DataFrame({
                    "Produto": df_od_ord["produto"],
                    "Safras": df_od_ord["safras"],
                    "Produção média": df_od_ord["producao_media"].apply(formatar_decimal),
                    "Consumo médio": df_od_ord["consumo_medio"].apply(formatar_decimal)
                })
                st.dataframe(df_t4_exib, use_container_width=True, hide_index=True)

            with col_g4:
                st.markdown("**Médias de produção e consumo por produto**")
                df_plot_od = df_od_ord.copy()
                df_plot_od["Produção"] = (df_plot_od["producao_media"].astype(float) / 1000.0).round(2)
                df_plot_od["Consumo"] = (df_plot_od["consumo_medio"].astype(float) / 1000.0).round(2)
                ordem_produtos = df_plot_od["produto"].tolist()
                df_long_od = df_plot_od.melt(
                    id_vars=["produto"],
                    value_vars=["Produção", "Consumo"],
                    var_name="Indicador",
                    value_name="Milhoes_t"
                )
                chart_od = (
                    alt.Chart(df_long_od)
                    .mark_bar()
                    .encode(
                        x=alt.X("produto:N", sort=ordem_produtos, title="Produto", axis=alt.Axis(labelAngle=-25)),
                        xOffset="Indicador:N",
                        y=alt.Y("Milhoes_t:Q", title="Milhões de toneladas (média por safra)"),
                        color=alt.Color(
                            "Indicador:N",
                            scale=alt.Scale(domain=["Produção", "Consumo"], range=["#1b7857", "#e69f45"]),
                            legend=alt.Legend(title="Indicador")
                        ),
                        tooltip=[
                            alt.Tooltip("produto:N", title="Produto"),
                            alt.Tooltip("Indicador:N", title="Indicador"),
                            alt.Tooltip("Milhoes_t:Q", title="Milhões de t", format=",.2f"),
                        ]
                    )
                    .properties(title="Produção e consumo médios por produto", height=380)
                )
                st.altair_chart(chart_od, use_container_width=True)

        if not df_od_detalhe.empty:
            st.divider()
            st.markdown("#### Registros por Safra e Produto")
            produtos_lista = ["Todos"] + sorted(df_od_detalhe["produto"].unique().tolist())
            prod_sel = st.selectbox("Filtrar por Produto:", produtos_lista, key="filtro_prod_od")

            df_det_filtrado = (
                df_od_detalhe.copy() if prod_sel == "Todos"
                else df_od_detalhe[df_od_detalhe["produto"] == prod_sel].copy()
            )

            df_det_exib = df_det_filtrado.rename(columns={
                "produto": "Produto",
                "safra": "Safra",
                "producao": "Produção (1000t)",
                "consumo": "Consumo (1000t)",
                "importacao": "Importação (1000t)",
                "exportacao": "Exportação (1000t)",
                "estoque_inicial": "Estoque Inicial (1000t)",
                "estoque_final": "Estoque Final (1000t)",
                "diferenca_producao_consumo": "Saldo Produção - Consumo (1000t)"
            })
            st.dataframe(df_det_exib, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # Análise do Valor Médio de Comercialização no Rio Grande do Norte
    # --------------------------------------------------------------------------
    with sub_valor_medio:
        st.markdown("### Valor Médio de Comercialização por Atendimento no Rio Grande do Norte")

        sql_vm_rn = """
            SELECT
                municipio_armazem_venda AS municipio,
                SUM(numero_atendimentos) AS total_atendimentos,
                ROUND(SUM(valor_comercializado), 2) AS valor_total_reais,
                ROUND(
                    SUM(valor_comercializado) /
                    NULLIF(SUM(numero_atendimentos), 0), 2
                ) AS valor_medio_por_atendimento
            FROM conab_venda_balcao
            WHERE uf = 'RN'
            GROUP BY municipio_armazem_venda
            ORDER BY valor_medio_por_atendimento DESC
        """
        df_vm_rn = query_publica(sql_vm_rn)

        if not df_vm_rn.empty:
            opcoes_vm = {
                "Valor Médio por Atendimento (R$)": ("valor_medio_por_atendimento", "moeda", "R$ por atendimento"),
                "Valor Total Comercializado (R$)": ("valor_total_reais", "moeda", "Valor total (R$)"),
                "Total de Atendimentos": ("total_atendimentos", "int", "Atendimentos")
            }

            ind_vm_nome = st.selectbox("Indicador em destaque:", list(opcoes_vm.keys()), key="ind_vm_rn")
            col_vm_sel, fmt_vm_sel, eixo_vm_label = opcoes_vm[ind_vm_nome]

            exibir_metricas_destaque(df_vm_rn, col_vm_sel, "municipio", formato=fmt_vm_sel)
            st.divider()

            df_vm_ord = df_vm_rn.sort_values(by=col_vm_sel, ascending=False).reset_index(drop=True)

            col_t5, col_g5 = st.columns([1, 1.3])
            with col_t5:
                st.markdown("**Valor médio por atendimento nos municípios do RN**")
                df_t5_exib = pd.DataFrame({
                    "Município": df_vm_ord["municipio"],
                    "Atendimentos": df_vm_ord["total_atendimentos"].apply(formatar_int),
                    "Valor total (R$)": df_vm_ord["valor_total_reais"].apply(formatar_decimal),
                    "Média (R$)": df_vm_ord["valor_medio_por_atendimento"].apply(formatar_decimal)
                })
                st.dataframe(df_t5_exib, use_container_width=True, hide_index=True)

            with col_g5:
                st.markdown(f"**{ind_vm_nome} por município**")
                grafico_barras_horizontal(
                    df_vm_ord,
                    col_cat="municipio",
                    col_val=col_vm_sel,
                    titulo=f"{ind_vm_nome} nos municípios do RN",
                    label_x=eixo_vm_label,
                    label_y="Município",
                    cor="#1b7857"
                )

    # --------------------------------------------------------------------------
    # Desempenho Regional — Polos de Abastecimento no Rio Grande do Norte
    # --------------------------------------------------------------------------
    with sub_polos:
        st.markdown("### Desempenho Regional — Polos de Abastecimento no Rio Grande do Norte")

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
        df_rn = query_publica(sql_vb_rn)

        if not df_rn.empty:
            opcoes_metricas = {
                "Volume Total Comercializado (kg)": {"coluna": "Total_kg", "cor": "#10b981", "formato": "int"},
                "Média Mensal Comercializada (kg)": {"coluna": "Media_Mensal_kg", "cor": "#3b82f6", "formato": "decimal"},
                "Maior Volume Registrado no Mês (kg)": {"coluna": "Max_kg", "cor": "#f59e0b", "formato": "int"},
                "Menor Volume Registrado no Mês (kg)": {"coluna": "Min_kg", "cor": "#ec4899", "formato": "int"},
                "Valor Total Movimentado (R$)": {"coluna": "Total_Reais", "cor": "#8b5cf6", "formato": "moeda"},
                "Total de Produtores / Clientes Atendidos": {"coluna": "Clientes_Atendidos", "cor": "#06b6d4", "formato": "int"}
            }

            metrica_escolhida = st.selectbox(
                "Selecione o indicador para análise e visualização:",
                list(opcoes_metricas.keys()),
                key="sel_metrica_polos"
            )

            config_atual = opcoes_metricas[metrica_escolhida]
            coluna_dados = config_atual["coluna"]
            cor_grafico = config_atual["cor"]
            formato_dados = config_atual["formato"]

            exibir_metricas_destaque(df_rn, coluna_dados, "Polo_RN", formato=formato_dados)
            st.divider()

            df_rn_ord = df_rn.sort_values(by=coluna_dados, ascending=False).reset_index(drop=True)

            df_rn_exibicao = df_rn_ord.rename(columns={
                "Polo_RN": "Polo Regional (RN)",
                "Total_kg": "Volume Total (kg)",
                "Media_Mensal_kg": "Média Mensal (kg)",
                "Min_kg": "Menor Volume Mensal (kg)",
                "Max_kg": "Maior Volume Mensal (kg)",
                "Total_Reais": "Valor Movimentado (R$)",
                "Clientes_Atendidos": "Pequenos Produtores Atendidos"
            })
            st.dataframe(df_rn_exibicao, use_container_width=True, hide_index=True)

            st.markdown(f"#### Comparativo entre Polos — {metrica_escolhida}")
            grafico_barras_horizontal(
                df_rn_ord,
                col_cat="Polo_RN",
                col_val=coluna_dados,
                titulo=f"Comparativo entre Polos — {metrica_escolhida}",
                label_x=metrica_escolhida,
                label_y="Polo Regional (RN)",
                cor=cor_grafico
            )
