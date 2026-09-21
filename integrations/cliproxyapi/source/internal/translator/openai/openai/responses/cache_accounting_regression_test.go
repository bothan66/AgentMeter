package responses

import (
	"context"
	"github.com/tidwall/gjson"
	"testing"
)

func TestCacheMissIsNotWriteOrHit(t *testing.T) {
	u := gjson.Parse(`{"prompt_tokens":1000,"prompt_cache_hit_tokens":800,"prompt_cache_miss_tokens":200}`)
	if got := parseOpenAIResponsesCachedTokens(u); got != 800 {
		t.Fatalf("hit=%d, want 800", got)
	}
	if got := parseOpenAIResponsesCacheCreationTokens(u); got != 0 {
		t.Fatalf("write=%d, want 0", got)
	}
}

func TestCachePresenceAndStreamAccounting(t *testing.T) {
	cases := []struct {
		name, usage string
		hit         int64
		reported    bool
	}{
		{"missing", `{"prompt_tokens":1000,"completion_tokens":20}`, 0, false},
		{"explicit_zero", `{"prompt_tokens":1000,"completion_tokens":20,"prompt_tokens_details":{"cached_tokens":0}}`, 0, true},
		{"deepseek_hit_miss", `{"prompt_tokens":1000,"completion_tokens":20,"prompt_cache_hit_tokens":800,"prompt_cache_miss_tokens":200}`, 800, true},
		{"read_write", `{"prompt_tokens":1000,"completion_tokens":20,"prompt_tokens_details":{"cached_tokens":800,"cache_creation_input_tokens":200}}`, 800, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			request := []byte(`{"model":"test"}`)
			lines := []string{
				`data: {"id":"test","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"OK"},"finish_reason":null}]}`,
				`data: {"id":"test","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":` + tc.usage + `}`,
				`data: [DONE]`,
			}
			var param any
			var completed gjson.Result
			for _, line := range lines {
				for _, chunk := range ConvertOpenAIChatCompletionsResponseToOpenAIResponses(context.Background(), "test", request, request, []byte(line), &param) {
					event, data := parseOpenAIResponsesSSEEvent(t, chunk)
					if event == "response.completed" {
						completed = data
					}
				}
			}
			if !completed.Exists() {
				t.Fatal("missing completion")
			}
			u := completed.Get("response.usage")
			if u.Get("input_tokens_details.cached_tokens").Int() != tc.hit {
				t.Fatalf("wrong cache: %s", u.Raw)
			}
			if u.Get("input_tokens_details.cache_usage_reported").Bool() != tc.reported {
				t.Fatalf("wrong presence: %s", u.Raw)
			}
			if u.Get("total_tokens").Int() != 1020 {
				t.Fatalf("wrong total: %s", u.Raw)
			}
		})
	}
}

func TestResponsesToolRoundTripInput(t *testing.T) {
	payload := []byte(`{"input":[{"role":"user","content":"read a.txt"},{"type":"function_call","call_id":"call_1","name":"read","arguments":"{\"path\":\"a.txt\"}"},{"type":"function_call_output","call_id":"call_1","output":"hello"}],"tools":[{"type":"function","name":"read","parameters":{"type":"object","properties":{"path":{"type":"string"}}}}],"max_output_tokens":1024}`)
	out := gjson.ParseBytes(ConvertOpenAIResponsesRequestToOpenAIChatCompletions("test", payload, true))
	if out.Get("messages.1.tool_calls.0.id").String() != "call_1" {
		t.Fatal(out.Raw)
	}
	if out.Get("messages.2.tool_call_id").String() != "call_1" {
		t.Fatal(out.Raw)
	}
	if out.Get("messages.2.content").String() != "hello" {
		t.Fatal(out.Raw)
	}
	if out.Get("tools.0.function.name").String() != "read" {
		t.Fatal(out.Raw)
	}
	if out.Get("max_tokens").Int() != 1024 {
		t.Fatal(out.Raw)
	}
}
