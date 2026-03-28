# GlycemiBot - Sistema de Monitoramento e Predicao Glicemica

Bot de Telegram para monitoramento continuo de glicemia com calculo clinico de doses de insulina, busca de alimentos na tabela TACO, refeicoes salvas e interface por botoes.

## Funcionalidades

### Interface por Botoes
O bot usa botoes inline em todas as interacoes. Nao e necessario digitar comandos.

### Registro Glicemico Completo
1. Informe a glicemia
2. Adicione alimentos (busca na tabela TACO com 597 itens)
3. Informe a quantidade (gramas ou medidas caseiras)
4. Registre humor e exercicio
5. Veja o calculo detalhado da dose de insulina
6. Salve refeicoes favoritas para reutilizar

### Calculo Clinico de Insulina

```
Bolus Alimentar = Carboidratos (g) / ICR
Dose de Correcao = (Glicemia - Alvo) / FC (se acima do alvo)
Fator Exercicio: Leve -10%, Moderado -20%, Intenso -30%
Dose Total = (Bolus + Correcao) x Fator Exercicio
```

### Medidas Caseiras Aceitas
O bot converte automaticamente medidas do dia a dia em gramas:

| Medida | Equivale a |
|--------|-----------|
| colher de sopa (cs) | 25g |
| colher de cha (cc) | 5g |
| colher de sobremesa | 15g |
| xicara | 160g |
| concha | 100g |
| unidade | 80g |
| fatia | 30g |
| pedaco | 50g |
| copo | 240g |
| prato | 300g |

Exemplos: `200g`, `2 colheres de sopa`, `1 xicara`, `meia concha`

### Refeicoes Salvas
Apos registrar uma refeicao, voce pode salva-la como favorita. Na proxima vez, basta selecioná-la nos botoes sem precisar adicionar cada alimento novamente.

## Arquitetura

```
glycemic_bot/
├── main.py                          # Ponto de entrada
├── core/
│   └── config.py                    # Variaveis de ambiente
├── database/
│   └── supabase_client.py           # Cliente Supabase
├── handlers/
│   └── telegram_handlers.py         # Botoes inline + state machines
├── services/
│   ├── nlp_service.py               # Extracao de dados via Groq (LLama 3.1)
│   ├── calculator_service.py        # Calculo clinico (bolus + correcao + exercicio)
│   ├── chart_service.py             # Graficos (matplotlib)
│   └── portion_service.py           # Conversao de medidas caseiras
├── repositories/
│   ├── user_repository.py           # Perfil do usuario + IMC
│   ├── logs_repository.py           # Logs glicemicos
│   ├── food_repository.py           # Busca TACO
│   └── meal_repository.py           # Refeicoes salvas
├── scripts/
│   └── ingest_taco.py               # Ingestao da tabela TACO
├── taco/                            # Dados nutricionais (~600 alimentos)
└── tests/                           # 67 testes unitarios (pytest)
```

## Stack Tecnologica

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.10+ |
| Bot Framework | python-telegram-bot 20.8 |
| NLP/LLM | Groq API (llama-3.1-8b-instant) |
| Banco de Dados | Supabase (PostgreSQL) |
| Visualizacao | Matplotlib |
| Deploy | Render |

## Banco de Dados

### Tabela `user_profiles`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `telegram_user_id` | bigint (PK) | ID Telegram |
| `age` | integer | Idade |
| `weight` | float | Peso (kg) |
| `height` | float | Altura (m) |
| `bmi` | float | IMC calculado |
| `last_hba1c` | float | Hemoglobina glicada |
| `basal_insulin_dose` | float | Dose basal (UI) |
| `basal_insulin_time` | text | Horario da basal |
| `insulin_carb_ratio` | float | ICR (g carbo / 1U) |
| `correction_factor` | float | FC (mg/dL / 1U) |
| `target_glucose` | integer | Glicemia alvo (mg/dL) |

### Tabela `glycemic_logs`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `id` | serial (PK) | ID |
| `telegram_user_id` | bigint (FK) | Usuario |
| `timestamp` | timestamptz | Data/hora UTC |
| `glucose_level` | integer | Glicemia (mg/dL) |
| `carbs_ingested` | float | Carboidratos (g) |
| `bolus_insulin` | float | Insulina rapida (UI) |
| `exercise_done` | boolean | Se houve exercicio |
| `exercise_intensity` | text | Intensidade |
| `mood` | text | Humor |
| `refeicao` | text | Descricao da refeicao |

### Tabela `food_reference`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `id` | serial (PK) | ID |
| `food_name` | text | Nome (TACO) |
| `portion_size` | float | Porcao padrao (100g) |
| `unit` | text | Unidade (g) |
| `carbs_per_portion` | float | Carbs por 100g |

### Tabela `saved_meals`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `id` | serial (PK) | ID |
| `telegram_user_id` | bigint (FK) | Usuario |
| `meal_name` | text | Nome da refeicao |
| `items` | jsonb | Lista de alimentos com quantidades |
| `total_carbs` | float | Total de carboidratos |

## Instalacao

### Pre-requisitos

- Python 3.10+
- [Supabase](https://supabase.com/) (tier gratuito)
- Bot via [@BotFather](https://t.me/BotFather)
- [Groq API](https://console.groq.com/)

### Setup

```bash
git clone https://github.com/Dias0202/glicemia.git
cd glicemia
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env
# Edite .env com suas credenciais
```

### SQL (Supabase SQL Editor)

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

CREATE TABLE saved_meals (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES user_profiles(telegram_user_id),
    meal_name TEXT NOT NULL,
    items JSONB NOT NULL,
    total_carbs REAL NOT NULL
);

-- Desabilitar RLS
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE glycemic_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE food_reference DISABLE ROW LEVEL SECURITY;
ALTER TABLE saved_meals DISABLE ROW LEVEL SECURITY;
```

Se ja tem as tabelas anteriores, adicione apenas:
```sql
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS insulin_carb_ratio REAL;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS correction_factor REAL;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS target_glucose INTEGER DEFAULT 120;

CREATE TABLE IF NOT EXISTS saved_meals (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES user_profiles(telegram_user_id),
    meal_name TEXT NOT NULL,
    items JSONB NOT NULL,
    total_carbs REAL NOT NULL
);
ALTER TABLE saved_meals DISABLE ROW LEVEL SECURITY;
```

### Popular TACO e iniciar

```bash
python scripts/ingest_taco.py
python main.py
```

## Testes

```bash
python -m pytest tests/ -v
```

67 testes cobrindo: calculadora clinica (bolus + correcao + exercicio), porcoes (medidas caseiras), IMC, graficos, repositorios (logs, food, meals).

## Deploy (Render)

1. Conecte o repo GitHub ao Render
2. Build: `pip install -r requirements.txt`
3. Start: `python main.py`
4. Configure variaveis de ambiente

## Variaveis de Ambiente

| Variavel | Obrigatoria | Descricao |
|----------|-------------|-----------|
| `TELEGRAM_TOKEN` | Sim | Token do bot |
| `SUPABASE_URL` | Sim | URL Supabase |
| `SUPABASE_KEY` | Sim | Chave anon Supabase |
| `GROQ_API_KEY` | Sim | Chave Groq |
| `PORT` | Nao | Porta health check (default: 10000) |

## Licenca

Projeto academico / uso pessoal.
