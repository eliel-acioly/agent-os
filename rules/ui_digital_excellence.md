# 💎 ANTECIPIA UI SOTA: O PILAR CENTRAL DA EXCELÊNCIA DIGITAL
Governança Oficial de Frontend (Psicologia × Estética × Performance)

---

## 🎯 1. A Tríade da Excelência

1. **IDENTIDADE (Formas & Geometria):**
   - Geometria tática e cantos médios (`border-radius: 12px a 16px`) para SaaS/Dashboard.
   - Minimalismo radical e linhas finas para Luxury/Boutique.
   - Arredondamento e solidez para Fintech/Segurança.

2. **VITALIDADE (Cores em `oklch()`):**
   - Cores perceptualmente uniformes em qualquer tela (sem pontos mortos de cinza).
   - WCAG AAA compliance nativo.
   - **Deep Teal Base:** `oklch(14% 0.03 210)`
   - **Card Surface:** `oklch(20% 0.04 210)`
   - **Elevated Surface / Modal:** `oklch(24% 0.05 210)`
   - **Subtle Borders:** `oklch(32% 0.04 210)`
   - **Primary Text:** `oklch(96% 0.01 210)`
   - **Secondary Text:** `oklch(72% 0.03 210)`
   - **Emerald Data (Verde Sucesso/ROI):** `oklch(72% 0.18 145)`
   - **Tactical Brand (Laranja Ação/Alerta):** `oklch(72% 0.19 55)`

3. **ESTRUTURA (Grid & Flex Sinergia):**
   - **Grid (Macro / Esqueleto):** `display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem;`
   - **Flexbox (Micro / Coração):** `display: flex; gap: 8px | 16px; align-items: center;`
   - **Container Queries (`@container`):** Cards que respondem ao tamanho do contêiner pai, não à viewport inteira.

---

## ⚡ 2. Performance & Animações na GPU

- **Regra de Ouro da Leveza:** Animações exclusivamente em `transform` e `opacity`.
- **Hardware Acceleration:** `will-change: transform, opacity;` nos componentes interativos.
- **Glassmorphism Tático:** `backdrop-filter: blur(16px); background: oklch(18% 0.03 210 / 0.85);` com borda fina de 1px.
- **Tipografia Fluida:** `font-size: clamp(1.5rem, 2vw + 1rem, 2.5rem);` com Inter e JetBrains Mono (para telemetria).

---

## 🧭 3. Arquitetura Adaptativa & Navegação à Velocidade do Pensamento

1. **Mobile-First (< 768px):** Bottom Navigation Bar fixa, translúcida, com alcance ideal ao polegar.
2. **Desktop-First (≥ 768px):** Sidebar expansível/retrátil com transições suaves em `transform`.
3. **Command Palette (`Cmd/Ctrl + K` - Palácio Mental):** Acesso instantâneo a qualquer workspace, câmera, alerta ou ação com digitação ultrarrápida.
