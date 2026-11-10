CREATE DATABASE IF NOT EXISTS db_feira_online
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_feira_online;

-- 1. Tabela de Produtores (alinhada à estrutura do CNPO/MAPA)
CREATE TABLE tb_produtor (
    id_produtor INT AUTO_INCREMENT PRIMARY KEY,
    nome_produtor VARCHAR(150) NOT NULL,
    cpf_cnpj VARCHAR(20) NOT NULL UNIQUE,
    tipo_certificacao ENUM('OCS', 'OPAC', 'CERTIFICADORA', 'AGRICULTURA_FAMILIAR') NOT NULL DEFAULT 'OCS',
    entidade_certificadora VARCHAR(200),
    escopo_producao VARCHAR(150) NOT NULL DEFAULT 'PRODUCAO PRIMARIA VEGETAL',
    cidade VARCHAR(100) NOT NULL,
    uf CHAR(2) NOT NULL DEFAULT 'RN',
    contato VARCHAR(120),
    situacao ENUM('ATIVO', 'SUSPENSO', 'INATIVO') NOT NULL DEFAULT 'ATIVO',
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela de Categorias
CREATE TABLE tb_categoria (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nome_categoria VARCHAR(80) NOT NULL UNIQUE,
    descricao VARCHAR(255)
);

-- 3. Tabela de Produtos da Feira Online
CREATE TABLE tb_produto (
    id_produto INT AUTO_INCREMENT PRIMARY KEY,
    id_produtor INT NOT NULL,
    id_categoria INT NOT NULL,
    nome_produto VARCHAR(120) NOT NULL,
    unidade_medida ENUM('kg', 'unidade', 'maco', 'bandeja', 'duzia', 'litro') NOT NULL DEFAULT 'kg',
    preco_unitario DECIMAL(10, 2) NOT NULL CHECK (preco_unitario > 0),
    estoque_disponivel DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (estoque_disponivel >= 0),
    organico_certificado BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_produto_produtor FOREIGN KEY (id_produtor) 
        REFERENCES tb_produtor(id_produtor) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_produto_categoria FOREIGN KEY (id_categoria) 
        REFERENCES tb_categoria(id_categoria) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 4. Tabela de Clientes
CREATE TABLE tb_cliente (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nome_cliente VARCHAR(150) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    telefone VARCHAR(30),
    cidade VARCHAR(100) NOT NULL DEFAULT 'Natal',
    uf CHAR(2) NOT NULL DEFAULT 'RN',
    endereco_entrega VARCHAR(255) NOT NULL
);

-- 5. Tabela de Pedidos
CREATE TABLE tb_pedido (
    id_pedido INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    status_pedido ENUM('PENDENTE', 'CONFIRMADO', 'ENTREGUE', 'CANCELADO') NOT NULL DEFAULT 'CONFIRMADO',
    modalidade_entrega ENUM('RETIRADA_PONTO_FEIRA', 'ENTREGA_DOMICILIO') NOT NULL DEFAULT 'ENTREGA_DOMICILIO',
    CONSTRAINT fk_pedido_cliente FOREIGN KEY (id_cliente) 
        REFERENCES tb_cliente(id_cliente) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 6. Tabela Associativa de Itens do Pedido
CREATE TABLE tb_item_pedido (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade DECIMAL(10, 2) NOT NULL CHECK (quantidade > 0),
    preco_unitario_venda DECIMAL(10, 2) NOT NULL CHECK (preco_unitario_venda > 0),
    CONSTRAINT fk_item_pedido FOREIGN KEY (id_pedido) 
        REFERENCES tb_pedido(id_pedido) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_item_produto FOREIGN KEY (id_produto) 
        REFERENCES tb_produto(id_produto) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- VIEW 1: Catálogo Completo da Feira
CREATE OR REPLACE VIEW vw_catalogo_feira AS
SELECT 
    p.id_produto,
    p.nome_produto,
    c.nome_categoria,
    p.unidade_medida,
    p.preco_unitario,
    p.estoque_disponivel,
    pr.id_produtor,
    pr.nome_produtor,
    pr.tipo_certificacao,
    pr.cidade AS cidade_origem,
    pr.uf AS uf_origem,
    pr.situacao AS status_produtor
FROM tb_produto p
INNER JOIN tb_produtor pr ON p.id_produtor = pr.id_produtor
INNER JOIN tb_categoria c ON p.id_categoria = c.id_categoria;

-- VIEW 2: Desempenho Financeiro e Volume de Vendas por Produtor
CREATE OR REPLACE VIEW vw_faturamento_produtor AS
SELECT 
    pr.id_produtor,
    pr.nome_produtor,
    pr.cidade,
    pr.tipo_certificacao,
    COUNT(DISTINCT ip.id_pedido) AS total_pedidos,
    COALESCE(SUM(ip.quantidade), 0) AS volume_itens_vendidos,
    COALESCE(ROUND(SUM(ip.quantidade * ip.preco_unitario_venda), 2), 0.00) AS receita_total_reais
FROM tb_produtor pr
LEFT JOIN tb_produto p ON pr.id_produtor = p.id_produtor
LEFT JOIN tb_item_pedido ip ON p.id_produto = ip.id_produto
GROUP BY pr.id_produtor, pr.nome_produtor, pr.cidade, pr.tipo_certificacao;

-- Carga Inicial de Dados (Baseada nos Municípios do RN presentes no CNPO)
INSERT INTO tb_categoria (nome_categoria, descricao) VALUES
('Hortaliças e Folhosas', 'Alface, rúcula, coentro, couve e hortaliças frescas sem agrotóxicos'),
('Frutas Tropicais', 'Banana, mamão, melancia, cajarana, manga e acerola'),
('Raízes e Tubérculos', 'Macaxeira, batata-doce, inhame e jerimum'),
('Ovos e Derivados', 'Ovos caipiras orgânicos e derivados da agricultura familiar'),
('Processados Artesanais', 'Farinha de mandioca, polpas de frutas, mel e goma');

INSERT INTO tb_produtor (nome_produtor, cpf_cnpj, tipo_certificacao, entidade_certificadora, escopo_producao, cidade, uf, contato, situacao) VALUES
('Francisca Alves da Costa', '102.345.678-90', 'OCS', 'OCS Gramorezinho Agroecológico', 'PRODUCAO PRIMARIA VEGETAL', 'NATAL', 'RN', 'francisca.ocs@email.com', 'ATIVO'),
('João Batista de Oliveira', '213.456.789-01', 'OCS', 'OCS Assentamento Mulunguzinho', 'PRODUCAO PRIMARIA VEGETAL', 'MOSSORO', 'RN', 'joao.mossoro@email.com', 'ATIVO'),
('Maria das Graças Dantas', '324.567.890-12', 'OPAC', 'Associação Agroecológica do Sertão do Apodi', 'PRODUCAO PRIMARIA VEGETAL; PROCESSAMENTO', 'APODI', 'RN', 'graca.apodi@email.com', 'ATIVO'),
('Severino Ramos Potengi', '435.678.901-23', 'OCS', 'OCS Sabugi Sustentável', 'PRODUCAO PRIMARIA ANIMAL E VEGETAL', 'SAO PAULO DO POTENGI', 'RN', 'severino.potengi@email.com', 'ATIVO');

INSERT INTO tb_produto (id_produtor, id_categoria, nome_produto, unidade_medida, preco_unitario, estoque_disponivel, organico_certificado) VALUES
(1, 1, 'Alface Crespa Orgânica (Gramorezinho)', 'maco', 4.50, 85.00, TRUE),
(1, 1, 'Coentro Fresco Agroecológico', 'maco', 3.50, 120.00, TRUE),
(2, 3, 'Jerimum Caboclo Orgânico', 'kg', 6.80, 210.00, TRUE),
(2, 2, 'Melancia Orgânica sem Agrotóxico', 'kg', 3.90, 350.00, TRUE),
(3, 5, 'Polpa de Cajarana Integral (Chapada do Apodi)', 'kg', 16.00, 60.00, TRUE),
(4, 4, 'Ovos Caipiras Orgânicos', 'duzia', 14.50, 45.00, TRUE);

INSERT INTO tb_cliente (nome_cliente, email, telefone, cidade, uf, endereco_entrega) VALUES
('Ana Clara Medeiros', 'anaclara@ufrn.edu.br', '(84) 99911-2233', 'Natal', 'RN', 'Av. Senador Salgado Filho, 3000 - Lagoa Nova'),
('Carlos Eduardo Varela', 'carloseduardo@email.com', '(84) 98822-3344', 'Parnamirim', 'RN', 'Rua Maria Lacerda Montenegro, 450 - Nova Parnamirim');

INSERT INTO tb_pedido (id_cliente, status_pedido, modalidade_entrega) VALUES
(1, 'CONFIRMADO', 'RETIRADA_PONTO_FEIRA'),
(2, 'ENTREGUE', 'ENTREGA_DOMICILIO');

INSERT INTO tb_item_pedido (id_pedido, id_produto, quantidade, preco_unitario_venda) VALUES
(1, 1, 3, 4.50),
(1, 6, 2, 14.50),
(2, 3, 5, 6.80),
(2, 5, 2, 16.00);