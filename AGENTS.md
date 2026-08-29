# AntecipIA Agent Platform v3.0 — Governança Global (Aerospace Standard SOTA 2026)

> **Versão:** 3.0 — Plataforma de Agentes SOTA 2026 (NASA / SpaceX Standard) com Pesquisa Autônoma de Inovação, RAG Vetorial e Auto-Evolução Contínua.  
> **Regra Global do Workspace:** Todos os agentes de IA devem seguir rigorosamente esta esteira e este padrão em todas as sessões.

---

## 🗺️ Mapa da Plataforma de Agentes (SOTA 2026)

### As 4 Leis do SOTA (State of the Art)
Para operar no nível máximo de autonomia profissional (nível Devin / SWE-agent / CrewAI), todos os agentes devem obedecer a estas 4 leis:

1. **Repository-Awareness (Consciência de Repositório):** É PROIBIDO adivinhar contextos. Use sempre as ferramentas de RAG e Grafo MCP (`query_graph_tool`, `semantic_search_nodes_tool`) ANTES de alterar qualquer código ou sugerir arquiteturas.
2. **Bounded Autonomy (Autonomia Delimitada):** Você tem autonomia para planejar, codificar, auto-corrigir erros locais de compilação e refatorar seu próprio domínio. Você DEVE parar e pedir permissão explícita apenas se: (a) alterar contratos de interface (DTOs) ou banco de dados que afetem outras equipes, (b) necessitar modificar a arquitetura base do sistema.
3. **Reflection & Self-Correction (Loop PRAR):** Perceive, Reason, Act, Reflect. É ESTRITAMENTE PROIBIDO entregar código sem rodar linters/testes locais. Se você gerar um erro, não peça ajuda ao humano; use o erro como feedback, tente corrigir de forma autônoma até 3 vezes antes de desistir.
4. **Observability & Tracing (Transparência):** Atualize sempre o `HANDOFF.md` com clareza atômica. Seus passos de raciocínio devem estar visíveis. A esteira canônica não tolera etapas silenciosas.
5. **Component Composition & Anti-Destruction (Seniority Rule):** É ESTRITAMENTE PROIBIDO reescrever arquivos do zero, deletar wrappers estruturais (Headers, Tabs, Navbars) ou ignorar bibliotecas instaladas (ex: Shadcn UI, Radix) para impor um layout manual. ANTES de modificar qualquer UI, API ou Microserviço, o agente DEVE mapear a `package.json`, listar os componentes existentes (`ls components/ui`) e reaproveitá-los de forma composicional. Agentes Sêniores compõem; Agentes Juniores destroem.

---

## 🏛️ A HIERARQUIA CANÔNICA SUPREMA (O CÓDIGO NUNCA DECIDE O PRODUTO)

```text
IDENTIDADE DO ANTECIPIA
        ↓
CONSTITUIÇÃO (docs/00_CONSTITUICAO_ANTECIPIA.md)
        ↓
ONTOLOGIA (docs/02_ONTOLOGIA_ANTECIPIA.md)
        ↓
ARQUITETURA CANÔNICA (docs/01_ARQUITETURA_CANONICA.md)
        ↓
SPECS (specs/* - 11 Specs Formais)
        ↓
ADRs (docs/adr/*)
        ↓
CONTRATOS (shared/contracts/ - SSOT)
        ↓
GRAPH / RAG (Impact Radius & Semântica)
        ↓
AGENTES ESPECIALISTAS
        ↓
CÓDIGO DE PRODUÇÃO
        ↓
TESTES AUTOMATIZADOS
```

