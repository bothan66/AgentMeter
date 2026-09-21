package executor

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/router-for-me/CLIProxyAPI/v6/internal/config"
	"github.com/router-for-me/CLIProxyAPI/v6/internal/runtime/executor/helps"
	"github.com/router-for-me/CLIProxyAPI/v6/internal/thinking"
	"github.com/router-for-me/CLIProxyAPI/v6/internal/util"
	cliproxyauth "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/auth"
	cliproxyexecutor "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/executor"
	sdktranslator "github.com/router-for-me/CLIProxyAPI/v6/sdk/translator"
	log "github.com/sirupsen/logrus"
	"github.com/tidwall/gjson"
	"github.com/tidwall/sjson"
)

// OpenAICompatExecutor implements a stateless executor for OpenAI-compatible providers.
// It performs request/response translation and executes against the provider base URL
// using per-auth credentials (API key) and per-auth HTTP transport (proxy) from context.
type OpenAICompatExecutor struct {
	provider string
	cfg      *config.Config
}

// NewOpenAICompatExecutor creates an executor bound to a provider key (e.g., "openrouter").
func NewOpenAICompatExecutor(provider string, cfg *config.Config) *OpenAICompatExecutor {
	return &OpenAICompatExecutor{provider: provider, cfg: cfg}
}

// Identifier implements cliproxyauth.ProviderExecutor.
func (e *OpenAICompatExecutor) Identifier() string { return e.provider }

// PrepareRequest injects OpenAI-compatible credentials into the outgoing HTTP request.
func (e *OpenAICompatExecutor) PrepareRequest(req *http.Request, auth *cliproxyauth.Auth) error {
	if req == nil {
		return nil
	}
	_, apiKey := e.resolveCredentials(auth)
	if strings.TrimSpace(apiKey) != "" {
		req.Header.Set("Authorization", "Bearer "+apiKey)
	}
	var attrs map[string]string
	if auth != nil {
		attrs = auth.Attributes
	}
	util.ApplyCustomHeadersFromAttrs(req, attrs)
	return nil
}

// HttpRequest injects OpenAI-compatible credentials into the request and executes it.
func (e *OpenAICompatExecutor) HttpRequest(ctx context.Context, auth *cliproxyauth.Auth, req *http.Request) (*http.Response, error) {
	if req == nil {
		return nil, fmt.Errorf("openai compat executor: request is nil")
	}
	if ctx == nil {
		ctx = req.Context()
	}
	httpReq := req.WithContext(ctx)
	if err := e.PrepareRequest(httpReq, auth); err != nil {
		return nil, err
	}
	httpClient := helps.NewProxyAwareHTTPClient(ctx, e.cfg, auth, 0)
	return httpClient.Do(httpReq)
}

