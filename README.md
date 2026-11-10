# 🌱 Feira Online Sustentável — RN

Projeto acadêmico desenvolvido na disciplina de **Banco de Dados (DCA3604)** da Universidade Federal do Rio Grande do Norte (UFRN).

A Feira Online Sustentável — RN propõe uma plataforma digital para aproximar produtores agrícolas e consumidores do Rio Grande do Norte, facilitando a divulgação de produtos e o gerenciamento de informações relacionadas à comercialização.

O projeto combina a implementação de bancos de dados relacionais com a integração e análise de dados públicos sobre produção orgânica, comercialização agrícola e indicadores de oferta e demanda.

Desenvolvido utilizando **MySQL, Python e Streamlit**, o sistema reúne funcionalidades de gerenciamento de dados e visualização de informações, aplicando conceitos de modelagem, manipulação e integração de bancos de dados.

---

## 📌 Sobre o projeto

A solução é organizada em duas frentes complementares:

- **Gestão da feira virtual:** gerenciamento de produtores, categorias, produtos, clientes e pedidos por meio de um banco de dados operacional.
- **Análise de dados públicos:** armazenamento, consulta e visualização de informações agrícolas disponibilizadas por bases governamentais.

Essa integração permite explorar informações sobre o cenário agrícola brasileiro, com atenção especial ao Rio Grande do Norte, contribuindo para contextualizar a proposta da feira virtual.

---

## 🚀 Funcionalidades

A aplicação desenvolvida em Streamlit apresenta quatro áreas principais:

| Área | Funcionalidades |
|---|---|
| **Catálogo e Faturamento** | Consulta de produtos disponíveis, filtros por município e categoria e visualização do desempenho de vendas por produtor. |
| **Gestão de Produtos** | Cadastro de novos produtos, atualização de preços e estoques e exclusão de produtos. |
| **Rede de Produtores** | Cadastro, busca, edição e listagem de produtores cadastrados na plataforma. |
| **Inteligência de Mercado** | Visualização de indicadores agrícolas provenientes dos dados públicos da CONAB, com tabelas e gráficos interativos. |

---

## 🗄️ Bancos de dados

O projeto utiliza dois bancos de dados MySQL, separados conforme suas finalidades.

### 1. Banco operacional — `db_feira_online`

Responsável pelo gerenciamento das informações necessárias ao funcionamento da feira virtual.

| Tabela | Finalidade |
|---|---|
| `tb_produtor` | Cadastro e identificação dos produtores. |
| `tb_categoria` | Organização das categorias de produtos. |
| `tb_produto` | Cadastro de produtos, preços e estoques. |
| `tb_cliente` | Cadastro dos consumidores. |
| `tb_pedido` | Registro dos pedidos realizados. |
| `tb_item_pedido` | Associação entre pedidos e produtos, incluindo quantidades e preços praticados. |

**Views implementadas:**

- `vw_catalogo_feira`: disponibiliza informações dos produtos, categorias, preços, estoques e respectivos produtores.
- `vw_faturamento_produtor`: apresenta informações consolidadas sobre o desempenho das vendas por produtor.

### 2. Banco analítico — `analise_publica_dos_dados`

Destinado ao armazenamento e à análise de conjuntos de dados públicos relacionados ao setor agrícola.

| Tabela | Origem | Finalidade |
|---|---|---|
| `cnpo_produtores` | MAPA | Armazena informações dos produtores orgânicos cadastrados. |
| `conab_venda_balcao` | CONAB | Reúne registros de comercialização do Programa de Venda em Balcão. |
| `conab_oferta_demanda` | CONAB | Armazena indicadores de produção, consumo, importação, exportação e estoques agrícolas. |

**View implementada:**

- `vw_resumo_oferta_demanda`: apresenta indicadores estatísticos de oferta e demanda agrupados por produto.

---

## 📊 Análise de dados públicos

Foram utilizados três conjuntos de dados relacionados à produção e à comercialização agrícola:

| Conjunto de dados | Instituição | Informações analisadas |
|---|---|---|
| Cadastro Nacional de Produtores Orgânicos (CNPO) | Ministério da Agricultura e Pecuária (MAPA) | Distribuição de produtores orgânicos por estado e município. |
| Programa de Venda em Balcão | Companhia Nacional de Abastecimento (CONAB) | Volume e valor de comercialização por estado e município. |
| Dados de Oferta e Demanda | CONAB | Indicadores de produção, consumo, importação, exportação e estoques por produto e safra. |

As consultas SQL desenvolvidas permitem investigar:

- Distribuição territorial dos produtores orgânicos no Brasil e no Rio Grande do Norte.
- Volume e valor de comercialização de produtos agrícolas por estado.
- Variação dos indicadores de produção e consumo entre produtos e safras.
- Valor médio de comercialização por atendimento nos municípios do Rio Grande do Norte.

### Fontes dos dados

- **MAPA — Cadastro Nacional de Produtores Orgânicos:**

  https://mapa-indicadores.agricultura.gov.br/publico/extensions/CNPO_Painel_de_Indicadores/CNPO_Painel_de_Indicadores.html

- **CONAB — Agriculture & Food Security: CONAB Data:**

  https://www.kaggle.com/datasets/jadsonchagas/agriculture-and-food-security-conab-data

---

## 🛠️ Tecnologias utilizadas

