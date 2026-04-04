# Controle de Desenvolvimento - GlycemiBot: Plataforma de Inteligencia Metabolica

## Arquitetura Definida
- **Padrao:** Layered Architecture (Handlers -> Services -> Repositories -> Database)
- **Linguagem:** Python 3.10+
- **Banco de Dados:** Supabase (PostgreSQL)
- **IA/NLP:** Groq API (llama-3.1-8b-instant)
- **Visao Computacional:** Groq Vision (llama-3.2-90b-vision-preview)
- **Voz/STT:** Groq Whisper (whisper-large-v3-turbo)
- **Predicao:** Motor de tendencias baseado em regressao linear (base para GluFormer/AttenGluco)
- **CGM:** FreeStyle Libre 2 Plus via LibreLinkUp API (pylibrelinkup)
- **Criptografia:** Fernet (AES-128-CBC) via cryptography
- **Visualizacao:** Matplotlib + NumPy
- **Infraestrutura:** Render (Web Service + health check)

## Status das Implementacoes

### [X] Fase 0: Planejamento e Design
- [X] Definicao do PDD (Product Design Document)
- [X] Definicao do SDD (System Design Document)
- [X] Modelagem do Banco de Dados (PostgreSQL). Separacao de insulina basal e bolus.
- [X] Definicao da Arquitetura de Software

### [X] Fase 1: Infraestrutura e Configuracao Base
- [X] Criacao do projeto no Supabase e execucao do DDL das tabelas
- [X] Criacao do bot via BotFather e obtencao do Token
- [X] Criacao da conta no Groq e obtencao da API Key
- [X] Configuracao do ambiente local (Virtualenv, dependencias e .env)
- [X] Ingestao da Tabela TACO (script `scripts/ingest_taco.py`)

### [X] Fase 2: Desenvolvimento de Codigo (Back-end Core)
- [X] `core/config.py` - Carregamento e validacao de variaveis de ambiente (incluindo CGM)
- [X] `core/security.py` - Criptografia AES (Fernet) para credenciais do LibreLinkUp
- [X] `database/supabase_client.py` - Cliente Supabase global
- [X] `repositories/logs_repository.py` - Logs glicemicos expandidos (CGM source, tendencia, predicao)
- [X] `repositories/user_repository.py` - CRUD de perfil, IMC, parametros clinicos
- [X] `repositories/food_repository.py` - Busca de alimentos na tabela TACO
- [X] `repositories/meal_repository.py` - CRUD de refeicoes salvas (JSONB)
- [X] `repositories/sensor_repository.py` - CRUD de integracoes de sensor CGM
- [X] `services/nlp_service.py` - Extracao de dados via Groq API
- [X] `services/calculator_service.py` - Calculo clinico: bolus + correcao + fator exercicio
- [X] `services/chart_service.py` - Geracao de graficos glicemicos (matplotlib)
- [X] `services/voice_service.py` - Transcricao de voz via Groq Whisper API
- [X] `services/vision_service.py` - Identificacao de alimentos por foto (Groq Vision)
- [X] `services/libre_service.py` - Integracao com LibreLinkUp API (FreeStyle Libre)
- [X] `services/alert_service.py` - Alertas proativos empaticos e score metabolico
- [X] `services/portion_service.py` - Conversao de medidas caseiras brasileiras
- [X] `ml_engine/prediction_service.py` - Predicao de tendencia glicemica + score metabolico + gemeo digital
- [X] `tasks/cgm_worker.py` - Worker assincrono de sincronizacao CGM
- [X] `handlers/telegram_handlers.py` - State machines com texto, voz, foto e CGM
- [X] `main.py` - Integracao completa com CGM worker e health check

