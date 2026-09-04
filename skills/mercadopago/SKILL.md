---
name: mercadopago
description: >-
  Operações, diagnósticos, conciliação e gestão de pagamentos reais via Mercado Pago PIX,
  integração MCP oficial e local, tratamento de webhooks HMAC e custódia segura na LigaCommerce.
---

# Skill: Mercado Pago — Pagamentos Reais & Integração MCP

Esta skill governa o ciclo de vida completo de pagamentos, conciliação e transações financeiras da **LigaCommerce** utilizando o ecossistema oficial do **Mercado Pago**.

---

## 🏛️ 1. Arquitetura de Pagamentos LigaCommerce

1. **Gateway:** Mercado Pago SDK v3 (`mercadopago: ^3.6.0`).
2. **Método Principal:** PIX Dinâmico com QR Code em imagem Base64 e Chave Copia e Cola (EMV Standard).
3. **Validade do PIX:** 30 minutos por cobrança (`date_of_expiration`).
4. **Liquidação & Split:**
   - Taxa da plataforma calculada dinamicamente via `calculateMonetization` (ex: 5% a 12% por categoria).
   - Valor líquido do lojista reservado para repasse.
5. **Webhook Autoritativo (`POST /api/payments/mercadopago/webhook`):**
   - Assinatura HMAC SHA-256 no header `x-signature` com proteção anti-replay (janela de tolerância máxima de 10 minutos).
   - Consulta autoritativa `GET /v1/payments/{id}` no gateway (Zero Trust no payload).
   - Decremento atômico de estoque via RPC Postgres `decrement_listing_stock`.
   - Transição idempotente para status `pago`.

---

## 🔑 2. Chaves de Acesso: Sandbox (TEST) vs Produção Real (APP_USR)

| Tipo de Ambiente | Prefixo do Access Token | Prefixo da Public Key | Efeito Prático |
| :--- | :--- | :--- | :--- |
| **Sandbox / Homologação** | `TEST-...` | `TEST-...` | Simulação bancária. Dinheiro fictício. Não debita do app do banco. |
| **Produção Oficial** | `APP_USR-...` | `APP_USR-...` | **Pagamento Real**. O cliente escaneia com o app do banco (Nubank, Itaú, etc.) e o valor é creditado na conta do Mercado Pago. |

> [!CAUTION]
> A aplicação possui trava de isolamento estrito: em `NEXT_PUBLIC_APP_ENV="production"`, o sistema rejeita chaves `TEST-` para evitar que vendas reais sejam registradas com dinheiro fictício.

---

## 🚀 3. Checklist para Ativação de Pagamentos Reais

1. Acesse o painel de desenvolvedores: [Mercado Pago Developers](https://www.mercadopago.com.br/developers/panel).
2. Selecione a sua aplicação ou crie uma aplicação do tipo *Marketplace / Pagamentos Online*.
3. Clique em **Credenciais de Produção**:
   - Copie o **Access Token** (`APP_USR-...`).
   - Copie a **Public Key** (`APP_USR-...`).
4. Clique em **Webhooks / Notificações IPN**:
   - Cadastre a URL: `https://ligacommerce.vercel.app/api/payments/mercadopago/webhook`.
   - Marque o evento: **Pagamentos** (`payment`).
   - Copie a **Chave Secreta de Assinatura** (`MERCADOPAGO_WEBHOOK_SECRET`).
5. Atualize as variáveis no `.env.production` e sincronize com a Vercel:
   ```bash
   npx tsx scripts/sync-vercel-env.ts SEU_VERCEL_TOKEN
   ```

---

## 🛠️ 4. Servidores MCP Disponíveis

### A. Servidor MCP Remoto Oficial do Mercado Pago
- Endpoint: `https://mcp.mercadopago.com/mcp`
- Configurado em `.agents/mcp_config.json`.
- Permite que a IA consulte diretamente a documentação técnica e endpoints oficiais.

### B. Servidor MCP Local LigaCommerce (`scripts/mcp-mercadopago-server.js`)
- Ferramentas disponíveis:
  - `mp_check_diagnostic`: Testa conectividade e tipo de chave.
  - `mp_get_payment`: Consulta status de um pagamento pelo ID.
  - `mp_create_test_pix`: Emite um PIX de teste para validação.
  - `mp_simulate_webhook`: Simula o envio de webhook assinado com HMAC SHA-256.

---

## 🧪 5. Comandos e Scripts Úteis

```bash
# Diagnóstico de conectividade e prontidão para pagamentos reais
npx tsx --env-file=.env.production scripts/test-mercadopago-readiness.ts

# Teste do servidor MCP local via Stdio
node scripts/mcp-mercadopago-server.js
```
