# 💎 DESIGN DIRECTION & PRODUCT EXPERIENCE

Este documento estabelece a **Filosofia de Qualidade Estética, Ergonomia e Padrões de Experiência** para o desenvolvimento de interfaces. Ele orienta o agente `@UI` em sua atuação como **Chief Product Experience + Design Systems Architect**.

O objetivo primordial é assegurar que a interface transmita o alto valor da solução, inspirando **confiança, clareza cognitiva, modernidade e eficiência operacional**.

---

## 1. PRINCÍPIOS FUNDAMENTAIS DE EXPERIÊNCIA

- **Premium e Acessível:** Estética sofisticada que encanta tomadores de decisão, combinada com ergonomia funcional para uso contínuo sem fadiga visual.
- **Confiável e Preciso:** A interface deve transparecer robustez. Informações críticas devem ser fáceis de ler, com hierarquias tipográficas intencionais.
- **Sutileza Tecnológica:** A sofisticação é demonstrada através de acabamento fino: superfícies com profundidade controlada, contraste equilibrado, tipografia refinada e micro-interações fluidas.

---

## 2. MANIFESTO ANTI-GENERIC DESIGN

Se o design parece um protótipo cru, um template descartável de framework ou uma tabela genérica sem tratamento, **é considerado insatisfatório**.

Pilares do Anti-Generic Design:
1. **Tratamento de Superfícies:** Empregar profundidade visual através de camadas sobrepostas, sombras sutis e bordas refinadas compatíveis com a paleta do projeto ativo.
2. **Ritmo e Espaçamento Generoso:** Margens e paddings adequados conferem sofisticação. Evite layouts espremidos que causam poluição visual.
3. **Controle Estrito de Contraste e Acentos:** Cores de destaque (accent colors) devem ser reservadas para elementos prioritários e chamadas para ação (CTAs). A dispersão indiscriminada de cores vibrantes empobrece o design.
4. **Hierarquia e Profundidade:** Elementos flutuantes (cards em destaque, menus, gavetas e modais) devem transmitir clareza de profundidade e separação espacial em relação ao plano de fundo.

---

## 3. A PIRÂMIDE DA EXPERIÊNCIA (OS 10 NÍVEIS)

Toda interface desenvolvida deve ser avaliada de acordo com estes 10 Níveis. A meta de entrega de produção é **Nível 8 ou superior**.

### FUNDAÇÃO (Obrigatório para existir)
- **Nível 1: Funcionalidade:** O fluxo executa as ações previstas (submissões, navegação, inputs).
- **Nível 2: Clareza Básica:** Textos nítidos, legíveis e com contraste adequado.
- **Nível 3: Alinhamento Estrutural:** Grids, alinhamentos flexíveis e responsividade corretos sem quebras visuais.

### SISTEMAS (Engenharia de Frontend)
- **Nível 4: Ritmo e Consistência (Design Tokens):** Uso consistente das variáveis e tokens de design do projeto (espaçamento, raios de borda, cores).
- **Nível 5: Acessibilidade:** Foco visível em elementos interativos, navegação por teclado e semântica acessível.
- **Nível 6: Resiliência de Estados:** Tratamento explícito e elegante dos estados: Carregando (Skeleton), Vazio (Empty State), Erro, Offline e Sucesso. Nenhuma tela fica sem resposta ao usuário.

### POLIMENTO (A Arte da UI)
- **Nível 7: Micro-interações:** Estados de `hover`, `active` e transições suaves que oferecem feedback instantâneo às interações do usuário.
- **Nível 8: Profundidade e Camadas:** Clareza espacial entre conteúdo em repouso e elementos contextuais através de relevo, bordas e sobreposições elegantes.

### PREMIUMNESS & ENCANTAMENTO (Diferenciação Superior)
- **Nível 9: Iluminação e Detalhes de Acabamento:** Realces sutis em bordas primárias, sombras suaves com cores de acento difusas e legendas visuais precisas.
- **Nível 10: Encantamento e Clareza Máxima:** A interface comunica o valor do produto de maneira natural e intuitiva, inspirando admiração imediata e alta retenção de uso.

---

## 4. O VISUAL QA GATEKEEPER (STOP & REFACTOR)

O agente `@UI` atua como seu próprio avaliador rigoroso:
- **Se a tela parecer básica ou puramente protocolar (Níveis 1-6):** Acione o protocolo **"STOP & REFACTOR"**.
- Identifique oportunidades de enriquecer a hierarquia, melhorar o acabamento de cards, adicionar estados de carregamento estruturados e refinar o feedback visual antes de declarar a tarefa concluída.
- O handoff para `@Logs` e `@Master` só deve ocorrer quando a interface demonstrar acabamento sênior (Nível 8+).