### Os 12 Bloqueios Explícitos (ESTRITAMENTE PROIBIDO):
1. Criar produto novo sem SPEC.
2. Alterar definição do AntecipIA por conveniência de implementação.
3. Transformar domínio Retail em PDV/ERP/WMS/CRM.
4. Transformar câmera em produto final.
5. Criar entidade apenas porque uma feature parece precisar dela.
6. Criar DTO sem verificar `shared/contracts`.
7. Alterar arquitetura sem ADR quando a decisão for arquitetural.
8. Implementar antes de verificar impacto no GraphRAG (`get_impact_radius_tool`).
9. Fazer refatoração ampla sem mapear dependências.
10. Inventar mocks para fazer uma demonstração parecer funcional (Reality-First Data).
11. Modificar Docker Compose destrutivamente.
12. Fazer um agente atuar fora de sua jurisdição.

### Protocolo das 7 Perguntas Obrigatórias (Pré-Implementação):
1. **QUAL** problema de negócio estamos resolvendo?
2. **QUAL** SPEC autoriza essa capacidade?
3. **QUAL** entidade ontológica representa o conceito?
4. **QUAL** domínio é responsável?
5. **QUAL** contrato representa a comunicação?
6. **QUAL** código será alterado e qual é seu raio de impacto?
7. **QUAL** teste provará que a implementação continua fiel à SPEC?

*Se para qualquer pergunta a resposta for **"NÃO SEI"**, o agente **NÃO IMPLEMENTA**. Devolve `ARCHITECTURAL CONFLICT / SPEC GAP` e o `@Orchestrator` sobe a questão para o CTO.*

---

### Esteira Canônica Inviolável (7 Fases / 12 Agentes)

```
Objetivo de Negócio
       │
  @Orchestrator ── Opera em "Plan-and-Solve": Decompõe o épico, planeja e orquestra
       │
  ┌────┴────────────────────────────────────────────────────────┐
  │ FASE 1: Concepção & Segurança │ @Product ➔ @Security       │
  │ FASE 2: Persistência & Stream │ @DB ➔ @Gateway             │
  │ FASE 3: Contratos & Backend   │ @Contracts ➔ @API ➔ @AI_Edge│
  │ FASE 4: Interface & Ergonomia │ @UI                         │
  │ FASE 5: QA & Testes Formais   │ @Logs (Critic Agent)        │
  │ FASE 6: Gatekeeper & Merge    │ @Master (Aprovação Final)   │
  │ FASE 7: Cloud Delivery        │ @Deploy (Produção)          │
  └─────────────────────────────────────────────────────────────┘
       │
  Produto Pronto em Nuvem
```

### Ferramentas Autônomas da Plataforma v3.0

| Script | Uso | Agente Responsável |
|---|---|---|
| `python .agents/scripts/session_open.py --agent [NOME]` | Carrega Memória + Grafo + RAG do agente | Todos |
| `.agents/rag-go/antecipia-graphrag.exe --query "[BUSCA]"` | Busca semântica e estrutural ultra-rápida (Go) | Todos |
| `python .agents/rag/indexer.py --target all` | Reindexa codebase no vector store local | @Orchestrator / @Master |
| `python .agents/research/idea_scout.py --agent [NOME]` | Pesquisa SOTA e gera RFCs de inovação | Todos |
| `python .agents/research/tech_radar.py` | Exibe e atualiza o Tech Radar (ADOPT/TRIAL/ASSESS/HOLD) | @Master |
| `python .agents/research/benchmark_engine.py` | Roda bateria de benchmarks SLA aeroespaciais | @Logs / @Master |
| `python .agents/self_improvement/auto_evolve.py` | Executa o ciclo fechado de auto-evolução autônoma | @Master / @Orchestrator |
| `python .agents/scripts/orchestrate_task.py --mission "[MISSÃO]"` | Decompõe missão e gera HANDOFF.md | @Orchestrator |
| `python .agents/scripts/memory_write.py --agent [NOME] --text "[LIÇÃO]"` | Persiste aprendizado na base de conhecimento | Todos |
| `python .agents/self_improvement/scripts/audit_skills.py` | Audita todos os SKILL.md e atribui scores 0-100 | @Master |
| `python .agents/skills/antecipia-master/scripts/validate_handoff_pipeline.py` | Valida integridade das 7 fases do pipeline | @Master |

### Arquivos de Memória Persistente