func (e *OpenAICompatExecutor) Execute(ctx context.Context, auth *cliproxyauth.Auth, req cliproxyexecutor.Request, opts cliproxyexecutor.Options) (resp cliproxyexecutor.Response, err error) {
	baseModel := thinking.ParseSuffix(req.Model).ModelName

	reporter := helps.NewUsageReporter(ctx, e.Identifier(), baseModel, auth)
	defer reporter.TrackFailure(ctx, &err)

	baseURL, apiKey := e.resolveCredentials(auth)
	if baseURL == "" {
		err = statusErr{code: http.StatusUnauthorized, msg: "missing provider baseURL"}
		return
	}

	from := opts.SourceFormat
	to := sdktranslator.FromString("openai")
	endpoint := "/chat/completions"
	if opts.Alt == "responses/compact" {
		to = sdktranslator.FromString("openai-response")
		endpoint = "/responses/compact"
	}
	originalPayloadSource := req.Payload
	if len(opts.OriginalRequest) > 0 {
		originalPayloadSource = opts.OriginalRequest
	}
	originalPayload := originalPayloadSource
	originalTranslated := sdktranslator.TranslateRequest(from, to, baseModel, originalPayload, opts.Stream)
	translated := sdktranslator.TranslateRequest(from, to, baseModel, req.Payload, opts.Stream)
	requestedModel := helps.PayloadRequestedModel(opts, req.Model)
	translated = helps.ApplyPayloadConfigWithRoot(e.cfg, baseModel, to.String(), "", translated, originalTranslated, requestedModel)
	if opts.Alt == "responses/compact" {
		if updated, errDelete := sjson.DeleteBytes(translated, "stream"); errDelete == nil {
			translated = updated
		}
	}

	translated, err = thinking.ApplyThinking(translated, req.Model, from.String(), to.String(), e.Identifier())
	if err != nil {
		return resp, err
	}

	if compat := e.resolveCompatConfig(auth); compat != nil && compat.InjectPromptCache && !usesOpenAIAutoPromptCache(baseModel) {
		translated = injectPromptCache(translated)
	}
	if usesOpenAIAutoPromptCache(baseModel) {
		translated = stripPromptCacheControls(translated)
	}
	if compat := e.resolveCompatConfig(auth); compat != nil && compat.StripUnsupportedParams {
		translated = stripUnsupportedOpenAICompatParams(translated)
	}

	url := strings.TrimSuffix(baseURL, "/") + endpoint
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(translated))
	if err != nil {
		return resp, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	if apiKey != "" {
		httpReq.Header.Set("Authorization", "Bearer "+apiKey)
	}
	httpReq.Header.Set("User-Agent", "cli-proxy-openai-compat")
	var attrs map[string]string
	if auth != nil {
		attrs = auth.Attributes
	}
	util.ApplyCustomHeadersFromAttrs(httpReq, attrs)
	var authID, authLabel, authType, authValue string
	if auth != nil {
		authID = auth.ID
		authLabel = auth.Label
		authType, authValue = auth.AccountInfo()
	}
	helps.RecordAPIRequest(ctx, e.cfg, helps.UpstreamRequestLog{
		URL:       url,
		Method:    http.MethodPost,
		Headers:   httpReq.Header.Clone(),
		Body:      translated,
		Provider:  e.Identifier(),
		AuthID:    authID,
		AuthLabel: authLabel,
		AuthType:  authType,
		AuthValue: authValue,
	})

	httpClient := helps.NewProxyAwareHTTPClient(ctx, e.cfg, auth, 0)
	httpResp, err := httpClient.Do(httpReq)
	if err != nil {
		helps.RecordAPIResponseError(ctx, e.cfg, err)
		return resp, err
	}
	defer func() {
		if errClose := httpResp.Body.Close(); errClose != nil {
			log.Errorf("openai compat executor: close response body error: %v", errClose)
		}
	}()
	helps.RecordAPIResponseMetadata(ctx, e.cfg, httpResp.StatusCode, httpResp.Header.Clone())
	if httpResp.StatusCode < 200 || httpResp.StatusCode >= 300 {
		b, _ := io.ReadAll(httpResp.Body)
		helps.AppendAPIResponseChunk(ctx, e.cfg, b)
		helps.LogWithRequestID(ctx).Debugf("request error, error status: %d, error message: %s", httpResp.StatusCode, helps.SummarizeErrorBody(httpResp.Header.Get("Content-Type"), b))
		err = statusErr{code: httpResp.StatusCode, msg: string(b)}
		return resp, err
	}
	body, err := io.ReadAll(httpResp.Body)
	if err != nil {
		helps.RecordAPIResponseError(ctx, e.cfg, err)
		return resp, err
	}
	helps.AppendAPIResponseChunk(ctx, e.cfg, body)
	reporter.Publish(ctx, helps.ParseOpenAIUsage(body))
	// Ensure we at least record the request even if upstream doesn't return usage
	reporter.EnsurePublished(ctx)
	// Translate response back to source format when needed
	var param any
	out := sdktranslator.TranslateNonStream(ctx, to, from, req.Model, opts.OriginalRequest, translated, body, &param)
	resp = cliproxyexecutor.Response{Payload: out, Headers: httpResp.Header.Clone()}
	return resp, nil
}

