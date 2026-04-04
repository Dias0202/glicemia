# GlycemiBot - Plataforma de Inteligencia Metabolica

Bot de Telegram que evolui de um simples diario glicemico para uma **plataforma de inteligencia metabolica** com monitoramento continuo via CGM (FreeStyle Libre 2 Plus), predicao de tendencias, gemeo digital, identificacao de alimentos por foto, entrada por voz e alertas proativos empaticos.

## Funcionalidades

### Interface por Botoes
O bot usa botoes inline em todas as interacoes. Nao e necessario digitar comandos.

### Registro Glicemico Completo
1. Informe a glicemia (texto ou voz)
2. Adicione alimentos (busca TACO, foto do prato ou refeicao salva)
3. Informe a quantidade (gramas ou medidas caseiras)
4. Registre humor e exercicio
5. Veja o calculo detalhado da dose de insulina
6. Salve refeicoes favoritas para reutilizar

### Monitoramento Continuo de Glicose (CGM)
- Integracao com FreeStyle Libre 2 Plus via LibreLinkUp
- Sincronizacao automatica com roteamento geografico (BR/US/EU/AU)
- Credenciais criptografadas com AES (Fernet)
- Worker assincrono com jitter para evitar rate limiting
- Alertas proativos via Telegram push

### Predicao de Tendencias
- Regressao linear sobre serie temporal de CGM
- Predicao de glicemia a 60 minutos
- Classificacao de tendencia (FALLING_FAST → STABLE → RISING_FAST)
- Tempo estimado ate hipoglicemia/hiperglicemia
- Confianca da predicao via R-squared

### Score Metabolico (0-100)
- **Tempo no alvo** (70-180 mg/dL): peso 50%
- **Variabilidade glicemica** (CV): peso 25%
- **Seguranca** (ausencia de hipo/hiper): peso 25%
- Mensagens empaticas orientadas a acao

### Gemeo Digital (Simulacao)
- Simule o impacto de uma refeicao ANTES de comer
- Projecao de curva glicemica de 4 horas
- Farmacocinetica simplificada de insulina rapida + absorcao de carboidratos
- Sugere acoes (caminhada, exercicio) para achatar picos

### Identificacao de Alimentos por Foto
- Envie foto do prato durante o registro
- IA identifica alimentos e estima porcoes (Groq Vision)
- Cruzamento automatico com tabela TACO

### Entrada por Voz
- Envie audio em qualquer etapa do registro ou onboarding
- Transcricao via Groq Whisper (pt-BR)

### Calculo Clinico de Insulina

```
Bolus Alimentar = Carboidratos (g) / ICR
Dose de Correcao = (Glicemia - Alvo) / FC (se acima do alvo)
Fator Exercicio: Leve -10%, Moderado -20%, Intenso -30%
Dose Total = (Bolus + Correcao) x Fator Exercicio
```

### Alertas Proativos Empaticos
Em vez de "Glicemia alta - Cuidado", o bot usa **interceptacao de momentum**:
> "Predicao indica elevacao para ~210 mg/dL. Uma caminhada de 10-15 minutos agora pode achatar o pico em ate 30%."

### Medidas Caseiras Aceitas

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

## Arquitetura

```
glycemic_bot/
├── main.py                          # Ponto de entrada + CGM worker
├── core/
│   ├── config.py                    # Variaveis de ambiente
│   └── security.py                  # Criptografia AES (Fernet)
├── database/
│   └── supabase_client.py           # Cliente Supabase
├── handlers/
│   └── telegram_handlers.py         # Botoes inline + state machines (28 estados)
├── ml_engine/
│   └── prediction_service.py        # Predicao + score metabolico + gemeo digital
├── services/
│   ├── nlp_service.py               # Extracao de dados via Groq (LLama 3.1)
│   ├── calculator_service.py        # Calculo clinico (bolus + correcao + exercicio)
│   ├── chart_service.py             # Graficos (matplotlib)
│   ├── portion_service.py           # Conversao de medidas caseiras
│   ├── voice_service.py             # Groq Whisper (transcricao pt-BR)
│   ├── vision_service.py            # Groq Vision (identificacao de alimentos)
│   ├── libre_service.py             # LibreLinkUp API (FreeStyle Libre CGM)
│   └── alert_service.py             # Alertas proativos empaticos + score
├── repositories/
│   ├── user_repository.py           # Perfil do usuario + IMC
│   ├── logs_repository.py           # Logs glicemicos (manual + CGM)
│   ├── food_repository.py           # Busca TACO
│   ├── meal_repository.py           # Refeicoes salvas
│   └── sensor_repository.py         # Integracoes CGM
├── tasks/
│   └── cgm_worker.py                # Worker assincrono de sincronizacao
├── scripts/
│   └── ingest_taco.py               # Ingestao da tabela TACO
├── taco/                            # Dados nutricionais (~600 alimentos)
└── tests/                           # 127 testes unitarios (pytest)
```

## Stack Tecnologica

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.10+ |
| Bot Framework | python-telegram-bot 20.8 |
| NLP/LLM | Groq API (llama-3.1-8b-instant) |
| Visao | Groq Vision (llama-3.2-90b-vision-preview) |
| Voz/STT | Groq Whisper (whisper-large-v3-turbo) |
| CGM | pylibrelinkup (FreeStyle Libre 2 Plus) |
| Predicao | NumPy (regressao linear, base para GluFormer/AttenGluco) |
| Criptografia | cryptography (Fernet AES-128-CBC) |
| Banco de Dados | Supabase (PostgreSQL) |
| Visualizacao | Matplotlib |
| Deploy | Render |

