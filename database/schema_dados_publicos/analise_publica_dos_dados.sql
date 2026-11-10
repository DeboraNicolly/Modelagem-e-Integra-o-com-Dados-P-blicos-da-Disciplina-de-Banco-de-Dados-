CREATE DATABASE IF NOT EXISTS db_analise_publica
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_analise_publica;

-- Tabela do Cadastro Nacional de Produtores Orgânicos
CREATE TABLE cnpo_produtores (
    id_registro INT AUTO_INCREMENT PRIMARY KEY,
    tipo_entidade VARCHAR(50) NOT NULL,
    entidade VARCHAR(255) NOT NULL,
    pais VARCHAR(80) NOT NULL,
    uf VARCHAR(20),
    cidade VARCHAR(120) NOT NULL,
    situacao VARCHAR(30) NOT NULL,
    cnpf_cnpj_nif VARCHAR(40),
    nome_produtor VARCHAR(255) NOT NULL,
    escopo TEXT,
    atividade TEXT,
    contato TEXT,
    ano INT NOT NULL,
    mes VARCHAR(15) NOT NULL
);

-- Tabela do Programa Venda em Balcão
CREATE TABLE conab_venda_balcao (
    id_venda INT AUTO_INCREMENT PRIMARY KEY,
    num_ano_gravacao INT NOT NULL,
    num_mes_gravacao INT NOT NULL,
    municipio_armazem_venda VARCHAR(120) NOT NULL,
    uf CHAR(2) NOT NULL,
    qtd_produto_kg BIGINT NOT NULL,
    valor_comercializado DECIMAL(15, 2) NOT NULL,
    numero_atendimentos INT NOT NULL,
    clientes_atendidos INT NOT NULL
);

-- Tabela de Balanço de Oferta e Demanda
CREATE TABLE conab_oferta_demanda (
    id_balanco INT AUTO_INCREMENT PRIMARY KEY,
    produto VARCHAR(80) NOT NULL,
    id_produto INT NOT NULL,
    dsc_safra VARCHAR(20) NOT NULL,
    estoque_inicial_1000t DECIMAL(12, 2) NOT NULL,
    producao_1000t DECIMAL(12, 2) NOT NULL,
    importacao_1000t DECIMAL(12, 2) NOT NULL,
    consumo_1000t DECIMAL(12, 2) NOT NULL,
    exportacao_1000t DECIMAL(12, 2) NOT NULL,
    estoque_final_1000t DECIMAL(12, 2) NOT NULL
);