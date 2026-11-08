USE db_analise_publica;

-- 1° consulta: Ranking estadual de venda em balcão
-- Qual a relevância do RN na demanda de pequenos produtores por insumos?
SELECT 
    uf,
    COUNT(*) AS total_registros_mensais,
    SUM(qtd_produto_kg) AS volume_total_kg,
    ROUND(AVG(qtd_produto_kg), 2) AS media_mensal_kg,
    MIN(qtd_produto_kg) AS menor_volume_kg,
    MAX(qtd_produto_kg) AS maior_volume_kg,
    ROUND(SUM(valor_comercializado), 2) AS valor_total_reais,
    ROUND(SUM(valor_comercializado) / SUM(qtd_produto_kg), 2) AS preco_medio_kg,
    SUM(clientes_atendidos) AS total_clientes_atendidos
FROM conab_venda_balcao
GROUP BY uf
ORDER BY volume_total_kg DESC
LIMIT 10;

--  2° consulta: Desempenho dos Polos do RN no Programa Venda em Balcão
-- Quais polos potiguares concentram maior atendimento a pequenos produtores?
SELECT 
    municipio_armazem_venda AS polo_rn,
    SUM(qtd_produto_kg) AS total_kg,
    ROUND(AVG(qtd_produto_kg), 2) AS media_kg_mensal,
    ROUND(SUM(valor_comercializado), 2) AS total_reais,
    SUM(numero_atendimentos) AS total_atendimentos,
    ROUND(AVG(clientes_atendidos), 1) AS media_clientes_mes,
    MAX(clientes_atendidos) AS pico_clientes_mes
FROM conab_venda_balcao
WHERE uf = 'RN'
GROUP BY municipio_armazem_venda
ORDER BY total_kg DESC;

--  3° consulta: Distribuição de Produtores Orgânicos no RN por Cidade e Modalidade (CNPO)
-- Onde estão os produtores orgânicos no RN e quantos atuam em venda direta (OCS)?
SELECT 
    cidade,
    COUNT(*) AS total_produtores,
    SUM(CASE WHEN tipo_entidade = 'OCS' THEN 1 ELSE 0 END) AS qtd_ocs_venda_direta,
    SUM(CASE WHEN tipo_entidade = 'OPAC' THEN 1 ELSE 0 END) AS qtd_opac,
    SUM(CASE WHEN tipo_entidade = 'CERTIFICADORA' THEN 1 ELSE 0 END) AS qtd_certificadora
FROM cnpo_produtores
WHERE uf = 'RN' AND situacao = 'ATIVO'
GROUP BY cidade
ORDER BY total_produtores DESC
LIMIT 10;

--  4° consulta: histórico de oferta x Demanda interna e exportação
CREATE OR REPLACE VIEW vw_resumo_oferta_demanda AS
SELECT 
    produto,
    COUNT(dsc_safra) AS qtd_safras,
    ROUND(AVG(producao_1000t), 2) AS media_producao_1000t,
    ROUND(AVG(consumo_1000t), 2) AS media_consumo_1000t,
    ROUND(AVG(importacao_1000t), 2) AS media_importacao_1000t,
    ROUND(AVG(exportacao_1000t), 2) AS media_exportacao_1000t,
    MIN(producao_1000t) AS min_producao_1000t,
    MAX(producao_1000t) AS max_producao_1000t,
    ROUND(AVG(producao_1000t - consumo_1000t), 2) AS saldo_medio_interno_1000t
FROM conab_oferta_demanda
GROUP BY produto;