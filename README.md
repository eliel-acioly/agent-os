# 🛰️ Agent-OS: Autonomous Software Engineering Operating System (SOTA 2026)

> **Architectural Standard:** NASA / SpaceX / Palantir Aerospace Engineering Standard  
> **Operational Paradigm:** Single Human CTO + 12 Autonomous Specialized AI Agents  
> **Core Pillars:** Spec-Driven Development (Spec Kit), GraphRAG, Graph-of-Thought (GoT), Multi-Hop Blast Radius & Graph Grounding  
> **Official Repository:** [https://github.com/eliel-acioly/agent-os](https://github.com/eliel-acioly/agent-os)

---

## 🗺️ Visão Geral Executiva

O **Agent-OS** é um meta-framework de engenharia de software autônoma projetado para permitir que um único desenvolvedor ou CTO conduza projetos de altíssima escala e complexidade (Web, Desktop, Cloud, Edge AI, Sistemas Embarcados) com a disciplina, previsibilidade e rigor de uma equipe de 50 engenheiros seniores.

Diferente de assistentes de chat soltos ou agentes com raciocínio linear que alucinam e corrompem o código, o Agent-OS impõe a **Hierarquia Canônica Suprema de 11 Elos**:

```text
IDENTIDADE DO PRODUTO (DNA Inviolável)
        ↓
CONSTITUIÇÃO SOBERANA (Regras Supremas de Negócio e Engenharia)
        ↓
ONTOLOGIA FORMAL (Catálogo Universal de Entidades e Relações)
        ↓
ARQUITETURA CANÔNICA (Decisões de Topologia e Isolamento)
        ↓
SPECS FORMAIS (Spec-Driven Kit / BDD Given-When-Then)
        ↓
ADRs (Architecture Decision Records com Poda Formal)
        ↓
CONTRATOS ÚNICOS (SSOT Tipado / shared/contracts/)
        ↓
GRAFO DE CONHECIMENTO & AST (Topologia, Blast Radius e Centralidade)
        ↓
AGENTES ESPECIALISTAS (12 Personas Delimitadas por Domínio)
        ↓
CÓDIGO DE PRODUÇÃO (Alterações Mínimas e Cirúrgicas)
        ↓
TESTES AUTOMATIZADOS (E2E, Chaos Injection & Reality Verification)
```

---

## 🔬 Benchmark: Como o Agent-OS se Compara aos Melhores Sistemas Mundiais

| Capacidade de Engenharia | MetaGPT / ChatDev | SWE-agent / OpenHands | Aider | **Agent-OS (Este Sistema)** |
|:---|:---:|:---:|:---:|:---:|
| **Paradigma de Trabalho** | SOPs rígidos para PoCs | Agente único em sandbox | Pareamento direto via Git | **12 Agentes Especialistas em Esteira de 7 Fases** |
| **Prevenção de Deriva** | Baixa (alucina no código) | Média (depende de testes) | Baixa (orientado ao prompt) | **Constituição Soberana + Spec Linter + Drift Detector** |
| **Governança de Tipagem** | Nenhuma | Nenhuma | Tipos locais | **Single Source of Truth (SSOT) em Contratos Compartilhados** |
| **Raciocínio Arquitetural** | Chain-of-Thought (Linear) | Reflexão em linha | Prompt estático | **Graph-of-Thought (GoT) com Bifurcação e Poda Formal** |
| **Análise de Impacto** | Cega | Apenas histórico Git | Repo Map com PageRank | **Multi-Hop Blast Radius (5 Saltos: AST → Contratos → Specs → Testes)** |
| **Gaiola Anti-Alucinação** | Nenhuma | Apenas erros de execução | Nenhuma | **Graph Grounding Verifier (Verificação Física no AST SQLite)** |
| **Resiliência e Caos** | Nenhuma | Nenhuma | Nenhuma | **Chaos Engineering & Fault Injection Suite (Padrão NASA)** |
| **Portabilidade** | Monolítico | App isolado | CLI pessoal | **Submódulo Git Universal plugável em qualquer repositório** |

---

## 🤖 Os 12 Agentes Especialistas e suas Jurisdições

O Agent-OS opera sob uma **Máquina de Estados Finita Inviolável (Pipeline de 7 Fases)**:

```text
  ┌─────────────────────────────────────────────────────────────┐
  │ FASE 1: Concepção & Segurança │ @Product ➔ @Security        │
  │ FASE 2: Persistência & Rede   │ @DB ➔ @Gateway              │
  │ FASE 3: Contratos & Backend   │ @Contracts ➔ @API ➔ @AI_Edge │
  │ FASE 4: Interface & Ergonomia │ @UI                         │
  │ FASE 5: QA & Chaos Testing    │ @Logs (Critic Agent)        │
  │ FASE 6: Gatekeeper & Merge    │ @Master (Aprovação Final)    │
  │ FASE 7: Cloud Delivery        │ @Deploy (Produção)          │
  └─────────────────────────────────────────────────────────────┘
```

1. **`@Orchestrator` (Maestro da Intenção):** Opera em modo *Plan-and-Solve*. Decompõe objetivos em tarefas atômicas, delega entre os agentes e protege a esteira contra atalhos.
2. **`@Product` (CPO com Mentalidade de Fundador):** Guardião do problema real do cliente. Escreve Specs com critérios de aceite BDD mensuráveis e impede a criação de funcionalidades inúteis.
3. **`@Contracts` (Guardião da Camada de Contratos - SSOT):** Impede que Frontend e Backend inventem dados. Todo DTO, enum e interface nasce em `shared/contracts/`.
4. **`@DB` (Engenheiro de Dados & Migrations):** Responsável exclusivo pelas tabelas, esquemas Drizzle/Prisma/SQL e migrações determinísticas com idempotência comprovada.
5. **`@API` (Engenheiro de Backend & Realtime):** Constrói controllers, serviços, streaming WebSockets, gRPC e rotas resilientes com circuit breakers.
6. **`@Gateway` (Engenheiro de Rede & Borda):** Microserviços de streaming (MediaMTX, WebRTC, RTSP), telemetria e pontes locais sem abertura de portas.
7. **`@AI_Edge` (Engenheiro de Visão & IA Local):** Pipelines de visão computacional, YOLO, OpenVINO, ONNX e VLLM operando dentro do teto de CPU local.
8. **`@UI` (Chief Experience & Design System):** Projeta jornadas ergonômicas, micro-interações, dashboards visuais e combate ativamente interfaces genéricas.
9. **`@Logs` (Engenheiro de QA, Caos & Observabilidade):** O agente crítico obrigatório. Nenhum código vai para produção sem testes E2E e injeção de falhas controladas.
10. **`@Security` (Guardião de Segurança & Compliance):** RBAC granular, isolamento multi-tenant estrito, proteção de rotas (Plan Guard) e prevenção contra OWASP Top 10.
11. **`@Monetization` (Head de SaaS & Unit Economics):** Modelagem de planos de assinatura, precificação por valor e métricas de receita (MRR, LTV, CAC).
12. **`@Master` (Gatekeeper Final & Arquiteto-Chefe):** O único autorizado a aprovar merges e releases. Valida tipagem, cobertura de testes e aderência arquitetural.

---

## ⚡ Motores de Engenharia Cognitiva (`scripts/`)

### 1. `spec_linter.py` (Spec-Driven Development Kit)
Audita se uma SPEC atende aos 6 Critérios Áureos de Especificação Formal:
- Metadados canônicos e código de rastreabilidade (`SPEC-XXX-001`).
- Problema de negócio delimitado com custo da dor e hipótese técnica.
- Contratos e DTOs explicitamente referenciados da camada SSOT.
- Critérios de Aceite no formato BDD (*Given-When-Then*).
- Modos de falha e degradação graciosa (*Graceful Degradation*).
- Rastreabilidade direta para o arquivo de teste E2E.
```bash
python .agents/scripts/spec_linter.py -f specs/core/SPEC-CORE-002.md
```

### 2. `graph_architectural_navigator.py` (Multi-Hop Blast Radius & Grounding)
- **Multi-Hop Blast Radius:** Navega em 5 saltos de dependência topológica antes de qualquer alteração (`AST Callers → Contratos → Specs → Testes E2E → Comunidades`).
- **Graph Grounding Verifier:** Verifica fisicamente se qualquer classe, função ou contrato citado pela IA existe no AST SQLite. Termos não comprovados são barrados como alucinações.
- **Particionamento de Comunidades Leiden:** Agrupa o monorepo em macro-constelações (C0 Core, C1 Domínios, C2 Borda, C3 Contratos).
```bash
python .agents/scripts/graph_architectural_navigator.py -c TenantsController --blast-radius
python .agents/scripts/graph_architectural_navigator.py --grounding-check MinhaClasse RiskBuilder
```

### 3. `graph_of_thought_engine.py` (Decisões Não-Lineares GoT)
Substitui o *Chain-of-Thought* cego. Cria um grafo transitório de hipóteses, roda filtros de SLA de latência ($<1000\text{ms}$), teto de CPU ($<85\%$) e conformidade constitucional, executando **poda formal** dos ramos inviáveis para convergir na solução ótima antes de escrever código.
```bash
python .agents/scripts/graph_of_thought_engine.py --demo
```

### 4. `repo_map_engine.py` (Centrality & Hub Ranking)
Inspirado nas melhores práticas do Aider e SWE-agent. Varre centenas de arquivos de código, analisa a topologia de dependências e calcula a centralidade dos componentes para identificar os **Hubs Centrais** de qualquer repositório.
```bash
python .agents/scripts/repo_map_engine.py -d . --top 10
```

### 5. `product_drift_detector.py` (Guardião Anti-Deriva de Escopo)
Audita todo o monorepo garantindo que nenhuma entidade transacional de outro domínio seja implementada clandestinamente sem SPEC correspondente.

### 6. `bootstrap_project.py` (Onboarding Instantâneo)
Instancia a plataforma de agentes, templates de constituição e diretórios canônicos em qualquer projeto em $< 5$ segundos.

---

## 🚀 Como Usar o Agent-OS em Qualquer Repositório

### Passo 1: Adicionar como Submódulo Git
Dentro da raiz do seu projeto alvo (seja ele em Node, React, Python, Go, Rust, Tauri ou Flutter):
```bash
git submodule add git@github.com:eliel-acioly/agent-os.git .agents
```

### Passo 2: Inicializar o Projeto Alvo
Execute o bootstrap para gerar a estrutura de governança canônica:
```bash
python .agents/scripts/bootstrap_project.py --target-dir . --name "NomeDoMeuApp" --domain "MEU_DOMINIO"
```
Isso criará:
- `docs/00_CONSTITUICAO.md` com a identidade fundamental do projeto.
- Pastas canônicas `docs/specs/`, `docs/adr/`, `docs/testes/`, `shared/contracts/`.
- `HANDOFF.md` inicializado com a esteira do `@Orchestrator`.

### Passo 3: Sincronização Contínua Entre Todos os seus Projetos
Toda vez que você melhorar um script, criar uma nova regra ou calibrar um agente no `agent-os`:
```bash
# Dentro de .agents/
git commit -m "feat(got): aprimora filtros de latência"
git push origin main

# Em qualquer outro projeto seu:
git submodule update --remote
```
**Todos os seus softwares passam a ser desenvolvidos com a versão mais avançada dos seus agentes.**

---

## 📄 Propriedade Intelectual & Padrão de Engenharia

Desenvolvido por **Eliel Acioly** — Framework Autônomo de Engenharia de Software SOTA 2026.
Construído com base no aprendizado acumulado em missões de missão crítica e refinado sob o rigor da engenharia aeroespacial.
