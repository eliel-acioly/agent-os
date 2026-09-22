# 🛠️ UI PATTERNS & IMPLEMENTATION (AGENT-OS)

Este documento é a FONTE DA VERDADE **TÉCNICA** para o `@UI`. 
> Para regras de Estética, Qualidade Visual, Anti-Generic Design e os 10 Níveis de Excelência, consulte obrigatoriamente o **[DESIGN_DIRECTION.md](.agents/skills/antecipia-ui/DESIGN_DIRECTION.md)**.

---

## 1. ESTRATÉGIA DE LAYOUT (GRID & FLEX)

A escolha não é preferência, é arquitetura.
- **GRID (O Esqueleto / Macro):** Bidimensional. Use para dashboards, containers principais e painéis de câmeras.
  - Padrão: `grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr))`.
- **FLEXBOX (O Coração / Micro):** Unidimensional. Use para alinhamento interno de cards, navbars, botões e centralização de ícones.
- **A Regra do Ritmo:** O espaçamento (`gap`) DEVE ser sempre múltiplo de 8 (8, 16, 24, 32). O `gap` substitui margens manuais.

---

## 2. ARQUITETURA ADAPTATIVA E NAVEGAÇÃO

- **Desktop (≥ 768px):** Sidebar persistente e expansível (padrão dominante em SaaS B2B).
- **Mobile (< 768px):** Drawer (Vaul) como padrão principal. Bottom Nav apenas quando a arquitetura de informação for plana e com 3-5 destinos de peso equivalente e alta frequência.
- **O Palácio Mental (Command Palette):** Em desktop, implementar navegação via `Cmd/Ctrl + K` (cmdk) para pesquisa, saltos de seção e ações instantâneas.

---

## 3. IMPLEMENTAÇÃO DE SUPERFÍCIES (GLASS & ELEVATION)

A aplicação do Glassmorphism e da Profundidade (Nível 8 do `DESIGN_DIRECTION.md`) utiliza as seguintes classes baseadas em Tailwind v4 e CSS customizado:
- **Camadas Flutuantes (Chrome, Sidebars, Modais):** Utilize `backdrop-blur` com cores de superfície translúcidas (`bg-background/80`). 
- **Cards de Destaca/Dashboard:** `card-teal-sota` e `card-teal-elevated`.
- **Restrição:** Em superfícies densas de dados (tabelas, listas longas), utilize superfícies opacas para não sacrificar a performance de renderização.

---

## 4. CSS DE ÚLTIMA GERAÇÃO E PERFORMANCE (GPU)

- **Propriedades Lógicas:** `padding-inline`, `margin-block` etc.
- **Container Queries:** Use `@container` para cards de conteúdo. O componente se adapta ao tamanho do contêiner pai.
- **Fluidez:** `clamp()` para tipografia responsiva.
- **Animações:** Estritamente GPU-only.
  - Altere apenas `transform` e `opacity`.
  - Use `will-change: transform, opacity` em elementos de interação frequente.
  - Biblioteca obrigatória para micro-interações: Motion (Framer Motion).

---

## 5. GESTÃO DE ESTADOS E ACESSIBILIDADE

- Todo componente assíncrono deve tratar os 5 estados canônicos: `Loading` (skeletons), `Empty`, `Error`, `Offline/Syncing` e `Success`.
- Acessibilidade: `aria-live="polite"` ou `"assertive"` para atualizações dinâmicas, foco visível e contraste WCAG 2.1 AA/AAA.
- Feedback de ações críticas: Sonner (toasts).

---

## 6. COMPONENT-DRIVEN DEVELOPMENT (OBRIGATÓRIO)

1. Todo elemento visual novo ou refatorado deve ser criado primeiro como componente isolado no Storybook ou biblioteca de componentes.
2. Stories obrigatórias quando aplicável: Default, Hover, Loading, Error, Mobile, Desktop.
3. Variantes de status (ativo, pendente, crítico, liberado etc.) devem ser expressas via CVA (Class Variance Authority).
4. Páginas são apenas composição de componentes já documentados. Proibido gerar layout monolítico.
5. Bibliotecas de suporte recomendadas quando aplicável:
   - shadcn/ui + Base UI / Radix (base de componentes)
   - Tailwind v4 (estilização)
   - Motion (animações)
   - cmdk (Command Palette)
   - Vaul (Drawer mobile)
   - Sonner (toasts)

---

## 7. REGRAS TÉCNICAS INVIOLÁVEIS (STRICT BARRIERS)

- **Zero Emojis:** É ESTRITAMENTE PROIBIDO o uso de emojis nativos na UI. Use exclusivamente `<IconName />` da biblioteca vetorial do projeto (ex: `lucide-react`).
- **Edição de Arquivos:** PROIBIDO o uso de Regex (`replace`, `node -e`) para alterar arquivos TSX/JSX. Use sempre edição estruturada.
- **Gestão de Memória WebGL:** Se o projeto utilizar PixiJS, Three.js ou Canvas WebGL, implementar limpeza imperativa no desmonte dos componentes.
- **Navegação Mobile:** Drawer como padrão. Bottom Nav apenas sob condição de arquitetura de informação plana.
