# Agent-OS: Sistema Operacional Modular para Engenharia de Software Orientada a Agentes

> **Definição Técnica:** Framework de orquestração multiagente, governança de contratos de dados (SSOT) e automação do ciclo de vida de desenvolvimento de software (SDLC).  
> **Repositório Oficial:** [https://github.com/eliel-acioly/agent-os](https://github.com/eliel-acioly/agent-os)  
> **Padrão de Governança:** Spec-Driven Development, Tipagem Estrita, Análise Topológica de AST e Falsificabilidade Empírica.

---

## 1. Problema de Engenharia

Modelos de linguagem aplicados à engenharia de software frequentemente falham em bases de código de média e alta complexidade devido a quatro fatores estruturais:

1. **Deriva de Escopo (Product Drift):** Agentes introduzem componentes, tabelas e funcionalidades não autorizados pelas especificações formais.
2. **Fragmentação de Contratos:** Frontend, Backend e Banco de Dados utilizam modelos de dados dessincronizados, gerando falhas em tempo de execução.
3. **Explosão de Contexto e Alucinação:** LLMs sem mapeamento estrutural de dependências tentam inferir o comportamento de todo o repositório, inventando métodos e tipos inexistentes.
4. **Vieses Cognitivos em Auto-Avaliação:** Agentes tendem a avaliar o próprio código como correto mesmo sob condições de concorrência (*race conditions*), vazamentos de recursos ou quebras de contrato.

O **Agent-OS** resolve esses problemas restringindo a autonomia dos agentes a uma **Máquina de Estados Finita (FSM)** e a uma **Hierarquia de Governança Estrita**.

---

## 2. A Hierarquia Canônica de Governança (11 Elos)

O código nunca define os requisitos. Toda linha de código de produção deve possuir rastreabilidade descendente completa:

```text
1. IDENTIDADE DO SISTEMA       -> Limites e escopo do software
2. CONSTITUIÇÃO FORMAL         -> Invariantes e regras invioláveis de engenharia
3. ONTOLOGIA                   -> Catálogo canônico de entidades e relações de domínio
4. ARQUITETURA DE REFERÊNCIA   -> Topologia de serviços, protocolos e isolamento
5. ESPECIFICAÇÃO FORMAL (SPEC) -> Casos de uso e critérios de aceite BDD (Given-When-Then)
6. DECISÕES DE ARQUITETURA(ADR)-> Registro formal de trade-offs técnicos
7. CONTRATOS ÚNICOS (SSOT)     -> DTOs e interfaces tipadas (shared/contracts/)
8. GRAFO DE DEPENDÊNCIAS (AST) -> Análise estática de callers, blast radius e centralidade
9. AGENTES ESPECIALIZADOS      -> Execução restrita a domínios herméticos
10. CÓDIGO DE PRODUÇÃO         -> Alterações mínimas necessárias
11. TESTES AUTOMATIZADOS       -> Testes E2E, invariantes e testes de estresse
```

---

## 3. Matriz de Agentes Especializados e Jurisdições

O sistema opera com 18 personas agrupadas em 6 departamentos funcionais. Cada agente possui jurisdição técnica exclusiva, sendo proibida a escrita em diretórios fora de seu domínio.

| Departamento | Agente | Jurisdição Técnica / Responsabilidade | Artefatos Produzidos |
|:---|:---|:---|:---|
| **Estratégia & Produto** | `@Orchestrator` | Decomposição de tarefas em grafo direcionado e coordenação da esteira. | `HANDOFF.md`, Planos Táticos |
| | `@Product` | Definição de requisitos e especificações funcionais baseadas em dor de negócio. | `docs/specs/SPEC-*.md` |
| | `@MarketResearch`| Análise quantitativa de concorrência, dimensionamento de mercado e custos. | `docs/01_ESTUDO_DE_MERCADO.md` |
| **Design & Usabilidade** | `@UI` | Interface de usuário, sistemas de design, contraste e ergonomia visual. | Componentes visuais, CSS/Tailwind |
| | `@UX` | Arquitetura de informação, redução de etapas operacionais e carga cognitiva. | Fluxogramas, auditorias de UX |
| **Engenharia de Sistemas** | `@Contracts` | Guardião do SSOT. Manutenção e congelamento de DTOs e interfaces públicas. | `shared/contracts/*.ts` |
| | `@API` | Camada de serviços, controladores HTTP/REST, streaming gRPC e WebSockets. | Controladores, rotas de backend |
| | `@DB` | Modelagem relacional, esquemas de dados e migrações determinísticas. | `src/db/schema.ts`, migrations SQL |
| | `@AI_Edge` | Pipelines locais de visão computacional e modelos de inferência sob teto de CPU. | Workers de IA, scripts de inferência |
| | `@Gateway` | Ingestão de telemetria, streaming de vídeo (MediaMTX) e pontes locais. | Serviços de streaming e rede |
| **Garantia da Qualidade** | `@Debugger` | Análise forense de stack traces, teste mínimo de reprodução e patches cirúrgicos. | Testes de regressão, correções |
| | `@Logs` | Execução de suítes de teste de integração, ponta a ponta (E2E) e cobertura. | `tests/*.ts`, relatórios de execução |
| | `@Security` | Verificação de permissões (RBAC), sanitização de entrada e isolamento de dados. | Políticas de segurança, auditorias |
| | `@Master` | Revisão de código, auditoria estática de conformidade e autorização de merge. | Aprovação de branches, relatórios |
| **Comercial & Monetização** | `@Copywriter` | Documentação técnica comercial, mensagens de onboarding e propostas de valor. | Documentos de copy, páginas |
| | `@Growth` | Estrutura de aquisição de tráfego, eventos de conversão e rastreamento. | Esquemas de tracking, métricas |
| | `@Sales` | Roteiros técnicos para demonstração comercial e qualificação de clientes. | Scripts de demo, cadências |
| | `@Monetization`| Modelagem de planos de assinatura, precificação por uso e margem operacional. | Configurações de planos e cotas |

---

## 4. Ferramentas e Motores de Análise (`scripts/`)

O repositório disponibiliza utilitários de linha de comando para análise estática, verificação e automação de processos:

### 4.1. `spec_linter.py` — Auditoria Estática de Especificações
Verifica se um documento de especificação atende aos critérios formais de engenharia antes do início da codificação.
- **Critérios Auditados:** Metadados canônicos, problema de negócio delimitado, contratos DTOs associados, critérios de aceite BDD (*Given-When-Then*), modos de falha e rastreabilidade para testes.
- **Uso:**
  ```bash
  python scripts/spec_linter.py --file docs/specs/SPEC-CORE-001.md
  ```

### 4.2. `repo_map_engine.py` — Análise de Centralidade de Dependências
Mapeia o grafo de dependências do repositório através da análise estática de imports e calcula a centralidade dos nós (*in-degree*).
- **Finalidade:** Identifica os componentes centrais da arquitetura para mitigar riscos de regressão em alterações estruturais.
- **Uso:**
  ```bash
  python scripts/repo_map_engine.py --dir . --top 10
  ```

### 4.3. `scientific_researcher.py` — Avaliação Epistêmica e Red Teaming
Aplica filtros críticos contra hipóteses técnicas antes de sua implementação na base de código.
- **Critérios de Validação:**
  1. *Falsificabilidade:* Exigência de métricas quantitativas de rejeição (latência, memória, throughput).
  2. *Armadilha da Complexidade:* Penalização de dependências desnecessárias.
  3. *Red Teaming:* Identificação de riscos operacionais, consistência de cache e I/O.
- **Uso:**
  ```bash
  python scripts/scientific_researcher.py \
    --topic "Avaliação de Estratégia de Cache" \
    --hypothesis "Uso de cache em memória reduz p95 para menos de 50ms" \
    --metric "Latencia p95 < 50ms e consumo de RAM < 64MB" \
    --risk LOW
  ```

### 4.4. `autonomous_venture_engine.py` — Instanciação Estruturada de Projetos
Gera a estrutura física completa de um novo projeto a partir de uma descrição funcional delimitada, integrando contratos, esquemas de dados, backend, frontend e suíte de testes.
- **Uso:**
  ```bash
  python scripts/autonomous_venture_engine.py \
    --idea "Descrição concisa do sistema" \
    --name "NomeDoProjeto" \
    --target-dir ./projetos
  ```

### 4.5. `graph_architectural_navigator.py` — Raio de Impacto (Blast Radius)
Calcula o impacto de uma alteração em até 5 saltos na árvore de dependências (Chamadores AST -> Contratos -> Especificações -> Testes).

---

## 5. Procedimento de Instalação e Integração

### Adicionar a um Repositório Existente como Submódulo
```bash
git submodule add git@github.com:eliel-acioly/agent-os.git .agents
```

### Inicializar Estrutura de Governança
```bash
python .agents/scripts/bootstrap_project.py \
  --target-dir . \
  --name "NomeDoProjeto" \
  --domain "DOMINIO_TECNICO"
```

---

## 6. Verificação e Suíte de Testes

Para validar a integridade dos motores e scripts do repositório:

```bash
# Validação do linter de especificações
python scripts/spec_linter.py --file examples/ClinicReactivator/docs/specs/SPEC-CORE-001-motor-central.md

# Validação do mapeador topológico de repositório
python scripts/repo_map_engine.py --dir . --top 5

# Validação do laboratório de verificação científica
python scripts/scientific_researcher.py \
  --topic "Teste de Integridade de Cache" \
  --hypothesis "Persistência em memória reduz tempo de acesso" \
  --metric "Latencia < 10ms" \
  --risk LOW

# Execução do teste ponta a ponta do projeto de exemplo
node examples/ClinicReactivator/tests/test_core_e2e.js
```

---

## 7. Licença e Governança

Desenvolvido sob padrões formais de engenharia de software e análise estática.  
Mantido por **Eliel Acioly** — 2026.
