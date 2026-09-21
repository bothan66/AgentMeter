package executor

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/router-for-me/CLIProxyAPI/v6/internal/config"
	cliproxyauth "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/auth"
	cliproxyexecutor "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/executor"
	sdktranslator "github.com/router-for-me/CLIProxyAPI/v6/sdk/translator"
	"github.com/tidwall/gjson"
)

func TestOpenAICompatExecutorCompactPassthrough(t *testing.T) {
	var gotPath string
	var gotBody []byte
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		body, _ := io.ReadAll(r.Body)
		gotBody = body
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"resp_1","object":"response.compaction","usage":{"input_tokens":1,"output_tokens":2,"total_tokens":3}}`))
	}))
	defer server.Close()

	executor := NewOpenAICompatExecutor("openai-compatibility", &config.Config{})
	auth := &cliproxyauth.Auth{Attributes: map[string]string{
		"base_url": server.URL + "/v1",
		"api_key":  "test",
	}}
	payload := []byte(`{"model":"gpt-5.1-codex-max","input":[{"role":"user","content":"hi"}]}`)
	resp, err := executor.Execute(context.Background(), auth, cliproxyexecutor.Request{
		Model:   "gpt-5.1-codex-max",
		Payload: payload,
	}, cliproxyexecutor.Options{
		SourceFormat: sdktranslator.FromString("openai-response"),
		Alt:          "responses/compact",
		Stream:       false,
	})
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}
	if gotPath != "/v1/responses/compact" {
		t.Fatalf("path = %q, want %q", gotPath, "/v1/responses/compact")
	}
	if !gjson.GetBytes(gotBody, "input").Exists() {
		t.Fatalf("expected input in body")
	}
	if gjson.GetBytes(gotBody, "messages").Exists() {
		t.Fatalf("unexpected messages in body")
	}
	if string(resp.Payload) != `{"id":"resp_1","object":"response.compaction","usage":{"input_tokens":1,"output_tokens":2,"total_tokens":3}}` {
		t.Fatalf("payload = %s", string(resp.Payload))
	}
}

func TestStripUnsupportedOpenAICompatParamsPreservesPromptCache(t *testing.T) {
	input := []byte(`{
		"model":"gemini-3.5-flash",
		"reasoning_effort":"medium",
		"parallel_tool_calls":true,
		"stream_options":{"include_usage":true},
		"messages":[
			{"role":"system","content":[{"type":"text","text":"sys","cache_control":{"type":"ephemeral"}}]},
			{"role":"user","content":[{"type":"text","text":"hi","cache_control":{"type":"ephemeral"}}]}
		]
	}`)

	out := stripUnsupportedOpenAICompatParams(input)

	if gjson.GetBytes(out, "reasoning_effort").Exists() {
		t.Fatalf("reasoning_effort should be removed: %s", string(out))
	}
	if gjson.GetBytes(out, "parallel_tool_calls").Exists() {
		t.Fatalf("parallel_tool_calls should be removed: %s", string(out))
	}
	if gjson.GetBytes(out, "stream_options").Exists() {
		t.Fatalf("stream_options should be removed: %s", string(out))
	}
	if got := gjson.GetBytes(out, "messages.0.content.0.cache_control.type").String(); got != "ephemeral" {
		t.Fatalf("system cache_control = %q, want ephemeral: %s", got, string(out))
	}
	if got := gjson.GetBytes(out, "messages.1.content.0.cache_control.type").String(); got != "ephemeral" {
		t.Fatalf("user cache_control = %q, want ephemeral: %s", got, string(out))
	}
}
