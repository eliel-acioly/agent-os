---
name: mercadopago
description: >-
  Operações, diagnósticos, conciliação e gestão de pagamentos reais via Mercado Pago PIX,
  integração MCP oficial e local, tratamento de webhooks HMAC e custódia financeira.
---

# Skill: Mercado Pago — Pagamentos Reais & Integração MCP

Esta skill governa o ciclo de vida de integração, processamento de pagamentos, conciliação e webhooks utilizando o ecossistema oficial do **Mercado Pago** no projeto ativo.

---

## 🔍 Context Discovery Protocol (PRIMEIRO PASSO OBRIGATÓRIO)

Antes de executar operações financeiras ou testes de pagamento:
1. **Identificar Rotas de Pagamento e Webhooks:** Inspecione o repositório para localizar os endpoints de checkout e recepção de webhooks (ex: `/api/payments/mercadopago/webhook`).
2. **Descobrir Configuração de Credenciais:** Verifique os arquivos `.env` ou `.env.example` para mapear os nomes das variáveis (ex: `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_PUBLIC_KEY`, `MERCADOPAGO_WEBHOOK_SECRET`).
3. **Mapear Regras de Negócio e Taxas:** Inspecione os serviços de monetização ou comissões do projeto para calcular splits ou taxas da plataforma.

---

## 🏛️ 1. Arquitetura Padrão de Pagamentos PIX

1. **SDK / Integração:** Mercado Pago SDK v3 ou chamadas HTTP diretas à API v1.
2. **Método Principal:** PIX Dinâmico com QR Code em imagem Base64 e Chave Copia e Cola (EMV Standard).
3. **Validade do PIX:** Tempo determinado por cobrança (`date_of_expiration`).
4. **Webhook Autoritativo:**
   - Validação da assinatura HMAC SHA-256 no header `x-signature` com proteção anti-replay.
   - Consulta autoritativa `GET /v1/payments/{id}` no gateway (Zero Trust no payload).
   - Atualização atômica e transição idempotente de status do pedido.

---

## 🔑 2. Chaves de Acesso: Sandbox (TEST) vs Produção Real (APP_USR)

| Tipo de Ambiente | Prefixo do Access Token | Prefixo da Public Key | Efeito Prático |
| :--- | :--- | :--- | :--- |
| **Sandbox / Homologação** | `TEST-...` | `TEST-...` | Simulação bancária. Não debita de contas reais. |
| **Produção Oficial** | `APP_USR-...` | `APP_USR-...` | **Pagamento Real**. O cliente escaneia com o app do banco e o saldo é liquidado na conta do Mercado Pago. |

> [!CAUTION]
> Em ambientes de produção declarada, certifique-se de rejeitar chaves `TEST-` para evitar aprovação de pedidos com pagamentos fictícios.

---

## 🚀 3. Checklist para Ativação de Pagamentos

1. Acesse o painel de desenvolvedores: [Mercado Pago Developers](https://www.mercadopago.com.br/developers/panel).
2. Configure uma aplicação com credenciais correspondentes ao ambiente (Sandbox ou Produção).
3. Cadastre a URL do Webhook do projeto no painel para o evento `payment`.
4. Configure a chave secreta de webhook (`MERCADOPAGO_WEBHOOK_SECRET`) e as chaves de acesso no ambiente.

---

## 🛠️ 4. Servidores MCP e Ferramentas

- **Servidor MCP Oficial do Mercado Pago:** `https://mcp.mercadopago.com/mcp` para consulta técnica.
- **Scripts de Diagnóstico Locais:** Se o projeto contiver utilitários em `scripts/` (ex: testes de prontidão e simulação de webhooks), utilize-os para validação.
