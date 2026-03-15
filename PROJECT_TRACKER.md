# Controle de Desenvolvimento - Glycemic Bot

## Arquitetura Definida
- **Padrão:** Layered Architecture (Controllers/Handlers, Services, Repositories).
- **Linguagem:** Python 3.10+
- **Banco de Dados:** Supabase (PostgreSQL).
- **IA/NLP:** Groq API (Processamento de linguagem natural para JSON).
- **Infraestrutura:** Render.

## Status das Implementações

### [X] Fase 0: Planejamento e Design
- [X] Definição do PDD (Product Design Document).
- [X] Definição do SDD (System Design Document).
- [X] Modelagem do Banco de Dados (PostgreSQL).
- [X] Definição da Arquitetura de Software.

### [ ] Fase 1: Infraestrutura e Configuração Base
- [X] Criação do projeto no Supabase e execução do DDL das tabelas.
- [X] Criação do bot via BotFather e obtenção do Token.
- [X] Criação da conta no Groq e obtenção da API Key.
- [ ] Configuração do ambiente local (Virtualenv, dependências iniciais).

### [ ] Fase 2: Desenvolvimento de Código (Back-end)
- [ ] Implementar `core/config.py` para gestão de variáveis de ambiente.
- [ ] Implementar `database/supabase_client.py`.
- [ ] Implementar `repositories/logs_repository.py` (Inserção de registros).
- [ ] Implementar `services/nlp_service.py` (Comunicação com Groq e extração de JSON).
- [ ] Implementar `services/calculator_service.py` (Cálculo da dose de insulina).
- [ ] Implementar `handlers/telegram_handlers.py` (Recepção de mensagens).
- [ ] Integrar fluxo completo em `main.py`.

### [ ] Fase 3: Deploy e Validação
- [ ] Configurar repositório no GitHub.
- [ ] Configurar deploy no Render (Background Worker ou Web Service).
- [ ] Inserir variáveis de ambiente no Render.
- [ ] Realizar testes de ponta a ponta pelo Telegram.

## Log de Erros e Impedimentos
*(Nenhum erro registrado até o momento. Utilize esta seção para documentar exceções, falhas de API ou bugs lógicos encontrados durante o desenvolvimento).*