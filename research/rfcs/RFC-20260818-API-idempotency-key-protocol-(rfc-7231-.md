# 📄 Idempotency-Key Protocol (RFC 7231 Standard)

> **RFC ID:** RFC-20260818-API-idempotency-key-protocol-(rfc-7231-  
> **Agente Proponente:** @API  
> **Data de Emissão:** 2026-08-18 03:59  
> **Status:** PROPOSTO / EM AVALIAÇÃO  
> **Padrão:** AntecipIA Aerospace Standard v3.0 (NASA / SpaceX Quality)  

---

## 1. Contexto & Motivação
- **Domínio:** Core de Comunicação em Tempo Real, Resiliência e Despacho
- **Analogia Aeroespacial:** SpaceX Flight Software Fault-Tolerant Bus (Triple Modular Redundancy)
- **Problema:** Prevenir regressões, aumentar a resiliência e garantir confiabilidade de missão crítica.

---

## 2. Proposta Técnica
- **Categoria:** Integridade Transacional
- **Tecnologia / Paradigma:** Idempotency-Key Protocol (RFC 7231 Standard)
- **Maturidade (Readiness):** IETF RFC Standard
- **Biblioteca Recomendada:** `Express Idempotency Middleware com Redis/In-Memory Cache`

### Impacto Esperado:
> Evita duplicação acidental de despachos de viatura ou alarmes em reconnects de rede.

---

## 3. Plano de Ação Imediata (@API)
- [ ] Exigir cabeçalho Idempotency-Key em todas as rotas POST/PATCH de despacho e criação de alerta.
- [ ] Criar testes de validação no padrão Property-Based / Invariant
- [ ] Atualizar documentação em `/docs/` e `shared/contracts/`
- [ ] Registrar lição aprendida em `.agents/memory/knowledge_base.json`

---

## 4. Critérios de Aceite
1. Zero quebra de compatibilidade regressiva.
2. 100% de testes automatizados passando.
3. Avaliação formal de conformidade arquitetural pelo `@Master`.
