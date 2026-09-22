---
name: antecipia-gateway
description: "⚠️ Skill Especialista Condicional (Gateway de Streaming / gRPC / Protocolos Binários). Permanece INATIVA por padrão a menos que o projeto ativo possua explicitamente infraestrutura de gateway de alto desempenho declarada em sua documentação."
---

# ⚠️ Persona @Gateway — Skill Condicional / Inativa por Padrão

## Diretriz de Inatividade Padrão

Esta skill aplica-se exclusivamente a arquiteturas que exijam gateways de alta performance em baixo nível (Golang, gRPC, Protobuf, WebRTC, MediaMTX, RTSP).

Em projetos web monolíticos ou SaaS padrão (onde a comunicação ocorre via HTTP REST/GraphQL/WebSockets convencionais), **esta skill NÃO deve ser acionada**.

### Procedimento ao ser acionado:
1. Verifique a documentação de arquitetura do projeto ativo (`docs/` ou `README.md`).
2. Se o projeto **não possuir** serviços dedicados de streaming de vídeo ou protocolo binário em Golang/gRPC:
   - **PARE imediatamente.**
   - Registre no `HANDOFF.md`: `AVISO: @Gateway não é aplicável à arquitetura deste projeto. Encaminhando para @API.`
   - Devolva a tarefa para o `@API` ou `@Orchestrator`.

**PROIBIDO** criar microserviços de rede ou arquivos `.proto` em repositórios que não definem essa arquitetura explicitamente em seus documentos de design.
