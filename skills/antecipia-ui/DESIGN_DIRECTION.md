# 💎 DESIGN DIRECTION & PRODUCT EXPERIENCE (ANTECIPIA)

Este documento dita a **Alma, Personalidade e Padrão de Qualidade Estética** do AntecipIA. Ele complementa o `UI_PATTERNS.md` (que foca na implementação de código). 

O agente `@UI` atua como **Chief Product Experience + Design Systems Architect**. O objetivo principal é garantir que a interface reflita o alto valor da inteligência embarcada no produto, inspirando **confiança, eficiência e modernidade**.

---

## 1. A PERSONALIDADE DO ANTECIPIA

- **Premium, mas Acessível:** Uma estética sofisticada que impressiona diretores, mas com ergonomia tática para operadores 24/7.
- **Tático e Seguro:** Não somos um app de redes sociais nem um SaaS de marketing. Somos segurança pública, investigação e inteligência de varejo. O design deve transmitir *seriedade, robustez e precisão*.
- **Tecnológico, não "Gamer":** Elementos de ficção científica (brilhos neon intensos, fontes hackers) são proibidos. A tecnologia é revelada através de sutileza: glassmorphism polido, dark mode refinado, tipografia nítida (JetBrains Mono para dados) e micro-interações fluidas.

---

## 2. ANTI-GENERIC DESIGN MANIFESTO

Se o design parece um "dashboard genérico do Tailwind" ou um "template Bootstrap", **é uma falha**.
Para combater o design genérico, aplicamos:

1. **Guerra aos Brancos Estéreis e Cinzas Chatos:** O fundo (background) e as superfícies (surfaces) utilizam paletas baseadas em escuros profundos e coloridos (Teal/Navy escuro). 
2. **Chega de Espaçamento Espremido:** `Padding` generoso respira luxo. Interfaces espremidas parecem amadoras. O grid não é uma prisão.
3. **Alto Contraste Controlado:** O "Accent Laranja" (brand-orange) é a cor de energia do AntecipIA. Ele NUNCA deve ser espalhado. É exclusivo do Logo e de, no máximo, **1 CTA (Call to Action) tático crítico por tela**. Botões comuns usam tons sofisticados de teal/navy com overlays de estado.
4. **Fim dos Blocos Chapados:** Uma interface premium respira através de *Glassmorphism real* (backdrop-blur + bordas translúcidas + sombras sutis coloridas) aplicado com critério nas camadas flutuantes (chrome, navbars, cards de destaque).

---

## 3. A PIRÂMIDE DA EXPERIÊNCIA (OS 10 NÍVEIS)

Todo design no AntecipIA deve ser julgado segundo estes 10 Níveis. O `@UI` tem a obrigação de entregar, no mínimo, o Nível 8.

### FUNDAÇÃO (Obrigatório para existir)
- **Nível 1: Funcionalidade:** A interface faz o que deve fazer (ex: botão clica, formulário envia).
- **Nível 2: Clareza Básica:** Textos são legíveis, contrastes atendem minimamente (WCAG AA). 
- **Nível 3: Alinhamento Estrutural:** Flexbox e Grid estão corretos. Nada está visualmente quebrado ou torto.

### SISTEMAS (Engenharia de Frontend)
- **Nível 4: Ritmo e Consistência (Tokens):** Espaçamentos seguem múltiplos de 8. Cores são os tokens oficiais (`oklch()`).
- **Nível 5: Acessibilidade Profunda:** Navegação por teclado, ARIA labels corretas, foco visível (`ring-offset`).
- **Nível 6: Resiliência de Estado:** Trata os 5 estados canônicos (Loading/Skeleton, Empty, Error, Offline, Success). Nenhuma tela fica em branco sem explicação.

### POLIMENTO (A Arte da UI)
- **Nível 7: Micro-interações:** Estados de `hover`, `active` e `focus` são perceptíveis e fluidos. O sistema responde instantaneamente ao toque do usuário.
- **Nível 8: Profundidade e Camadas:** Uso magistral de glassmorphism em sobreposições, modais e sidebars. O usuário entende claramente a hierarquia da tela através de sombras e desfoque (`backdrop-blur`).

### PREMIUMNESS & ENCANTAMENTO (O Diferencial AntecipIA)
- **Nível 9: Iluminação e Detalhes Táticos:** O design usa a "luz" a seu favor. Bordas sutis iluminadas (1px gradiente no topo do botão primário), glows radiais extremamente suaves no fundo focando a atenção, degradês semânticos nos dados.
- **Nível 10: Encantamento Instintivo:** A interface conta a história da inteligência. O operador confia na IA (XAI) não apenas porque a métrica está lá, mas pela *maneira autoritária e elegante* com que a métrica é apresentada. O design exala segurança em nível de estado da arte.

---

## 4. O VISUAL QA GATEKEEPER (STOP & REFACTOR)

O agente `@UI` atua como seu próprio juiz implacável.
**Regra de Auto-Auditoria:** 
Antes de aprovar qualquer implementação e finalizar o seu turno, o `@UI` deve realizar uma avaliação visual silenciosa e rigorosa contra os 10 Níveis.

- **Se a tela parecer "Ok" ou "Genérica" (Nível 5-6):** O agente deve acionar a diretriz **"STOP & REFACTOR"**. 
- Ele deve investigar como adicionar profundidade (Nível 8), iluminação (Nível 9) e ritmo perfeito, refatorando o próprio código sem precisar que o CTO solicite.
- O Handoff para o `@Logs` ou `@Master` **só ocorre** quando o `@UI` está genuinamente orgulhoso do visual (Nível 8+).