### [X] Fase 3: Interface e Funcionalidades do Bot
- [X] `/start` - Menu principal com botoes inline e status de glicemia
- [X] `/perfil` - Onboarding clinico (ICR, fator de correcao, glicemia alvo) com voz
- [X] `/registrar` - Registro completo: glicemia -> alimentos (texto/foto/voz/salvos) -> humor -> exercicio -> dose
- [X] `/sensor` - Conexao do FreeStyle Libre 2 Plus via LibreLinkUp
- [X] `/simular` - Gemeo Digital: simula impacto de refeicao antes de comer
- [X] Historico - Ultimos 10 registros com icones de fonte (CGM/manual)
- [X] Grafico - Tendencia dos ultimos 7 dias
- [X] Score Metabolico - Pontuacao 0-100 (tempo no alvo, variabilidade, seguranca)
- [X] `/buscar <alimento>` - Busca na tabela TACO
- [X] `/ajuda` - Ajuda completa com todos os recursos
- [X] `/cancelar` - Cancelamento de operacao

### [X] Fase 4: Deploy e Validacao
- [X] Repositorio no GitHub configurado
- [X] Deploy no Render (Web Service)
- [X] Variaveis de ambiente configuradas no Render
- [X] Health check server na porta PORT (default: 10000)

### [X] Fase 5: Calculo Clinico de Insulina
- [X] Perfil do usuario armazena ICR, fator de correcao e glicemia alvo
- [X] Bolus alimentar: carboidratos / ICR
- [X] Dose de correcao: (glicemia - alvo) / fator de correcao
- [X] Dose total = (bolus + correcao) x fator exercicio
- [X] Exercicio: Leve -10%, Moderado -20%, Intenso -30%
- [X] Alertas de hipoglicemia (<70) e hiperglicemia severa (>250)
- [X] Feedback de diferenca entre dose sugerida e aplicada

### [X] Fase 6: Entrada Multimodal
- [X] Transcricao de audio via Groq Whisper (whisper-large-v3-turbo, pt-BR)
- [X] Suporte a voz em todas as etapas do onboarding e registro
- [X] Identificacao de alimentos por foto via Groq Vision (llama-3.2-90b-vision-preview)
- [X] Estimativa automatica de porcoes e carboidratos de foto
- [X] Cruzamento de alimentos identificados com tabela TACO

### [X] Fase 7: Integracao CGM (FreeStyle Libre 2 Plus)
- [X] Cadastro de credenciais LibreLinkUp com criptografia AES
- [X] Validacao de credenciais com roteamento geo (BR/US/EU/AU)
- [X] Sincronizacao automatica via worker assincrono (intervalo configuravel)
- [X] Jitter e backoff para evitar rate limiting (HTTP 429)
- [X] Leitura de glicemia atual com seta de tendencia
- [X] Historico de 12 horas do sensor
- [X] Armazenamento automatico no banco com source_type='LIBRELINKUP_CLOUD'
- [X] Alertas proativos via Telegram push

### [X] Fase 8: Inteligencia Metabolica
- [X] Motor de predicao: regressao linear sobre serie temporal de CGM
- [X] Predicao de glicemia a 60 minutos (predicted_glucose_60m)
- [X] Classificacao de tendencia (FALLING_FAST/FALLING/STABLE/RISING/RISING_FAST)
- [X] Calculo de taxa de variacao (mg/dL por minuto)
- [X] Tempo estimado ate atingir hipoglicemia ou hiperglicemia
- [X] R-squared como metrica de confianca da predicao
- [X] Score Metabolico 0-100 (TIR 50% + CV 25% + Seguranca 25%)
- [X] Mensagens empaticas orientadas a acao (paradigma de interceptacao de momentum)
- [X] Gemeo Digital: simulacao de curva glicemica de 4 horas pos-refeicao
- [X] Farmacocinetica simplificada de insulina rapida e absorcao de carboidratos

