// Package usage — file_logger_plugin: writes each per-call usage record to a
// daily-rotated JSONL file on disk. Designed for benchmark trial token attribution
// (so codex / qwen-coder / claude-code per-call usage can be aligned to a trial
// timeline post-hoc).
//
// Output: <log_dir>/per_call_usage_YYYY-MM-DD.jsonl  (one JSON record per line)
//
// Enable via env var: CLIPROXY_PER_CALL_USAGE_DIR (defaults to ./logs)
package usage

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	coreusage "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/usage"
)

func init() {
	// Register alongside the in-memory LoggerPlugin (init order in this file
	// runs after the existing init() since both are in the same package; Go
	// guarantees init() per file, no ordering between files in same package
	// for non-dep reasons, so registering twice is fine — both plugins receive
	// each Record).
	coreusage.RegisterPlugin(NewFileLoggerPlugin())
}

// FileLoggerPlugin writes each Record as one JSONL line to a daily file.
type FileLoggerPlugin struct {
	mu     sync.Mutex
	curDay string
	file   *os.File
	dir    string
}

// NewFileLoggerPlugin builds a new file logger.
func NewFileLoggerPlugin() *FileLoggerPlugin {
	dir := os.Getenv("CLIPROXY_PER_CALL_USAGE_DIR")
	if dir == "" {
		dir = "logs"
	}
	return &FileLoggerPlugin{dir: dir}
}

// HandleUsage implements coreusage.Plugin: append one JSON line per call.
func (p *FileLoggerPlugin) HandleUsage(ctx context.Context, record coreusage.Record) {
	if p == nil {
		return
	}
	p.mu.Lock()
	defer p.mu.Unlock()

	day := time.Now().UTC().Format("2006-01-02")
	if p.file == nil || p.curDay != day {
		if p.file != nil {
			_ = p.file.Close()
		}
		_ = os.MkdirAll(p.dir, 0o755)
		path := filepath.Join(p.dir, fmt.Sprintf("per_call_usage_%s.jsonl", day))
		f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
		if err != nil {
			return
		}
		p.file = f
		p.curDay = day
	}

	entry := map[string]any{
		"requested_at_unix_ms":        record.RequestedAt.UnixMilli(),
		"requested_at":                record.RequestedAt.UTC().Format(time.RFC3339Nano),
		"latency_ms":                  record.Latency.Milliseconds(),
		"provider":                    record.Provider,
		"model":                       record.Model,
		"source":                      record.Source,
		"auth_id":                     record.AuthID,
		"auth_index":                  record.AuthIndex,
		"failed":                      record.Failed,
		"input_tokens":                record.Detail.InputTokens,
		"output_tokens":               record.Detail.OutputTokens,
		"reasoning_tokens":            record.Detail.ReasoningTokens,
		"cached_tokens":               record.Detail.CachedTokens,
		"cache_read_input_tokens":     record.Detail.CacheReadInputTokens,
		"cache_creation_input_tokens": record.Detail.CacheCreationInputTokens,
		"total_tokens":                record.Detail.TotalTokens,
		"cache_usage_reported":        record.Detail.CacheUsageReported,
		"upstream_usage_json":         record.Detail.RawUsage,
		"upstream_response_id":        record.Detail.UpstreamResponseID,
	}

	b, err := json.Marshal(entry)
	if err != nil {
		return
	}
	b = append(b, '\n')
	_, _ = p.file.Write(b)
	_ = p.file.Sync() // best-effort flush so harbor can read mid-trial
}
