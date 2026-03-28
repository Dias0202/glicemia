# GlycemiBot - Sistema de Monitoramento e Predicao Glicemica

Bot de Telegram para monitoramento continuo de glicemia, calculo clinico de doses de insulina e registro de dados nutricionais. Utiliza NLP para extrair informacoes de refeicoes, transcricao de voz (Whisper) para entrada por audio, e gera visualizacoes graficas do historico glicemico.

## Funcionalidades

| Comando | Descricao |
|---------|-----------|
| `/start` | Mensagem de boas-vindas com lista de comandos |
| `/perfil` | Perfil clinico completo (ICR, fator de correcao, glicemia alvo, etc) |
| `/registrar` | Registro com calculo automatico de dose (bolus + correcao) |
| `/historico` | Visualizacao dos ultimos 10 registros |
| `/grafico` | Grafico de tendencia glicemica dos ultimos 7 dias |
| `/buscar <alimento>` | Busca de carboidratos na tabela TACO (597 alimentos) |
| `/ajuda` | Ajuda detalhada sobre todos os comandos |
| `/cancelar` | Cancela qualquer operacao em andamento |

### Entrada por Voz

Todas as etapas de `/perfil` e `/registrar` aceitam mensagens de voz. O audio e transcrito automaticamente via Groq Whisper API (modelo `whisper-large-v3-turbo`) em portugues.

## Calculo Clinico de Insulina

O bot aplica a formula padrao de contagem de carboidratos usada na pratica clinica:

```
Bolus Alimentar = Carboidratos (g) / ICR
Dose de Correcao = (Glicemia Atual - Glicemia Alvo) / Fator de Correcao
Dose Total = Bolus Alimentar + Dose de Correcao
```

Onde:
- **ICR** (Insulin-to-Carb Ratio): gramas de carboidrato cobertas por 1U de insulina rapida
- **Fator de Correcao (FC)**: quantos mg/dL 1U de insulina rapida reduz a glicemia
- **Glicemia Alvo**: meta individual (padrao clinico: 100-120 mg/dL)

A dose de correcao so e calculada quando a glicemia esta acima do alvo. Alertas sao emitidos para hipoglicemia (<70 mg/dL) e hiperglicemia severa (>250 mg/dL).

## Arquitetura

```
glycemic_bot/
├── main.py                          # Ponto de entrada (bot + health check server)
├── core/
│   └── config.py                    # Carregamento e validacao de variaveis de ambiente
├── database/
│   └── supabase_client.py           # Cliente Supabase (PostgreSQL)
├── handlers/
│   └── telegram_handlers.py         # Handlers do Telegram (state machines + voz)
├── services/
│   ├── nlp_service.py               # Extracao de dados via Groq API (LLama 3.1)
│   ├── calculator_service.py        # Calculo clinico de insulina (bolus + correcao)
│   ├── chart_service.py             # Geracao de graficos (matplotlib)
│   └── voice_service.py             # Transcricao de voz (Groq Whisper)
├── repositories/
│   ├── user_repository.py           # CRUD de perfil do usuario + calculo de IMC
│   ├── logs_repository.py           # Insercao e consulta de logs glicemicos
│   └── food_repository.py           # Busca de alimentos na tabela TACO
├── scripts/
│   └── ingest_taco.py               # Script de ingestao da tabela TACO no Supabase
├── taco/                            # Tabela Brasileira de Composicao de Alimentos
│   ├── tabelas/                     # CSVs com dados nutricionais (~600 alimentos)
│   └── originais/                   # PDFs e XLS originais da UNICAMP/NEPA
└── tests/                           # Testes unitarios (pytest, 42 testes)
    ├── conftest.py                  # Mocks globais (Supabase, Groq)
    ├── test_calculator_service.py   # Testes de bolus, correcao e dose total
    ├── test_user_repository.py      # Testes de calculo de IMC
    ├── test_chart_service.py        # Testes de geracao de graficos
    ├── test_logs_repository.py      # Testes de insercao/consulta de logs
    ├── test_food_repository.py      # Testes de busca de alimentos
    └── test_voice_service.py        # Testes de transcricao de voz
```

### Padrao de Camadas

```
Telegram (Usuario - texto ou voz)
    |
    v
Handlers (State Machines / ConversationHandler)
    |
    ├──> Voice Service (Whisper) ──> texto transcrito
    v
Services (NLP, Calculadora Clinica, Graficos)
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
| Voz/STT | Groq Whisper (whisper-large-v3-turbo) |
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
| `insulin_carb_ratio` | float | Razao insulina/carboidrato (ICR) |
| `correction_factor` | float | Fator de correcao (FC) |
| `target_glucose` | integer | Glicemia alvo (mg/dL) |

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
- Chave da API [Groq](https://console.groq.com/) (NLP + Whisper)

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
    basal_insulin_time TEXT,
    insulin_carb_ratio REAL,
    correction_factor REAL,
    target_glucose INTEGER DEFAULT 120
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

Se voce ja tem as tabelas e precisa apenas adicionar as novas colunas:

```sql
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS insulin_carb_ratio REAL;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS correction_factor REAL;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS target_glucose INTEGER DEFAULT 120;
```

6. **Desabilite o RLS (Row Level Security) se necessario**
```sql
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE glycemic_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE food_reference DISABLE ROW LEVEL SECURITY;
```

7. **Popule a tabela de alimentos (TACO)**
```bash
python scripts/ingest_taco.py
```

8. **Inicie o bot**
```bash
python main.py
```

## Testes

```bash
pip install pytest
python -m pytest tests/ -v
```

Os testes cobrem (42 testes):
- **calculator_service**: bolus alimentar, dose de correcao, dose total, edge cases
- **user_repository**: calculo de IMC (metros, centimetros, valores invalidos)
- **chart_service**: geracao de graficos PNG, dados vazios, ponto unico
- **logs_repository**: insercao, auto-timestamp, filtragem de nulls, consulta
- **food_repository**: busca por nome, resultado vazio, tratamento de erros
- **voice_service**: transcricao de voz, resposta como string/objeto, erros

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
2. Use `/perfil` para cadastrar seus dados clinicos:
   - Dados pessoais (idade, peso, altura, HbA1c)
   - Insulina basal (dose e horario)
   - **ICR** (razao insulina/carboidrato)
   - **Fator de correcao**
   - **Glicemia alvo**
3. O bot calcula seu IMC e salva o perfil

### Uso diario (texto ou voz)
1. Envie `/registrar`
2. Informe sua glicemia atual (ex: "120" ou envie audio)
3. Descreva sua refeicao (ex: "arroz com feijao e bife" ou "nada")
4. O bot mostra o calculo detalhado:
   ```
   --- Calculo de Dose ---
   Bolus alimentar: 60g / 10 (ICR) = 6.0 U
   Correcao: (200 - 120) / 50 (FC) = 1.6 U
   DOSE TOTAL SUGERIDA: 7.6 U
   ```
5. Informe a insulina que aplicou de fato
6. Registro salvo com feedback sobre diferenca aplicada vs sugerida

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
| `GROQ_API_KEY` | Sim | Chave da API Groq (LLM + Whisper) |
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