### [X] Fase 9: UX Modernizada
- [X] Botoes inline em todas as interacoes (zero comandos digitados)
- [X] Emojis contextuais nas mensagens
- [X] Status de glicemia no menu principal (se sensor conectado)
- [X] Medidas caseiras brasileiras (colher de sopa, xicara, concha, etc.)
- [X] Refeicoes salvas como favoritas para reusar
- [X] Registro de humor (Bem/Normal/Estressado/Ansioso/Triste)
- [X] Barra visual de score metabolico
- [X] Alertas proativos empaticos (nao punitivos)

### [X] Fase 10: Testes e Documentacao
- [X] 127 testes unitarios com pytest
- [X] Cobertura: calculator, portion, prediction, security, sensor, libre, alert, chart, food, logs, meal, user
- [X] Mocks completos (Supabase, Groq, Whisper, pylibrelinkup) - testes rodam sem credenciais
- [X] README.md completo com DDL expandido e arquitetura atualizada
- [X] .env.example com todas as variaveis
- [X] PROJECT_TRACKER.md atualizado

## Estrutura de Diretorios
```
glycemic_bot/
├── core/
│   ├── config.py          # Configuracao e variaveis de ambiente
│   └── security.py        # Criptografia AES para credenciais
├── database/
│   └── supabase_client.py # Pool de conexoes Supabase
├── ml_engine/
│   └── prediction_service.py  # Predicao, score metabolico, gemeo digital
├── repositories/
│   ├── food_repository.py     # TACO food search
│   ├── logs_repository.py     # Logs glicemicos (manual + CGM)
│   ├── meal_repository.py     # Refeicoes salvas
│   ├── sensor_repository.py   # Integracoes de sensor CGM
│   └── user_repository.py     # Perfis de usuario
├── services/
│   ├── alert_service.py       # Alertas empaticos e score
│   ├── calculator_service.py  # Calculo clinico de insulina
│   ├── chart_service.py       # Graficos glicemicos
│   ├── libre_service.py       # LibreLinkUp API wrapper
│   ├── nlp_service.py         # Groq LLM para NLP
│   ├── portion_service.py     # Medidas caseiras brasileiras
│   ├── vision_service.py      # Identificacao de alimentos por foto
│   └── voice_service.py       # Groq Whisper transcricao
├── tasks/
│   └── cgm_worker.py          # Worker assincrono de CGM
├── handlers/
│   └── telegram_handlers.py   # Todos os fluxos de conversacao
├── tests/                     # 127 testes unitarios
├── scripts/
│   └── ingest_taco.py         # Ingestao da tabela TACO
├── taco/                      # Dados da tabela TACO
├── main.py                    # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Log de Erros e Resolucoes
- **[2026-03-15] Erro Groq 400 (model_decommissioned):** Modelo `llama3-8b-8192` descontinuado.
  - *Resolucao:* Atualizado para `llama-3.1-8b-instant` em `services/nlp_service.py`.
- **[2026-03-27] Bug: telegram_user_id ausente nos logs:** Funcao `insert_glycemic_log` nao recebia `telegram_user_id`.
  - *Resolucao:* Adicionado parametro obrigatorio `telegram_user_id` em `repositories/logs_repository.py`.
- **[2026-03-27] Path hardcoded no ingest_taco.py:** Caminho absoluto Windows.
  - *Resolucao:* Substituido por path relativo via `os.path`.
- **[2026-03-27] RLS bloqueando operacoes:** Supabase Row Level Security bloqueava inserts.
  - *Resolucao:* Desabilitar RLS ou criar policies permissivas.
- **[2026-03-28] Refatoracao clinica:** CARB_FACTOR global substituido por ICR/FC/alvo por usuario.
  - *Resolucao:* Novos campos em user_profiles, calculator_service reescrito com formula clinica.
- **[2026-04-04] Evolucao para Plataforma Metabolica:** Paradigma reativo -> preditivo.
  - *Resolucao:* CGM via LibreLinkUp, predicao de tendencia, gemeo digital, visao computacional, alertas empaticos.