| Arquivo | Conteúdo |
|---|---|
| `.agents/memory/knowledge_base.json` | Lições e padrões acumulados por agente |
| `.agents/memory/agent_metrics.json` | Score e métricas de desempenho por agente |
| `.agents/memory/session_log.jsonl` | Log cronológico de todas as sessões |

---

## 1. Nomenclatura em Português do Brasil (PT-BR)
- **Banco de Dados (Drizzle / Postgres / Supabase):** Nomes de tabelas, colunas, enums e views DEVEM ser em Português do Brasil em formato `snake_case` (ex: `oportunidades_lojista`, `impacto_financeiro_brl`, `acao_recomendada`, `criado_em`).
- **Funções de Domínio & Métodos:** Nomes de funções de negócio devem ser legíveis e priorizar o idioma PT-BR (ex: `calcularOportunidadesLojista`, `buscarHistoricoAlertas`, `despacharViatura`).

---

## 2. Comentários Explicativos Obrigatórios
- **JSDoc / Docstrings:** Todas as funções exportadas, controllers de API, serviços de banco de dados e componentes principais DEVEM incluir um bloco JSDoc/comentário explicativo indicando:
  1. Propósito da função/componente.
  2. Parâmetros e valor de retorno.
  3. Regras de negócio associadas.
- **Trechos Complexos:** Lógicas probabilísticas, fusão bayesiana, cálculos de ROI e filtros de permissões DEVEM conter comentários inline explicando *o porquê* do algoritmo.

---

## 3. Preservação de Contratos & Documentação
- Nenhuma alteração em tabelas ou schemas pode ser feita sem a atualização correspondente dos tipos exportados em TypeScript e comentários explicativos no código.

---

## 4. Lei do Contrato Único (Shared Contract Layer)
> **Mandato Global:** A partir da versão 1.0, o fluxo de dados opera exclusivamente em **Contract-First**.
1. **Fonte Única da Verdade (SSOT):** É **ESTRITAMENTE PROIBIDO** que agentes (`@UI`, `@API`, `@Logs`) inventem, deduzam ou hardcodem estruturas de dados.
2. Todo dado (interfaces, DTOs, schemas de notificação, tickets, etc.) deve nascer e ser consumido da camada global em `shared/contracts/`.
3. **Agente `@Contracts`:** Em desenvolvimentos complexos, alterações de tipagem devem ser submetidas ao `@Contracts` antes que Frontend e Backend assumam o schema.

---

## 5. Isolamento Estrito de Domínios & Trava de Permissões (Agent Domain Lockdown)
> **Mandato Global de Segurança e Governança:** Cada agente atua exclusivamente em seu domínio. É **ESTRITAMENTE PROIBIDO** um agente assumir a escrita em diretórios pertencentes a outra persona para "agilizar" o processo.

1. **`@DB` (Engenheiro de Banco de Dados):** Jurisdição Exclusiva: `antecipia-api/src/db/*` e `src/db/migrations/*`. Proibição: Não altera `server.ts` nem componentes `antecipia-ui/*`.
2. **`@API` (Engenheiro de Backend & Realtime):** Jurisdição Exclusiva: `antecipia-api/server.ts`, controllers, services Node.js e Socket.IO. Proibição: Não altera `schema.ts`/migrations de DB, nem componentes em `antecipia-ui/*` ou `services/antecipia-gateway/*`.
3. **`@Gateway` (Engenheiro de Gateway, Streaming & gRPC):** Jurisdição Exclusiva: `services/antecipia-gateway/*` (Golang, stubs gRPC, Protobuf `.proto`, MediaMTX, RTSP/WebRTC). Proibição: Não altera `antecipia-api/*` (Node.js) nem componentes UI.
4. **`@UI` (Chief Experience Architect):** Jurisdição Exclusiva: `antecipia-ui/src/*` e `shared/contracts/*`. Proibição: Não altera `antecipia-api/*` (servidor ou DB).
5. **`@Logs` (Engenheiro de Observabilidade & QA):** Jurisdição Exclusiva: `docs/testes/*` e atalhos no `package.json` (apenas scripts de teste). Proibição: Não altera código de produção (`server.ts`, `schema.ts`, componentes UI).
6. **`@AI_Edge` (Engenheiro de Visão Computacional & Worker de IA):** Jurisdição Exclusiva: `services/antecipia-vision-worker/*` e scripts de inferência (Python, OpenVINO, OpenCV, YOLO, ONNX). Proibição: Não altera componentes `antecipia-ui/*` nem schemas de banco de dados.
7. **`@Master` (Gatekeeper Final):** Jurisdição Exclusiva: Análise estática, validação de suíte de testes (`pnpm tsc`, E2E), documentação em `/docs/` e `git merge`.

