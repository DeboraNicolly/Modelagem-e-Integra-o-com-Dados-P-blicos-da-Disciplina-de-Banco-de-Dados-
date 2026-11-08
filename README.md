# 🌱 Feira Online Sustentável — RN

Projeto acadêmico de **Modelagem e Integração com Dados Públicos**, utilizando MySQL, Python e Streamlit. A proposta combina a gestão de uma feira virtual de produtos agrícolas com análises de dados públicos relacionados à produção e ao abastecimento.

## Organização do repositório

| Pasta | Conteúdo |
|---|---|
| `app/` | Aplicação Streamlit para gestão e visualização |
| `database/schema_feira/` | Estrutura SQL do banco operacional `db_feira_online` |
| `database/schema_dados_publicos/` | Estrutura e consultas do banco analítico `db_analise_publica` |
| `data/raw/` | Planilhas e CSVs públicos originais |
| `data/processed/` | CSVs tratados pelos scripts |
| `scripts/` | Limpeza e importação de dados |
| `docs/modelo_er/` | Espaço para diagrama entidade-relacionamento |
| `docs/modelo_relacional/` | Espaço para o modelo relacional |
| `docs/relatorio/` | Espaço para relatório e documentação acadêmica |

## Bancos de dados

- **`db_feira_online`**: produtores, categorias, produtos, clientes, pedidos e itens de pedidos.
- **`db_analise_publica`**: produtores orgânicos (CNPO), venda em balcão e oferta/demanda (CONAB).

## Como executar localmente

1. Instale Python e MySQL e crie um ambiente virtual (opcional).
2. Instale as dependências: `pip install -r requirements.txt`.
3. Execute os scripts SQL de criação, começando por `database/schema_feira/db_feira_online.sql` e `database/schema_dados_publicos/analise_publica_dos_dados.sql`.
4. Configure `MYSQL_HOST`, `MYSQL_USER` e `MYSQL_PASSWORD` como variáveis de ambiente do seu sistema. O arquivo `.env.example` é apenas um modelo; os scripts não carregam `.env` automaticamente.
5. Se precisar gerar novamente os arquivos tratados, execute `python scripts/limpeza_de_dados.py`.
6. Importe os dados públicos com `python scripts/importar_dados_publicos.py`. **Atenção:** a importação insere registros e, se repetida, pode duplicá-los.
7. Execute `streamlit run app/app_feira.py`.

**Observação:** o funcionamento integral depende de MySQL configurado e de dados adequados no banco da feira. A organização dos arquivos não equivale à validação de execução do projeto.

## Modelagem e documentação pendentes

- [ ] Criar o diagrama ER do banco da feira
- [ ] Documentar o modelo relacional e as chaves PK/FK
- [ ] Documentar o banco analítico e a origem dos conjuntos de dados
- [ ] Preparar relatório acadêmico e evidências das consultas

## Segurança

Não publique senhas reais ou arquivos `.env`. Os scripts foram adaptados para ler as credenciais de variáveis de ambiente.
