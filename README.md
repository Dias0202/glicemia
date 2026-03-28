# GlycemiBot - Sistema de Monitoramento e Predicao Glicemica

Bot de Telegram para monitoramento continuo de glicemia, calculo automatico de doses de insulina e registro de dados nutricionais. Utiliza processamento de linguagem natural (NLP) para extrair informacoes de refeicoes e gera visualizacoes graficas do historico glicemico.

## Funcionalidades

| Comando | Descricao |
|---------|-----------|
| `/start` | Mensagem de boas-vindas com lista de comandos |
| `/perfil` | Configuracao de perfil clinico (idade, peso, altura, HbA1c, insulina basal) |
| `/registrar` | Registro de glicemia, refeicao (com NLP) e insulina aplicada |
| `/historico` | Visualizacao dos ultimos 10 registros |
| `/grafico` | Grafico de tendencia glicemica dos ultimos 7 dias |
| `/buscar <alimento>` | Busca de carboidratos na tabela TACO (597 alimentos) |
| `/ajuda` | Ajuda detalhada sobre todos os comandos |
| `/cancelar` | Cancela qualquer operacao em andamento |

## Arquitetura

```
glycemic_bot/
├── main.py                          # Ponto de entrada (bot + health check server)
├── core/
│   └── config.py                    # Carregamento e validacao de variaveis de ambiente
├── database/
│   └── supabase_client.py           # Cliente Supabase (PostgreSQL)
├── handlers/
│   └── telegram_handlers.py         # Handlers do Telegram (state machines)
├── services/
│   ├── nlp_service.py               # Extracao de dados via Groq API (LLama 3.1)
│   ├── calculator_service.py        # Calculo de dose de insulina bolus
│   └── chart_service.py             # Geracao de graficos (matplotlib)
├── repositories/
│   ├── user_repository.py           # CRUD de perfil do usuario + calculo de IMC
│   ├── logs_repository.py           # Insercao e consulta de logs glicemicos
│   └── food_repository.py           # Busca de alimentos na tabela TACO
├── scripts/
│   └── ingest_taco.py               # Script de ingestao da tabela TACO no Supabase
├── taco/                            # Tabela Brasileira de Composicao de Alimentos
│   ├── tabelas/                     # CSVs com dados nutricionais (~600 alimentos)
│   └── originais/                   # PDFs e XLS originais da UNICAMP/NEPA
└── tests/                           # Testes unitarios (pytest)
    ├── conftest.py                  # Mocks globais (Supabase, Groq)
    ├── test_calculator_service.py   # Testes de calculo de bolus
    ├── test_user_repository.py      # Testes de calculo de IMC
    ├── test_chart_service.py        # Testes de geracao de graficos
    ├── test_logs_repository.py      # Testes de insercao/consulta de logs
    └── test_food_repository.py      # Testes de busca de alimentos
```

### Padrao de Camadas

```
Telegram (Usuario)
    |
    v
Handlers (State Machines / ConversationHandler)
    |
    v
Services (NLP, Calculadora, Graficos)
    |
    v
Repositories (User, Logs, Food)
    |
    v
Supabase (PostgreSQL)
```

## Stack Tecnologica

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.10+ |
| Bot Framework | python-telegram-bot 20.8 |
| NLP/LLM | Groq API (llama-3.1-8b-instant) |
| Banco de Dados | Supabase (PostgreSQL gerenciado) |
| Visualizacao | Matplotlib |
| Deploy | Render (Web Service com health check) |

## Banco de Dados

### Tabela `user_profiles`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `telegram_user_id` | bigint (PK) | ID unico do usuario no Telegram |
| `age` | integer | Idade |
| `weight` | float | Peso (kg) |
| `height` | float | Altura (m) |
| `bmi` | float | IMC calculado |
| `last_hba1c` | float | Ultima hemoglobina glicada |
| `basal_insulin_dose` | float | Dose diaria de insulina basal (UI) |
| `basal_insulin_time` | text | Horario de aplicacao da basal |

### Tabela `glycemic_logs`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `id` | serial (PK) | ID auto-incremento |
| `telegram_user_id` | bigint (FK) | Vinculo com o usuario |
| `timestamp` | timestamptz | Data/hora da medicao (ISO 8601 UTC) |
| `glucose_level` | integer | Glicemia medida (mg/dL) |
| `carbs_ingested` | float | Carboidratos ingeridos (g) |
| `bolus_insulin` | float | Insulina rapida aplicada (UI) |
| `basal_insulin` | float | Insulina basal aplicada (UI) |
| `exercise_done` | boolean | Se houve exercicio |
| `exercise_intensity` | text | Intensidade (Baixa/Media/Alta) |
| `mood` | text | Estado emocional |
| `refeicao` | text | Tipo de refeicao |