## Banco de Dados

### DDL Completo (Supabase SQL Editor)

```sql
-- Perfis de usuario com parametros clinicos
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

-- Logs glicemicos expandidos (manual + CGM + predicao)
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
    refeicao TEXT,
    source_type VARCHAR(50) DEFAULT 'MANUAL',
    trend_arrow VARCHAR(10),
    predicted_glucose_60m INTEGER,
    ai_recommendation TEXT,
    heart_rate_bpm INTEGER,
    is_synthetic BOOLEAN DEFAULT FALSE
);

-- Tabela TACO de alimentos
CREATE TABLE food_reference (
    id SERIAL PRIMARY KEY,
    food_name TEXT NOT NULL,
    portion_size REAL DEFAULT 100.0,
    unit TEXT DEFAULT 'g',
    carbs_per_portion REAL
);

-- Refeicoes salvas pelo usuario
CREATE TABLE saved_meals (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES user_profiles(telegram_user_id),
    meal_name TEXT NOT NULL,
    items JSONB NOT NULL,
    total_carbs REAL NOT NULL
);

-- Integracoes de sensor CGM (credenciais criptografadas)
CREATE TABLE sensor_integrations (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES user_profiles(telegram_user_id) ON DELETE CASCADE,
    llu_email VARCHAR(255) NOT NULL,
    llu_password_hash VARCHAR(512) NOT NULL,
    llu_region_code VARCHAR(10) DEFAULT 'BR',
    llu_patient_uuid VARCHAR(100),
    llu_token_jwt TEXT,
    last_sync_timestamp TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    UNIQUE(telegram_user_id)
);

-- Desabilitar RLS (ou criar policies adequadas)
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE glycemic_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE food_reference DISABLE ROW LEVEL SECURITY;
ALTER TABLE saved_meals DISABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_integrations DISABLE ROW LEVEL SECURITY;
```

### Migracao (se ja tem as tabelas anteriores)

```sql
-- Novas colunas em glycemic_logs
ALTER TABLE glycemic_logs ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) DEFAULT 'MANUAL';
ALTER TABLE glycemic_logs ADD COLUMN IF NOT EXISTS trend_arrow VARCHAR(10);
ALTER TABLE glycemic_logs ADD COLUMN IF NOT EXISTS predicted_glucose_60m INTEGER;
ALTER TABLE glycemic_logs ADD COLUMN IF NOT EXISTS ai_recommendation TEXT;
ALTER TABLE glycemic_logs ADD COLUMN IF NOT EXISTS heart_rate_bpm INTEGER;
ALTER TABLE glycemic_logs ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN DEFAULT FALSE;

-- Nova tabela de integracoes CGM
CREATE TABLE IF NOT EXISTS sensor_integrations (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES user_profiles(telegram_user_id) ON DELETE CASCADE,
    llu_email VARCHAR(255) NOT NULL,
    llu_password_hash VARCHAR(512) NOT NULL,
    llu_region_code VARCHAR(10) DEFAULT 'BR',
    llu_patient_uuid VARCHAR(100),
    llu_token_jwt TEXT,
    last_sync_timestamp TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    UNIQUE(telegram_user_id)
);
ALTER TABLE sensor_integrations DISABLE ROW LEVEL SECURITY;

-- saved_meals (se nao existir)
CREATE TABLE IF NOT EXISTS saved_meals (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES user_profiles(telegram_user_id),
    meal_name TEXT NOT NULL,
    items JSONB NOT NULL,
    total_carbs REAL NOT NULL
);
ALTER TABLE saved_meals DISABLE ROW LEVEL SECURITY;
```

## Instalacao

### Pre-requisitos

- Python 3.10+
- [Supabase](https://supabase.com/) (tier gratuito)
- Bot via [@BotFather](https://t.me/BotFather)
- [Groq API](https://console.groq.com/)
- FreeStyle Libre 2 Plus + LibreLinkUp (opcional, para CGM)

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

### Popular TACO e iniciar

```bash
python scripts/ingest_taco.py
python main.py
```

## Testes

```bash
python -m pytest tests/ -v
```

127 testes cobrindo: predicao (tendencia + score + gemeo digital), seguranca (criptografia), sensor CGM, alertas empaticos, calculadora clinica, porcoes, IMC, graficos e repositorios.

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
| `GROQ_API_KEY` | Sim | Chave Groq (NLP + Whisper + Vision) |
| `CGM_ENABLED` | Nao | Ativar sync CGM (default: false) |
| `CGM_SYNC_INTERVAL_MINUTES` | Nao | Intervalo de sync (default: 5) |
| `PORT` | Nao | Porta health check (default: 10000) |

## Roadmap (Evolucao Futura)

Conforme documentado no PDD de Plataforma Metabolica:
- [ ] Modelo GluFormer (Foundation Model para predicao fisiologica)
- [ ] Modelo AttenGluco (atencao cruzada multiescalar para wearables)
- [ ] Integracao BLE direta (bypass nuvem Abbott)
- [ ] Sensores CGM White-Label asiaticos
- [ ] App mobile nativo (FastAPI backend)
- [ ] Gamificacao avancada (streaks, conquistas)
- [ ] Integracao Apple Health / Google Fit

## Licenca

Projeto academico / uso pessoal.