| Tecnologia | Aplicação no projeto |
|---|---|
| **MySQL** | Criação, gerenciamento e consulta aos bancos de dados relacionais. |
| **Python** | Tratamento, organização e importação dos dados públicos. |
| **Pandas** | Manipulação e organização dos dados utilizados nas análises. |
| **Streamlit** | Desenvolvimento da interface interativa e do dashboard. |
| **MySQL Connector** | Comunicação entre a aplicação Python e os bancos MySQL. |
| **SQL** | Modelagem, manipulação, consultas e criação de views. |

---

## 📁 Organização do repositório

```text
Feira-Online-Sustentavel-RN/
│
├── app/
│   └── app_feira.py
│
├── data/
│   ├── raw/
│  └── processed/
|
├── database/
│   ├── schema_feira/
│   │   └── db_feira_online.sql
│   │
│   └── schema_dados_publicos/
│       └── analise_publica_dos_dados.sql
|
├── scripts/
│   ├── limpeza_de_dados.py
│   └── importar_dados_publicos.py
│
|
├── README.md
└── requirements.txt
```

**Descrição dos diretórios:**

| Diretório | Conteúdo |
|---|---|
| `app/` | Aplicação Streamlit para gerenciamento e visualização dos dados. |
| `database/schema_feira/` | Scripts SQL de criação do banco operacional da feira. |
| `database/schema_dados_publicos/` | Scripts SQL de criação do banco de análise dos dados públicos. |
| `data/raw/` | Arquivos originais dos conjuntos de dados públicos. |
| `data/processed/` | Arquivos CSV tratados e preparados para importação. |
| `scripts/` | Scripts Python para limpeza e importação dos dados. |

---

## ⚙️ Como executar localmente

### 1. Requisitos

Antes de executar o projeto, instale:

- Python;
- MySQL Server;
- Gerenciador de pacotes pip.

### 2. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd Feira-Online-Sustentavel-RN
```

### 3. Configurar o ambiente Python

Recomenda-se utilizar um ambiente virtual:

```bash
python -m venv venv
```

No Linux:

```bash
source venv/bin/activate
```

No Windows:

```bash
venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### 4. Criar os bancos de dados

Com o MySQL em funcionamento, execute os scripts SQL na seguinte ordem:

**Banco operacional:**

```bash
mysql -u SEU_USUARIO -p < database/schema_feira/db_feira_online.sql
```

**Banco de dados públicos:**

```bash
mysql -u SEU_USUARIO -p < database/schema_dados_publicos/analise_publica_dos_dados.sql
```

Os scripts são responsáveis pela criação das estruturas e tabelas necessárias ao projeto.

### 5. Configurar as credenciais do MySQL

Configure as seguintes variáveis de ambiente no sistema:

```bash
export MYSQL_HOST="localhost"
export MYSQL_USER="seu_usuario"
export MYSQL_PASSWORD="sua_senha"
```

O arquivo `.env.example` disponibiliza um modelo de configuração. Entretanto, os scripts atuais não carregam arquivos `.env` automaticamente. Portanto, as variáveis devem estar disponíveis no ambiente de execução.

### 6. Tratar os dados públicos

Caso seja necessário gerar novamente os arquivos tratados, execute:

```bash
python scripts/limpeza_de_dados.py
```

Os arquivos tratados são disponibilizados no diretório `data/processed/`.

### 7. Importar os dados públicos

Após o tratamento, execute:

```bash
python scripts/importar_dados_publicos.py
```

O script realiza a conexão com o MySQL e insere os dados nas respectivas tabelas do banco analítico.

**Atenção:** a importação pode duplicar registros caso seja executada repetidamente. Antes de realizar uma nova importação, verifique se os dados já foram inseridos ou se existe algum procedimento de limpeza das tabelas.

### 8. Executar a aplicação

Com os bancos configurados e os dados necessários disponíveis, inicialize o Streamlit:

```bash
streamlit run app/app_feira.py
```

A aplicação poderá ser acessada pelo endereço local apresentado no terminal pelo Streamlit.

---

## 📚 Documentação

A documentação acadêmica e técnica do projeto contempla:

- Levantamento de requisitos funcionais e regras de integridade.
- Diagramas Entidade-Relacionamento (ER).
- Modelos relacionais com identificação de chaves primárias e estrangeiras.
- Scripts SQL de criação das estruturas e consultas.
- Análises estatísticas dos conjuntos de dados públicos.
- Relatório técnico com a descrição da implementação e dos resultados.

---

## ⚠️ Observações e limitações

- O funcionamento integral depende de uma instância MySQL devidamente configurada.
- Os bancos de dados precisam ser criados antes da execução da aplicação.
- O banco operacional necessita de registros adequados para que as consultas e funcionalidades relacionadas à feira apresentem resultados.
- A importação dos dados públicos deve ser realizada após o tratamento dos arquivos CSV.
- A execução da aplicação depende das bibliotecas e das configurações especificadas no projeto.
- A organização dos arquivos e a documentação não representam, isoladamente, uma validação completa de execução em outros ambientes.

---

## 🔒 Segurança

- Não publique senhas reais ou arquivos `.env` no repositório.
- Utilize `.env.example` apenas como modelo de configuração.
- Mantenha as credenciais do MySQL armazenadas em variáveis de ambiente.
- Verifique se arquivos contendo informações sensíveis estão incluídos no `.gitignore`.

---

## 👥 Equipe

Projeto desenvolvido por:

- Caio de Miranda Silva
- Débora Nicolly Araujo da Silva
- Douglas Amon Passos dos Anjos
- Paulo Guilherme Xavier da Silva

**Universidade Federal do Rio Grande do Norte (UFRN)**  
Disciplina: Banco de Dados (DCA3604)  
Ano: 2026