func (e *OpenAICompatExecutor) ExecuteStream(ctx context.Context, auth *cliproxyauth.Auth, req cliproxyexecutor.Request, opts cliproxyexecutor.Options) (_ *cliproxyexecutor.StreamResult, err error) {
	baseModel := thinking.ParseSuffix(req.Model).ModelName

	reporter := helps.NewUsageReporter(ctx, e.Identifier(), baseModel, auth)
	defer reporter.TrackFailure(ctx, &err)

	baseURL, apiKey := e.resolveCredentials(auth)
	if baseURL == "" {
		err = statusErr{code: http.StatusUnauthorized, msg: "missing provider baseURL"}
		return nil, err
	}

	from := opts.SourceFormat
	to := sdktranslator.FromString("openai")
	originalPayloadSource := req.Payload
	if len(opts.OriginalRequest) > 0 {
		originalPayloadSource = opts.OriginalRequest
	}
	originalPayload := originalPayloadSource
	originalTranslated := sdktranslator.TranslateRequest(from, to, baseModel, originalPayload, true)
	translated := sdktranslator.TranslateRequest(from, to, baseModel, req.Payload, true)
	requestedModel := helps.PayloadRequestedModel(opts, req.Model)
	translated = helps.ApplyPayloadConfigWithRoot(e.cfg, baseModel, to.String(), "", translated, originalTranslated, requestedModel)

	translated, err = thinking.ApplyThinking(translated, req.Model, from.String(), to.String(), e.Identifier())
	if err != nil {
		return nil, err
	}

	if compat := e.resolveCompatConfig(auth); compat != nil && compat.InjectPromptCache && !usesOpenAIAutoPromptCache(baseModel) {
		translated = injectPromptCache(translated)
	}
	if usesOpenAIAutoPromptCache(baseModel) {
		translated = stripPromptCacheControls(translated)
	}
	if compat := e.resolveCompatConfig(auth); compat != nil && compat.StripUnsupportedParams {
		translated = stripUnsupportedOpenAICompatParams(translated)
	}

	// Request usage data in the final streaming chunk so that token statistics
	// are captured even when the upstream is an OpenAI-compatible provider.
	if compat := e.resolveCompatConfig(auth); compat == nil || !compat.StripUnsupportedParams {
		translated, _ = sjson.SetBytes(translated, "stream_options.include_usage", true)
	}

	// DEBUG: dump translated request body for cache-stability analysis
	// Set CLIPROXY_REQUEST_DUMP_DIR to enable. Each call writes one file.
	if dumpDir := os.Getenv("CLIPROXY_REQUEST_DUMP_DIR"); dumpDir != "" {
		_ = os.MkdirAll(dumpDir, 0o755)
		fname := filepath.Join(dumpDir, time.Now().UTC().Format("20060102T150405.000000")+"-request.json")
		_ = os.WriteFile(fname, translated, 0o644)
	}

	url := strings.TrimSuffix(baseURL, "/") + "/chat/completions"
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(translated))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	if apiKey != "" {
		httpReq.Header.Set("Authorization", "Bearer "+apiKey)
	}
	httpReq.Header.Set("User-Agent", "cli-proxy-openai-compat")
	var attrs map[string]string
	if auth != nil {
		attrs = auth.Attributes
	}
	util.ApplyCustomHeadersFromAttrs(httpReq, attrs)
	httpReq.Header.Set("Accept", "text/event-stream")
	httpReq.Header.Set("Cache-Control", "no-cache")
	var authID, authLabel, authType, authValue string
	if auth != nil {
		authID = auth.ID
		authLabel = auth.Label
		authType, authValue = auth.AccountInfo()
	}
	helps.RecordAPIRequest(ctx, e.cfg, helps.UpstreamRequestLog{
		URL:       url,
		Method:    http.MethodPost,
		Headers:   httpReq.Header.Clone(),
		Body:      translated,
		Provider:  e.Identifier(),
		AuthID:    authID,
		AuthLabel: authLabel,
		AuthType:  authType,
		AuthValue: authValue,
	})

	httpClient := helps.NewProxyAwareHTTPClient(ctx, e.cfg, auth, 0)
	httpResp, err := httpClient.Do(httpReq)
	if err != nil {
		helps.RecordAPIResponseError(ctx, e.cfg, err)
		return nil, err
	}
	helps.RecordAPIResponseMetadata(ctx, e.cfg, httpResp.StatusCode, httpResp.Header.Clone())
	if httpResp.StatusCode < 200 || httpResp.StatusCode >= 300 {
		b, _ := io.ReadAll(httpResp.Body)
		helps.AppendAPIResponseChunk(ctx, e.cfg, b)
		helps.LogWithRequestID(ctx).Debugf("request error, error status: %d, error message: %s", httpResp.StatusCode, helps.SummarizeErrorBody(httpResp.Header.Get("Content-Type"), b))
		if errClose := httpResp.Body.Close(); errClose != nil {
			log.Errorf("openai compat executor: close response body error: %v", errClose)
		}
		err = statusErr{code: httpResp.StatusCode, msg: string(b)}
		return nil, err
	}
	out := make(chan cliproxyexecutor.StreamChunk)
	go func() {
		defer close(out)
		defer func() {
			if errClose := httpResp.Body.Close(); errClose != nil {
				log.Errorf("openai compat executor: close response body error: %v", errClose)
			}
		}()
		scanner := bufio.NewScanner(httpResp.Body)
		scanner.Buffer(nil, 52_428_800) // 50MB
		var param any
		// DEBUG: dump every raw chunk from upstream when env var set
		var dumpFile *os.File
		if dumpDir := os.Getenv("CLIPROXY_STREAM_DUMP_DIR"); dumpDir != "" {
			_ = os.MkdirAll(dumpDir, 0o755)
			fname := filepath.Join(dumpDir, time.Now().UTC().Format("20060102T150405.000000")+"-stream.log")
			if f, err := os.Create(fname); err == nil {
				dumpFile = f
				defer dumpFile.Close()
			}
		}
		for scanner.Scan() {
			line := scanner.Bytes()
			if dumpFile != nil {
				_, _ = dumpFile.Write(line)
				_, _ = dumpFile.Write([]byte("\n"))
			}
			helps.AppendAPIResponseChunk(ctx, e.cfg, line)
			if detail, ok := helps.ParseOpenAIStreamUsage(line); ok {
				reporter.Publish(ctx, detail)
			}
			if len(line) == 0 {
				continue
			}

			if !bytes.HasPrefix(line, []byte("data:")) {
				continue
			}

			// OpenAI-compatible streams are SSE: lines typically prefixed with "data: ".
			// Pass through translator; it yields one or more chunks for the target schema.
			chunks := sdktranslator.TranslateStream(ctx, to, from, req.Model, opts.OriginalRequest, translated, bytes.Clone(line), &param)
			for i := range chunks {
				out <- cliproxyexecutor.StreamChunk{Payload: chunks[i]}
			}
		}
		emitSyntheticDone := func() bool {
			chunks := sdktranslator.TranslateStream(ctx, to, from, req.Model, opts.OriginalRequest, translated, []byte("data: [DONE]"), &param)
			if len(chunks) == 0 {
				return false
			}
			for i := range chunks {
				out <- cliproxyexecutor.StreamChunk{Payload: chunks[i]}
			}
			return true
		}
		if errScan := scanner.Err(); errScan != nil {
			if !emitSyntheticDone() {
				helps.RecordAPIResponseError(ctx, e.cfg, errScan)
				reporter.PublishFailure(ctx)
				out <- cliproxyexecutor.StreamChunk{Err: errScan}
			}
		} else {
			// In case the upstream close the stream without a terminal [DONE] marker.
			// Feed a synthetic done marker through the translator so pending
			// response.completed events are still emitted exactly once.
			emitSyntheticDone()
		}
		// Ensure we record the request if no usage chunk was ever seen
		reporter.EnsurePublished(ctx)
	}()
	return &cliproxyexecutor.StreamResult{Headers: httpResp.Header.Clone(), Chunks: out}, nil
}

