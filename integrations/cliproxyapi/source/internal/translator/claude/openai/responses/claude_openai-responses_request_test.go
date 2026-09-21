package responses

import (
	"testing"

	"github.com/tidwall/gjson"
)

func TestConvertOpenAIResponsesRequestToClaude_SkipsUnnamedTools(t *testing.T) {
	inputJSON := []byte(`{
		"model": "claude-sonnet-4-6",
		"input": "hello",
		"tools": [
			{"type": "function", "name": "Bash", "description": "Run bash", "parameters": {"type": "object"}},
			{"type": "computer_use_preview"},
			{"type": "function", "name": "", "description": "bad", "parameters": {"type": "object"}}
		]
	}`)

	output := ConvertOpenAIResponsesRequestToClaude("claude-sonnet-4-6", inputJSON, true)

	tools := gjson.GetBytes(output, "tools").Array()
	if len(tools) != 1 {
		t.Fatalf("expected 1 translated tool, got %d: %s", len(tools), string(output))
	}
	if got := tools[0].Get("name").String(); got != "Bash" {
		t.Fatalf("tools[0].name = %q, want %q: %s", got, "Bash", string(output))
	}
}

func TestConvertOpenAIResponsesRequestToClaude_SkipsEmptyFunctionToolChoice(t *testing.T) {
	inputJSON := []byte(`{
		"model": "claude-sonnet-4-6",
		"input": "hello",
		"tool_choice": {
			"type": "function",
			"function": {
				"name": ""
			}
		}
	}`)

	output := ConvertOpenAIResponsesRequestToClaude("claude-sonnet-4-6", inputJSON, true)

	if choice := gjson.GetBytes(output, "tool_choice"); choice.Exists() {
		t.Fatalf("expected tool_choice to be omitted, got %s", choice.Raw)
	}
}
