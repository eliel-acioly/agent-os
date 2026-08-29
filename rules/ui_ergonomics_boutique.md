---
name: ui-ergonomics-boutique-rules
description: Regras obrigatórias de usabilidade, ergonomia e design de luxo B2B para o módulo Lojista Boutique (antecipia-ui).
trigger:
  path: "antecipia-ui/src/modules/admin/**/*"
---

# Regras de Usabilidade e Luxo B2B (Lojista Boutique)

Quando estiver trabalhando nos painéis ou visualizações do módulo Boutique (`antecipia-ui/src/modules/admin`), você **DEVE** seguir estas diretrizes visuais e de design. O cliente Boutique B2B não quer ver "código" ou "interface poluída", ele espera uma experiência neuromórfica e refinada.

## 1. Design de Luxo & Minimalismo (High-Contrast Elegante)
- **Paleta de Cores:** Evite o uso de vermelhos e verdes saturados (`bg-red-500`, `bg-green-500`). Substitua por tons brandos ou borders semânticos (`border-red-500/20`, texto em `text-rose-400`).
- **Glassmorphism / Neuromorphism:** Utilize efeitos de blur de fundo com opacidade controlada (`backdrop-blur-xl bg-slate-900/40`) para transmitir tecnologia avançada.
- **Micro-interações:** Toda ação do usuário deve ter feedback visual sutil, seja com `transition-all duration-300` ou animações opacas.

## 2. Hick's Law (Carga Cognitiva)
- O tempo que um lojista leva para tomar uma decisão aumenta com o número de opções.
- **Oculte complexidade:** Dashboards não devem expor JSONs crus, configurações complexas de câmera ou painéis técnicos sem um botão "Avançado".
- **Máximo de 4 chunks cognitivos por tela:** Apresente (1) Alertas Principais, (2) Mapa de Calor, (3) KPI de Perdas Evitadas, (4) Timeline. 

## 3. Foco em Ação (Insights vs Dados Brutos)
- O lojista não quer saber "quantas pessoas entraram". Ele quer saber "O pico de entrada foi às 14h, desloque um atendente".
- Os componentes devem ter labels auto-explicativos focados na **ação**. Use tipografia com hierarquia forte.
- **Acessibilidade AAA:** Contraste absoluto entre texto e fundo.

## 4. Priorização de Componentes Storybook
- Todo componente de botão, cartão de insight, ou overlay de vídeo (como o `NeuromorphicVisionViewer`) deverá ser exportado e modularizado, sendo preferencialmente testável isoladamente via Storybook.