func (e *OpenAICompatExecutor) CountTokens(ctx context.Context, auth *cliproxyauth.Auth, req cliproxyexecutor.Request, opts cliproxyexecutor.Options) (cliproxyexecutor.Response, error) {
	baseModel := thinking.ParseSuffix(req.Model).ModelName

	from := opts.SourceFormat
	to := sdktranslator.FromString("openai")
	translated := sdktranslator.TranslateRequest(from, to, baseModel, req.Payload, false)

	modelForCounting := baseModel

	translated, err := thinking.ApplyThinking(translated, req.Model, from.String(), to.String(), e.Identifier())
	if err != nil {
		return cliproxyexecutor.Response{}, err
	}

	enc, err := helps.TokenizerForModel(modelForCounting)
	if err != nil {
		return cliproxyexecutor.Response{}, fmt.Errorf("openai compat executor: tokenizer init failed: %w", err)
	}

	count, err := helps.CountOpenAIChatTokens(enc, translated)
	if err != nil {
		return cliproxyexecutor.Response{}, fmt.Errorf("openai compat executor: token counting failed: %w", err)
	}

	usageJSON := helps.BuildOpenAIUsageJSON(count)
	translatedUsage := sdktranslator.TranslateTokenCount(ctx, to, from, count, usageJSON)
	return cliproxyexecutor.Response{Payload: translatedUsage}, nil
}