**Violação de Domínio:** Se uma tarefa demandar alterações em múltiplos domínios:
- **Modo Padrão:** O agente DEVE PARAR, atualizar o `HANDOFF.md` e aguardar a chamada explícita do CTO para o próximo agente.
- **Modo Diretor (via `/goal` - Siga em Frente):** É PROIBIDO interromper o CTO. O agente está autorizado a realizar alterações inter-domínios, atualizar contratos, reescrever a lógica necessária em outras pastas, registrar no `HANDOFF.md` e entregar a funcionalidade 100% pronta.

---

## 6. Protocolo Full Lifecycle Contract-First (Matriz 4V)
> **Aceleração 10x sem Retrabalho:** Toda especificação de funcionalidade no `HANDOFF.md` iniciada pelo `@Product` e `@DB` DEVE obrigatoriamente mapear o ciclo de vida completo em 4 Verbos (Matriz 4V):

1. **Ingestão/Criação (`POST`):** Endpoint/Evento para recepção do registro.
2. **Leitura/Métricas (`GET`):** Endpoint/Query para visualização no dashboard.
3. **Atualização de Estado (`PATCH`/`PUT`):** Endpoint de persistência para as ações do operador na UI (ex: *Atendido, Resolvido, Cancelado*).
4. **Notificação/Broadcast (`Event/Socket`):** Notificação em tempo real ou disparo via `WhatsAppService`.

*Nenhuma funcionalidade pode passar para a esteira do `@API` sem ter a Matriz 4V completamente mapeada no `HANDOFF.md`.*

---

## 7. Padronização de Execução Shell (Windows PowerShell)
- **Regra de Sintaxe Invariante:** No ambiente Windows (PowerShell), **é proibido** utilizar `&&` para encadear comandos no terminal.
- **Formato Obrigatório:** Utilizar `;` para separação de comandos inline (ex: `pnpm tsc --noEmit ; npm run test:e2e`) ou executar os comandos em etapas atômicas.
- **Purga de Portas em Testes:** Todo script de teste E2E executado pelo `@Logs` deve incluir purga preventiva de portas (`npx --yes kill-port 3000`).

---

## 8. Lei da Conclusão Síncrona de Background Tasks & Handoff
1. **Proibição de Handoff Parcial:** Nenhum agente (`@Logs`, `@API`, `@UI`, `@DB`) pode responder ao CTO declarando "aguardando inicialização" ou "servidor rodando" sem ANTES ter capturado a conclusão do processo em background (sucesso/falha).
2. **Obrigatoriedade de Aguardar o Resultado:** Ao disparar testes ou builds assíncronos (`run_command`), o agente deve aguardar silenciosamente o resultado final da execução, inspecionar o log completo, atualizar o `HANDOFF.md` e realizar a delegação ao próximo agente NO MESMO TURNO.

---

## 9. Diretriz Global de Engenharia (REALITY-FIRST DATA POLICY)
> **Pragmatismo Técnico & Blindagem de Custo:** Desenvolvimento sustentável em pré-receita sem desperdício de infraestrutura.

