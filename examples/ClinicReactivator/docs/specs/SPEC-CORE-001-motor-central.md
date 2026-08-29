# SPEC-CORE-001: MOTOR CENTRAL DO ClinicReactivator
> Status: APPROVED | Domínio: CORE | Versão: 1.0.0

## 1. O Problema de Negócio
O sistema ClinicReactivator resolve a dor de: "Micro-SaaS para clínicas de estética que reativa pacientes inativos via WhatsApp".

## 2. Mapeamento de Contratos & DTOs (SSOT)
Os dados são estritamente governados pelos contratos em `shared/contracts/types.ts`:
- `RegistroAtividadeDTO`
- `OportunidadeReceitaDTO`
- `MetricasPerformanceDTO`

## 3. Critérios de Aceite (BDD / Given-When-Then)
- **Cenário 1: Ingestão de Novo Evento**
  - **Dado que** o sistema recebe uma mensagem ou evento via webhook,
  - **Quando** o payload contém identificador válido e timestamp,
  - **Então** o registro é persistido no banco e emitido em tempo real para a UI.

- **Cenário 2: Oportunidade de Receita Detectada**
  - **Dado que** um cliente está inativo há mais de 30 dias,
  - **Quando** o algoritmo preditivo roda,
  - **Então** uma oferta de reativação é gerada e despachada para o canal móvel.

## 4. Modos de Falha & Degradação Graciosa (Graceful Degradation)
- Em caso de queda do canal de mensageria, as mensagens entram em fila local com backoff exponencial.
- Em caso de timeout no banco de dados, o cache em memória absorve a requisição sem travar a interface.

## 5. Rastreabilidade com Testes E2E
- Implementação validada em: `tests/test_core_pipeline_e2e.ts`.