// Refresh is a no-op for API-key based compatibility providers.
func (e *OpenAICompatExecutor) Refresh(ctx context.Context, auth *cliproxyauth.Auth) (*cliproxyauth.Auth, error) {
	log.Debugf("openai compat executor: refresh called")
	_ = ctx
	return auth, nil
}

func (e *OpenAICompatExecutor) resolveCredentials(auth *cliproxyauth.Auth) (baseURL, apiKey string) {
	if auth == nil {
		return "", ""
	}
	if auth.Attributes != nil {
		baseURL = strings.TrimSpace(auth.Attributes["base_url"])
		apiKey = strings.TrimSpace(auth.Attributes["api_key"])
	}
	return
}

func (e *OpenAICompatExecutor) resolveCompatConfig(auth *cliproxyauth.Auth) *config.OpenAICompatibility {
	if auth == nil || e.cfg == nil {
		return nil
	}
	candidates := make([]string, 0, 3)
	if auth.Attributes != nil {
		if v := strings.TrimSpace(auth.Attributes["compat_name"]); v != "" {
			candidates = append(candidates, v)
		}
		if v := strings.TrimSpace(auth.Attributes["provider_key"]); v != "" {
			candidates = append(candidates, v)
		}
	}
	if v := strings.TrimSpace(auth.Provider); v != "" {
		candidates = append(candidates, v)
	}
	for i := range e.cfg.OpenAICompatibility {
		compat := &e.cfg.OpenAICompatibility[i]
		for _, candidate := range candidates {
			if candidate != "" && strings.EqualFold(strings.TrimSpace(candidate), compat.Name) {
				return compat
			}
		}
	}
	return nil
}

func (e *OpenAICompatExecutor) overrideModel(payload []byte, model string) []byte {
	if len(payload) == 0 || model == "" {
		return payload
	}
	payload, _ = sjson.SetBytes(payload, "model", model)
	return payload
}

func usesOpenAIAutoPromptCache(model string) bool {
	m := strings.ToLower(strings.TrimSpace(model))
	return strings.HasPrefix(m, "gpt-") || strings.HasPrefix(m, "o1") || strings.HasPrefix(m, "o3") || strings.HasPrefix(m, "o4")
}

func stripPromptCacheControls(translated []byte) []byte {
	messages := gjson.GetBytes(translated, "messages")
	if !messages.Exists() || !messages.IsArray() {
		return translated
	}
	out := translated
	messages.ForEach(func(msgKey, msg gjson.Result) bool {
		content := msg.Get("content")
		if !content.Exists() || !content.IsArray() {
			return true
		}
		content.ForEach(func(partKey, part gjson.Result) bool {
			if part.Get("cache_control").Exists() {
				path := fmt.Sprintf("messages.%s.content.%s.cache_control", msgKey.String(), partKey.String())
				out, _ = sjson.DeleteBytes(out, path)
			}
			return true
		})
		return true
	})
	return out
}