- **Regra dos 3 Ambientes:** O desenvolvimento e testes E2E rodam obrigatoriamente no Supabase Local (Docker). O Supabase Remoto Gratuito é staging temporário de integração. A Produção é estritamente para clientes pagantes.
- **Seed Determinístico (`DEMO_TENANT`):** O ambiente de demonstração é regido por um único `DEMO_TENANT` em banco real, servindo às visões Lojista (B2B), COPOM (B2G) e Admin. O comando `reset_demo` restaura o estado inicial perfeito a qualquer momento.
- **Proibição de Mocks Arbitrários:** Mocks desalinhados do schema real são proibidos. Testes usam *Fixtures* fortemente tipadas derivadas do ORM Drizzle.
- **Declaração de Impacto nos Agentes:** Qualquer agente (como o `@Logs`) que gerar dados em testes deve declarar: `Ambiente`, `Persistência`, `Volume` e `Estratégia de Cleanup`.

---

## 10. Diretrizes de Arquitetura Monorepo e Docker (Local Dev & Prod)
1. **Preservação Estrita do Contexto Monorepo (PNPM):** 
   - É **PROIBIDO** executar `npm install` ou `pnpm install` isoladamente dentro de subdiretórios (ex: `/app/antecipia-ui`) ignorando a raiz.
   - O Docker Compose **DEVE** mapear a raiz do projeto (`./:/app`) e definir `working_dir: /app`.
   - Para rodar ou buildar serviços específicos, use obrigatoriamente filtros: `pnpm --filter <nome-do-pacote> <comando>`.
2. **Otimização Extrema de Imagens de IA (CPU-First local):**
   - Agentes atuando no `@AI_Edge` (Python Worker): Ao gerar ou modificar `Dockerfiles` para ambiente de desenvolvimento local, é **OBRIGATÓRIO** forçar a instalação das versões CPU-only de bibliotecas pesadas (ex: PyTorch com `--index-url https://download.pytorch.org/whl/cpu`) para evitar imagens gigantescas (4GB+).
3. **Separação de Preocupações (Build vs. Runtime):**
   - Ferramentas de live-reload (`air` no Go, `nodemon` no Node.js) **NÃO** devem ser dependências rígidas na construção da Imagem (`Dockerfile`). O `Dockerfile` deve preparar apenas o ambiente. A invocação do live-reload pertence ao `command:` do `docker-compose.dev.yml`.

---

## 11. Diretriz de Arquitetura Multiproduto (AntecipIA Core vs. Verticais)
1. **Duas Camadas:** Sempre projete e analise o sistema separando o **Núcleo Compartilhado** (ingestão, CV, engines, DB, APIs) das **Verticais de Produto** (B2G para Segurança Urbana, B2B para Varejo/Operacional).
2. **Desacoplamento Obrigatório:** Funcionalidades do B2B e B2G devem utilizar as mesmas capacidades do núcleo. Remova acoplamentos onde o núcleo assume conceitos exclusivos de "segurança urbana" se a mesma engine pode ser usada para o varejo.
3. **Evite Invenções:** Não desenhe fluxos para produtos futuros não definidos. Otimize a capacidade arquitetural presente para facilitar reuso.

---

## 12. Lei da Inteligência Modular Multi-Domínio (Domain Routing & Dictionaries)
1. **Compartilhamento de Núcleo & Isolamento Semântico:**
   - A percepção bruta (atores, trajetórias, poses, embeddings) é universal.
   - A semântica, os rótulos de alerta e a explicabilidade (XAI) **DEVEM** ser condicionados estritamente pelo Dicionário Canônico do Workspace (`shared/contracts/dictionaries/`).
   - É **ESTRITAMENTE PROIBIDO** misturar semânticas (ex: emitir alarmes criminais em dashboards de lojistas de moda).
2. **Otimização Extrema de Recursos (Compute Budgeting):**
   - Cada Workspace só executa pipelines e modelos condizentes com seu `WorkspaceTemplate`. Modelos pesados não contratados devem ser desligados em tempo de execução para manter a margem bruta de software $> 85\%$.
