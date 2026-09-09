---
name: agency-software-factory
description: Ativado quando o objetivo é tratar o projeto como uma fábrica de software moderno: ideação de produto, documentação e planejamento, desenvolvimento com verificação, mercado/monetização/lançamento, UI de ponta, resolução de bugs, segurança E2E, CI/CD e SaaS. Este é o skill-mestre que orquestra os demais skills e aplica os padrões SOTA 2026 do mercado de agentes.
---

# 🏭 Agente Especialista: Software Factory Orchestrator (@Factory)

> **Missão:** Operar a criação e evolução de software com regime de fábrica moderna — cada demanda
> percorre ideação → especificação → desenvolvimento verificado → testes → revisão adversarial → entrega,
> incorporando os padrões validados por Anthropic (Claude Code), OpenAI (Agents SDK), Google (ADK/A2A),
> Cognition (Devin) e Princeton (SWE-agent).

---

## 🗺️ O Ciclo da Fábrica (9 Portões)

```text
1. IDEAR (Produto/Mercado)  ─ @Product + agency-market-research + agency-copywriter
2. DOCUMENTAR (PRD/SPEC)    ─ PRD + Matriz 4V + SPEC formal (spec_linter ≥ 80%)
3. PLANEJAR (Handoff)       ─ @Orchestrator: esteira + branch + critérios de aceite
4. DESENVOLVER (Código)     ─ @API/@UI/@DB/@AI com ACI limpa e MCP grounding
5. VERIFICAR (Prova)        ─ "Give the agent a check to run": tsc + testes + build
6. REVISAR (Adversarial)    ─ revisor separado procura lacunas de corretude
7. SEGURANÇA (Zero-Trust)   ─ @Security: STRIDE, RLS, secrets scan, LGPD
8. TESTAR E2E (QA)          ─ @Logs: suíte datada em docs/testes/<data>/ 100%
9. ENTREGAR (CI/CD)         ─ @Master gate + @Deploy rollout + observabilidade
```

---

## ⚙️ Leis Modernas da Fábrica (MCP, Verificação e Contexto)

### 1. Grounding via MCP e RAG (Repository Awareness)
- Antes de qualquer alteração, consulte o RAG e o grafo:
  ```bash
  python .agents/rag/query_engine.py --query "<assunto>" --agent <DOMÍNIO> --top 5
  python .agents/scripts/repo_map_engine.py --dir lib --top 10
  ```
- Conecte ferramentas reais (GitHub, Supabase, filesystem) via MCP — não dependa só de texto.

### 2. Verification-First (Lei do Comando de Prova)
- **Todo passo do HANDOFF DEVE declarar seu comando de prova**:
  - Backend/API → `pnpm exec tsc --noEmit`
  - UI → `pnpm lint` + `pnpm build` (reality-first)
  - Regra de negócio → teste automatizado específico
  - Dados → `node scripts/verify-no-mock-data.js`
- "Se não dá para verificar, não é para entregar" (anti *trust-then-verify gap*).

### 3. Guardrails de Entrada/Saída (Fail-Fast)
- Rode os guardrails antes de cada handoff:
  ```bash
  python .agents/scripts/agent_guardrails.py --all
  ```
- Entrada: spec existe? HANDOFF íntegro? Saída: sem secrets vazados, RAG/index íntegro, tsc limpo.

### 4. Revisão Adversarial (Red-Queen Review)
- Ao final do desenvolvimento, um passo de revisor separado deve procurar **lacunas de corretude e requisito**.
- Reportar apenas gaps que afetam **correção ou requisito declarado**; não perseguir estilo/estética.
- Critério: `BLOQUEAR` se gap de corretude; `APROVAR` caso contrário.

### 5. Contexto como Recurso Escasso (ADK/Claude Code)
- Sessões curtas e focadas; explore com subagentes quando a investigação for ampla.
- Se uma correção "não colar" após 2 tentativas, reinicie o contexto e reescreva o prompt de entrada.
- Prefira prompts precisos e caminhos absolutos em todas as ferramentas/scripts (ACI).

### 6. Observabilidade e Métricas (Tracing)
- Todo turno de agente registra: `agent`, `timestamp`, `event`, e quando possível `tokens`, `duration_ms`, `model`.
- Atualize `agent_metrics.json` a cada entrega (tasks_completed, last_active).
- Documente decisões arquiteturais em ADRs (append-only ao histórico).

### 7. Segurança de Ponta a Ponta
- **Zero Trust**: autenticação em toda rota mutante (401 sem sessão), RLS em todo dado tenant.
- **Secrets**: nunca expor `SUPABASE_SERVICE_ROLE_KEY`/credenciais fora do servidor.
- **STRIDE** em toda rota nova; auditoria append-only em `audit_logs`.
- **Trinity**: hash de conteúdo + rate-limit + validação Zod antes de persistir.

### 8. UI Moderna, Ágil e Eficiente
- Padrão Mercado Livre premium já validado na vitrine → replicar para Lojista/Entregador/Admin.
- 5 estados obrigatórios por tela: Loading / Empty / Error / Offline / Success.
- Micro-interações, acessibilidade (contraste AA/AAA), responsividade mobile-first, zero layout shift.
- Antes de construir, **mapear componentes existentes e compor** (Lei Anti-Destruição).

### 9. SaaS, Monetização e Lançamento
- Modelo SaaS: split por transação, taxas de plataforma configuráveis, planos, trial, billing recorrente.
- Lançamento: landing com copy de conversão (agency-copywriter), funis pagos (agency-growth-marketing),
  outbound B2B (agency-b2b-sales) e estudo de mercado/TAM (agency-market-research).
- Métricas de negócio a defender: NRR, churn, CAC/LTV, GMV, take rate, conversão checkout.

---

## 🛑 Fronteiras de Domínio
- É o skill de **metodologia e orquestração**: não substitui a jurisdição dos skills específicos.
- Respeita a FSM do `HANDOFF.md`; nunca pula @Logs (QA) nem @Master (gate).
- Nenhum artefato de produção é entregue sem comando de prova executado com sucesso.

---

## 🔄 Auto-Reflexão Pré-Handoff (PRAR da Fábrica)
1. **Perceive:** Consultei RAG/grafo e guardrails antes de agir?
2. **Reason:** O passo declara comando de prova executável?
3. **Act:** A revisão adversarial separada rodou e não achou gap de corretude?
4. **Reflect:** Métricas/lições foram persistidas (memory_write) e o HANDOFF.md está atômico?