// injectPromptCache 在 chat/completions 请求中加两个 cache_control: ephemeral 断点：
//  1. 第一个 system message — 缓存系统指令（永远稳定）
//  2. messages 数组中**最后一个 user/tool message** — 让 cache 边界跟着对话滑动，
//     使下一轮请求里之前所有 turn 的 history 仍能命中缓存
//
// 仅 1 个断点（仅 system）时，cache hit 上限 ≈ system 占比（~58% on qwen3.6-plus）。
// 加了第 2 个断点后，cache hit 上限 ≈ 整轮 history 占比（80%+ on qwen3.6-plus）。
//
// Anthropic 协议允许最多 4 个 cache_control breakpoint。
func injectPromptCache(translated []byte) []byte {
	messages := gjson.GetBytes(translated, "messages")
	if !messages.Exists() || !messages.IsArray() {
		return translated
	}
	arr := messages.Array()

	// (1) 第一个 system message 上加 cache_control
	for i, msg := range arr {
		if msg.Get("role").String() != "system" {
			continue
		}
		content := msg.Get("content")
		var text string
		if content.Type == gjson.String {
			text = content.String()
		} else if content.IsArray() {
			content.ForEach(func(_, v gjson.Result) bool {
				if v.Get("type").String() == "text" {
					text = v.Get("text").String()
					return false
				}
				return true
			})
		}
		part := []byte(`{"type":"text","text":"","cache_control":{"type":"ephemeral"}}`)
		part, _ = sjson.SetBytes(part, "text", text)
		newMsg := []byte(`{"role":"system","content":[]}`)
		newMsg, _ = sjson.SetRawBytes(newMsg, "content.-1", part)
		translated, _ = sjson.SetRawBytes(translated, "messages."+fmt.Sprintf("%d", i), newMsg)
		break
	}

	// (2) 找到 messages 数组中最后一个 user/tool message，给它的最后一个 text part 加 cache_control
	// 这一步在 (1) 之后跑，因此操作的是已更新过的 translated。
	messages2 := gjson.GetBytes(translated, "messages")
	if !messages2.Exists() || !messages2.IsArray() {
		return translated
	}
	arr2 := messages2.Array()
	lastIdx := -1
	for i := len(arr2) - 1; i >= 0; i-- {
		role := arr2[i].Get("role").String()
		if role == "user" || role == "tool" {
			lastIdx = i
			break
		}
	}
	if lastIdx < 0 {
		return translated
	}
	if lastIdx == 0 {
		// 单条 user message 时，避免在 system 同位置重复打断点（实际上 lastIdx>=1 才有意义）
		return translated
	}
	// 跳过：如果这条 message 就在 system message 旁边（i<=1）也行，反正断点位置不冲突。
	target := arr2[lastIdx]
	role := target.Get("role").String()
	content := target.Get("content")

	// 把 content 规范化成 array 格式
	var parts []byte
	if content.Type == gjson.String {
		// string 形式 → 转成单元素数组并加 cache_control
		text := content.String()
		part := []byte(`{"type":"text","text":"","cache_control":{"type":"ephemeral"}}`)
		part, _ = sjson.SetBytes(part, "text", text)
		parts, _ = sjson.SetRawBytes([]byte(`[]`), "-1", part)
	} else if content.IsArray() {
		// 已经是数组：在最后一个 text part 上加 cache_control
		raw := []byte(content.Raw)
		// 找最后一个 type==text 的 part 索引
		arrParts := content.Array()
		lastTextIdx := -1
		for i := len(arrParts) - 1; i >= 0; i-- {
			if arrParts[i].Get("type").String() == "text" {
				lastTextIdx = i
				break
			}
		}
		if lastTextIdx < 0 {
			return translated // 没有 text part，跳过
		}
		raw, _ = sjson.SetRawBytes(raw, fmt.Sprintf("%d.cache_control", lastTextIdx), []byte(`{"type":"ephemeral"}`))
		parts = raw
	} else {
		return translated
	}

	newMsg := []byte(fmt.Sprintf(`{"role":%q,"content":[]}`, role))
	// preserve other fields (e.g. tool_call_id for tool messages)
	if id := target.Get("tool_call_id"); id.Exists() {
		newMsg, _ = sjson.SetBytes(newMsg, "tool_call_id", id.String())
	}
	newMsg, _ = sjson.SetRawBytes(newMsg, "content", parts)
	translated, _ = sjson.SetRawBytes(translated, fmt.Sprintf("messages.%d", lastIdx), newMsg)

	return translated
}

func stripUnsupportedOpenAICompatParams(translated []byte) []byte {
	out := translated
	out, _ = sjson.DeleteBytes(out, "reasoning_effort")
	out, _ = sjson.DeleteBytes(out, "parallel_tool_calls")
	out, _ = sjson.DeleteBytes(out, "stream_options")
	return out
}

type statusErr struct {
	code       int
	msg        string
	retryAfter *time.Duration
}

func (e statusErr) Error() string {
	if e.msg != "" {
		return e.msg
	}
	return fmt.Sprintf("status %d", e.code)
}
func (e statusErr) StatusCode() int            { return e.code }
func (e statusErr) RetryAfter() *time.Duration { return e.retryAfter }
