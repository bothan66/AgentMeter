package responses

import (
	"context"
	"strings"
	"testing"

	"github.com/tidwall/gjson"
)

func TestConvertClaudeResponseToOpenAIResponses_PropagatesCacheUsage(t *testing.T) {
	var state any
	events := [][]byte{
		[]byte(`data: {"type":"message_start","message":{"id":"msg_123","usage":{"input_tokens":10,"cache_read_input_tokens":120,"cache_creation_input_tokens":30}}}`),
		[]byte(`data: {"type":"message_delta","usage":{"output_tokens":7}}`),
		[]byte(`data: {"type":"message_stop"}`),
	}

	var completed gjson.Result
	for _, event := range events {
		out := ConvertClaudeResponseToOpenAIResponses(context.Background(), "claude-sonnet-4-6", nil, nil, event, &state)
		for _, chunk := range out {
			data := parseSSEData(chunk)
			if data.Get("response.usage").Exists() {
				completed = data
			}
		}
	}

	if got := completed.Get("response.usage.input_tokens").Int(); got != 10 {
		t.Fatalf("input_tokens = %d, want 10; payload=%s", got, completed.Raw)
	}
	if got := completed.Get("response.usage.input_tokens_details.cached_tokens").Int(); got != 150 {
		t.Fatalf("cached_tokens = %d, want 150; payload=%s", got, completed.Raw)
	}
	if got := completed.Get("response.usage.input_tokens_details.cache_read_input_tokens").Int(); got != 120 {
		t.Fatalf("cache_read_input_tokens = %d, want 120; payload=%s", got, completed.Raw)
	}
	if got := completed.Get("response.usage.input_tokens_details.cache_creation_input_tokens").Int(); got != 30 {
		t.Fatalf("cache_creation_input_tokens = %d, want 30; payload=%s", got, completed.Raw)
	}
	if got := completed.Get("response.usage.output_tokens").Int(); got != 7 {
		t.Fatalf("output_tokens = %d, want 7; payload=%s", got, completed.Raw)
	}
}

func parseSSEData(chunk []byte) gjson.Result {
	for _, line := range strings.Split(string(chunk), "\n") {
		if strings.HasPrefix(line, "data: ") {
			return gjson.Parse(line[len("data: "):])
		}
	}
	return gjson.Result{}
}

func TestConvertClaudeResponseToOpenAIResponsesNonStream_PropagatesCacheUsage(t *testing.T) {
	raw := []byte(
		"data: " + `{"type":"message_start","message":{"id":"msg_123","usage":{"input_tokens":10,"cache_read_input_tokens":120,"cache_creation_input_tokens":30}}}` + "\n" +
			"data: " + `{"type":"message_delta","usage":{"output_tokens":7}}` + "\n" +
			"data: " + `{"type":"message_stop"}` + "\n",
	)

	out := ConvertClaudeResponseToOpenAIResponsesNonStream(context.Background(), "claude-sonnet-4-6", nil, nil, raw, nil)
	data := gjson.ParseBytes(out)

	if got := data.Get("usage.input_tokens").Int(); got != 10 {
		t.Fatalf("input_tokens = %d, want 10; payload=%s", got, string(out))
	}
	if got := data.Get("usage.input_tokens_details.cached_tokens").Int(); got != 150 {
		t.Fatalf("cached_tokens = %d, want 150; payload=%s", got, string(out))
	}
	if got := data.Get("usage.input_tokens_details.cache_read_input_tokens").Int(); got != 120 {
		t.Fatalf("cache_read_input_tokens = %d, want 120; payload=%s", got, string(out))
	}
	if got := data.Get("usage.input_tokens_details.cache_creation_input_tokens").Int(); got != 30 {
		t.Fatalf("cache_creation_input_tokens = %d, want 30; payload=%s", got, string(out))
	}
	if got := data.Get("usage.output_tokens").Int(); got != 7 {
		t.Fatalf("output_tokens = %d, want 7; payload=%s", got, string(out))
	}
}
