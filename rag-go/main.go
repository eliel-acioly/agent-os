package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// AgentCollections maps agents to their target collections (for future REST ChromaDB use)
var AgentCollections = map[string][]string{
	"API":          {"antecipia_antecipia-api", "antecipia_all"},
	"UI":           {"antecipia_antecipia-ui", "antecipia_all"},
	"DB":           {"antecipia_antecipia-api", "antecipia_all"},
	"Contracts":    {"antecipia_shared", "antecipia_all"},
	"AI_Edge":      {"antecipia_services", "antecipia_all"},
	"Gateway":      {"antecipia_services", "antecipia_all"},
	"Logs":         {"antecipia_all"},
	"Master":       {"antecipia_all"},
	"Orchestrator": {"antecipia_all"},
	"Deploy":       {"antecipia_all"},
}

type SearchResult struct {
	Text      string  `json:"text"`
	Source    string  `json:"source"`
	StartLine int     `json:"start_line"`
	EndLine   int     `json:"end_line"`
	FileType  string  `json:"file_type"`
	Relevance float64 `json:"relevance"`
}

type Snapshot struct {
	RecentChanges []string `json:"recent_changes"`
}

func main() {
	query := flag.String("query", "", "Consulta semântica (obrigatório)")
	qShort := flag.String("q", "", "Consulta semântica (atalho)")
	agent := flag.String("agent", "Master", "Agente consultante")
	aShort := flag.String("a", "", "Agente consultante (atalho)")
	top := flag.Int("top", 5, "Número de resultados")
	kShort := flag.Int("k", 0, "Número de resultados (atalho)")
	jsonOut := flag.Bool("json", false, "Saída em JSON")
	jShort := flag.Bool("j", false, "Saída em JSON (atalho)")

	flag.Parse()

	// Handle short flags
	if *qShort != "" {
		*query = *qShort
	}
	if *aShort != "" {
		*agent = *aShort
	}
	if *kShort != 0 {
		*top = *kShort
	}
	if *jShort {
		*jsonOut = true
	}

	if *query == "" {
		fmt.Println("Erro: --query ou -q é obrigatório.")
		os.Exit(1)
	}

	if !*jsonOut {
		separator := strings.Repeat("═", 65)
		fmt.Printf("\n%s\n", separator)
		fmt.Printf("  ⚡ AntecipIA GraphRAG Query Engine (Golang Edition)\n")
		fmt.Printf("  Agente: @%s  |  Query: '%s'\n", *agent, *query)
		fmt.Printf("%s\n", separator)
	}

	results := executeSearch(*query, *agent, *top)

	if *jsonOut {
		b, _ := json.MarshalIndent(results, "", "  ")
		fmt.Println(string(b))
	} else {
		printFormatted(results, *query)
	}
}

func executeSearch(query, agent string, top int) []SearchResult {
	// FASE 3 — Delega a busca semântica ao motor ChromaDB (Python), que agora
	// indexa antecipia-api/server (motores de inteligência) e usa espaço cosseno.
	root := findRepoRoot()
	script := filepath.Join(root, ".agents", "rag", "query_engine.py")
	py := os.Getenv("PYTHON_BIN")
	if py == "" {
		py = "python"
	}

	if _, err := os.Stat(script); err != nil {
		return fallbackKeywordSearch(query, filepath.Join(root, ".agents", "memory"), top)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, py, script,
		"--query", query, "--agent", agent, "--top", strconv.Itoa(top), "--json")
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	if err := cmd.Run(); err != nil {
		return fallbackKeywordSearch(query, filepath.Join(root, ".agents", "memory"), top)
	}

	var results []SearchResult
	if err := json.Unmarshal(bytes.TrimSpace(out.Bytes()), &results); err != nil {
		return fallbackKeywordSearch(query, filepath.Join(root, ".agents", "memory"), top)
	}

	logQuery(agent, query, len(results))

	return results
}

func findRepoRoot() string {
	// Localiza a raiz do monorepo subindo a partir do diretório do executável
	// (binário em .agents/rag-go/) ou do CWD, procurando pnpm-workspace.yaml.
	starts := []string{}
	if exe, err := os.Executable(); err == nil {
		starts = append(starts, filepath.Dir(exe))
	}
	if wd, err := os.Getwd(); err == nil {
		starts = append(starts, wd)
	}
	for _, start := range starts {
		dir := start
		for i := 0; i < 8; i++ {
			if _, err := os.Stat(filepath.Join(dir, "pnpm-workspace.yaml")); err == nil {
				return dir
			}
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	return "."
}

func fallbackKeywordSearch(query, snapshotDir string, top int) []SearchResult {
	var results []SearchResult
	keywords := strings.Fields(strings.ToLower(query))

	files, err := os.ReadDir(snapshotDir)
	if err != nil {
		return results
	}

	for _, file := range files {
		if strings.HasPrefix(file.Name(), "snapshot_") && strings.HasSuffix(file.Name(), ".json") {
			path := filepath.Join(snapshotDir, file.Name())
			content, err := os.ReadFile(path)
			if err != nil {
				continue
			}

			var snap Snapshot
			if err := json.Unmarshal(content, &snap); err != nil {
				continue
			}

			for _, change := range snap.RecentChanges {
				changeLower := strings.ToLower(change)
				match := false
				for _, kw := range keywords {
					if strings.Contains(changeLower, kw) {
						match = true
						break
					}
				}
				if match {
					results = append(results, SearchResult{
						Text:      fmt.Sprintf("Arquivo modificado recentemente: %s", change),
						Source:    change,
						Relevance: 0.5,
					})
				}
			}
		}
	}

	// Sort by relevance
	sort.Slice(results, func(i, j int) bool {
		return results[i].Relevance > results[j].Relevance
	})

	if len(results) > top {
		return results[:top]
	}
	return results
}

func logQuery(agent, query string, count int) {
	logFile := filepath.Join(findRepoRoot(), ".agents", "memory", "session_log.jsonl")
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	entry := map[string]interface{}{
		"timestamp":     time.Now().Format(time.RFC3339),
		"agent":         agent,
		"event":         "rag_query_go",
		"query":         query,
		"results_count": count,
	}
	b, _ := json.Marshal(entry)
	f.Write(append(b, '\n'))
}

func printFormatted(results []SearchResult, query string) {
	if len(results) == 0 {
		fmt.Println("Nenhum resultado encontrado no índice RAG.")
		fmt.Println("\n[DICA] Execute o indexador ou verifique a conexão com ChromaDB.")
		return
	}

	fmt.Printf("🔍 GraphRAG Context — Query: '%s'\n", query)
	fmt.Println(strings.Repeat("─", 65))

	for i, r := range results {
		fmt.Printf("\n[%d] %s:L%d-%d  (relevância: %.2f)\n", i+1, r.Source, r.StartLine, r.EndLine, r.Relevance)
		fmt.Println("```")
		
		text := r.Text
		if len(text) > 300 {
			text = text[:300] + "..."
		}
		fmt.Println(text)
		fmt.Println("```")
	}
	fmt.Printf("\n%s\n\n", strings.Repeat("═", 65))
}
