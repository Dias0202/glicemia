# Controle de Desenvolvimento - Glycemic Bot

## Arquitetura Definida
- **Padrao:** Layered Architecture (Handlers -> Services -> Repositories -> Database)
- **Linguagem:** Python 3.10+
- **Banco de Dados:** Supabase (PostgreSQL)
- **IA/NLP:** Groq API (llama-3.1-8b-instant)
- **Visualizacao:** Matplotlib
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

### [X] Fase 2: Desenvolvimento de Codigo (Back-end)
- [X] `core/config.py` - Carregamento e validacao de variaveis de ambiente
- [X] `database/supabase_client.py` - Cliente Supabase global
- [X] `repositories/logs_repository.py` - Insercao e consulta de logs glicemicos
- [X] `repositories/user_repository.py` - CRUD de perfil e calculo de IMC
- [X] `repositories/food_repository.py` - Busca de alimentos na tabela TACO
- [X] `services/nlp_service.py` - Extracao de dados via Groq API
- [X] `services/calculator_service.py` - Calculo de insulina bolus
- [X] `services/chart_service.py` - Geracao de graficos glicemicos (matplotlib)
- [X] `handlers/telegram_handlers.py` - State machines (onboarding + log diario + comandos)
- [X] `main.py` - Integracao de todos os handlers e health check

### [X] Fase 3: Comandos do Bot
- [X] `/start` - Mensagem de boas-vindas
- [X] `/perfil` - Onboarding de perfil clinico
- [X] `/registrar` - Registro diario (glicemia + refeicao NLP + insulina)
- [X] `/historico` - Ultimos 10 registros
- [X] `/grafico` - Grafico de tendencia dos ultimos 7 dias
- [X] `/buscar <alimento>` - Busca na tabela TACO
- [X] `/ajuda` - Ajuda detalhada
- [X] `/cancelar` - Cancelamento de operacao

### [X] Fase 4: Deploy e Validacao
- [X] Repositorio no GitHub configurado
- [X] Deploy no Render (Web Service)
- [X] Variaveis de ambiente configuradas no Render
- [X] Health check server na porta PORT (default: 10000)

### [X] Fase 5: Testes e Documentacao
- [X] Testes unitarios com pytest (27 testes)
- [X] Mocks para Supabase e Groq (testes rodam sem credenciais)
- [X] README.md completo
- [X] .env.example
- [X] PROJECT_TRACKER.md atualizado

## Log de Erros e Resolucoes
- **[2026-03-15] Erro Groq 400 (model_decommissioned):** Modelo `llama3-8b-8192` descontinuado.
  - *Resolucao:* Atualizado para `llama-3.1-8b-instant` em `services/nlp_service.py`.
- **[2026-03-27] Bug: telegram_user_id ausente nos logs:** Funcao `insert_glycemic_log` nao recebia `telegram_user_id`, quebrando vinculo usuario-log.
  - *Resolucao:* Adicionado parametro obrigatorio `telegram_user_id` em `repositories/logs_repository.py`.
- **[2026-03-27] Path hardcoded no ingest_taco.py:** Caminho absoluto Windows impedia execucao em outros ambientes.
  - *Resolucao:* Substituido por path relativo via `os.path` em `scripts/ingest_taco.py`.