### Tabela `food_reference`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `id` | serial (PK) | ID auto-incremento |
| `food_name` | text | Nome do alimento (TACO) |
| `portion_size` | float | Tamanho da porcao (default: 100) |
| `unit` | text | Unidade (g) |
| `carbs_per_portion` | float | Carboidratos por porcao (g) |

## Instalacao e Configuracao

### Pre-requisitos

- Python 3.10+
- Conta no [Supabase](https://supabase.com/) (tier gratuito)
- Bot criado via [@BotFather](https://t.me/BotFather) no Telegram
- Chave da API [Groq](https://console.groq.com/)

### Passo a passo

1. **Clone o repositorio**
```bash
git clone https://github.com/Dias0202/glicemia.git
cd glicemia
```

2. **Crie e ative o ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Instale as dependencias**
```bash
pip install -r requirements.txt
```

4. **Configure as variaveis de ambiente**
```bash
cp .env.example .env
# Edite o .env com suas credenciais
```

5. **Crie as tabelas no Supabase**

Execute o seguinte DDL no SQL Editor do Supabase:

```sql
CREATE TABLE user_profiles (
    telegram_user_id BIGINT PRIMARY KEY,
    age INTEGER,
    weight REAL,
    height REAL,
    bmi REAL,
    last_hba1c REAL,
    basal_insulin_dose REAL,
    basal_insulin_time TEXT
);

CREATE TABLE glycemic_logs (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES user_profiles(telegram_user_id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    glucose_level INTEGER,
    carbs_ingested REAL,
    bolus_insulin REAL,
    basal_insulin REAL,
    exercise_done BOOLEAN DEFAULT FALSE,
    exercise_intensity TEXT,
    mood TEXT,
    refeicao TEXT
);

CREATE TABLE food_reference (
    id SERIAL PRIMARY KEY,
    food_name TEXT NOT NULL,
    portion_size REAL DEFAULT 100.0,
    unit TEXT DEFAULT 'g',
    carbs_per_portion REAL
);
```

6. **Popule a tabela de alimentos (TACO)**
```bash
python scripts/ingest_taco.py
```

7. **Inicie o bot**
```bash
python main.py
```

## Testes

```bash
pip install pytest
python -m pytest tests/ -v
```

Os testes cobrem:
- **calculator_service**: calculo de bolus com diferentes fatores e edge cases
- **user_repository**: calculo de IMC (metros, centimetros, valores invalidos)
- **chart_service**: geracao de graficos PNG, dados vazios, ponto unico
- **logs_repository**: insercao, auto-timestamp, filtragem de nulls, consulta
- **food_repository**: busca por nome, resultado vazio, tratamento de erros

## Deploy (Render)

1. Conecte o repositorio GitHub ao Render
2. Tipo de servico: **Web Service**
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Configure as variaveis de ambiente no painel do Render
6. O health check responde na porta definida pela variavel `PORT` (default: 10000)

## Fluxo de Uso

### Primeiro acesso
1. Envie `/start` para ver os comandos
2. Use `/perfil` para cadastrar seus dados clinicos
3. O bot calcula seu IMC automaticamente

### Uso diario
1. Envie `/registrar`
2. Informe sua glicemia atual (mg/dL)
3. Descreva sua refeicao (ou digite "nada")
4. O bot usa NLP para estimar carboidratos e sugerir dose de insulina
5. Informe a insulina que aplicou de fato
6. Registro salvo no banco de dados

### Consultas
- `/historico` para ver registros recentes
- `/grafico` para visualizar a tendencia glicemica
- `/buscar arroz` para consultar carboidratos de alimentos

## Variaveis de Ambiente

| Variavel | Obrigatoria | Descricao |
|----------|-------------|-----------|
| `TELEGRAM_TOKEN` | Sim | Token do bot Telegram |
| `SUPABASE_URL` | Sim | URL do projeto Supabase |
| `SUPABASE_KEY` | Sim | Chave anonima do Supabase |
| `GROQ_API_KEY` | Sim | Chave da API Groq |
| `CARB_FACTOR` | Nao | Fator de sensibilidade a carboidratos (default: 15) |
| `PORT` | Nao | Porta do health check (default: 10000) |

## Objetivo Futuro (ML)

O projeto foi desenhado para coletar dados longitudinais com alta granularidade temporal. O dataset acumulado servira para treinar modelos de Machine Learning (XGBoost, RNNs) capazes de prever variabilidade glicemica, identificando tendencias de hipoglicemia ou hiperglicemia com base no contexto comportamental e historico do usuario.

### Features planejadas para o modelo preditivo:
- Glicemia medida + timestamp (ciclo circadiano)
- Carga de carboidratos e tipo de refeicao
- Insulina aplicada (bolus + basal) e IOB (Insulin On Board)
- Exercicio fisico (tipo, intensidade, duracao)
- Nivel de estresse e humor

## Licenca

Projeto academico / uso pessoal.
