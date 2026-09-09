---
name: ui-performance-rules
description: Regras obrigatórias de performance e otimização para desenvolvimento na interface de usuário, focando em WebGL, React 19 e renderizações limpas.
trigger:
  path: "{app,components}/**/*.{tsx,ts}"
---

# Regras de Performance para Frontend

Sempre que atuar em `app/` ou `components/`, você **DEVE** seguir estritamente as diretrizes abaixo para garantir performance na camada de visualização.

## 1. Otimização de WebGL (Pixi.js v8)
- **Garbage Collection (GC):** Nunca instancie novos `Graphics` ou `Sprites` dentro do loop principal (`ticker.add()`). Use pools de objetos (Object Pooling) para reaproveitar Bounding Boxes, trilhas e rótulos.
- **Evite Memory Leaks:** Ao desmontar um componente React que envolve Pixi.js, chame explicitamente `app.destroy(true, true)` e destrua texturas soltas para limpar a VRAM.
- **Main Thread Unblocking:** Cálculos pesados de intersecção (Hit Testing) em centenas de atores devem ocorrer na borda (Go) ou no máximo em Web Workers, mantendo a thread principal estável em 60 FPS.

## 2. Gerenciamento de Estado de Alta Frequência (Zustand & React 19)
- **Fatias de Estado (Slices):** Não consuma a *store* inteira em um componente. É ESTRITAMENTE PROIBIDO fazer `const state = useStore()`. Use seletores estritos: `const isAlertActive = useStore(state => state.isAlertActive)`.
- **Zustand em Eventos Frequentes:** Para updates de posição (telemetria < 100ms), evite renderizar a árvore do React. Em vez disso, faça **Transient Updates** assinando diretamente a *store* (`useStore.subscribe`) fora do ciclo de renderização.

## 3. Isolamento e Storybook (Componentes Puros)
- **Zero Lógica de Negócio Injetada na View:** Componentes visuais (Botões, Painéis, Cartões) não devem disparar chamadas fetch nem conhecer o Socket.IO diretamente. Devem receber propriedades (props) e handlers de eventos.
- **Desenvolvimento Isolado:** Sempre que criar um componente novo, certifique-se de que ele funcione perfeitamente fora do contexto da aplicação (ex: dentro do Storybook).

## 4. Gerenciamento de WebSockets
- Evite criar múltiplas instâncias de clientes Socket.IO. Utilize um único hook `useWorldModel` ou contexto global para manter a conexão viva, e distribua os eventos de forma reativa para as *stores* (Zustand) ou reducers locais.
