package helps

import (
	"testing"
	"time"

	"github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/usage"
)

func TestParseOpenAIUsageChatCompletions(t *testing.T) {
	data := []byte(`{"usage":{"prompt_tokens":1,"completion_tokens":2,"total_tokens":3,"prompt_tokens_details":{"cached_tokens":4},"completion_tokens_details":{"reasoning_tokens":5}}}`)
	detail := ParseOpenAIUsage(data)
	if detail.InputTokens != 1 {
		t.Fatalf("input tokens = %d, want %d", detail.InputTokens, 1)
	}
	if detail.OutputTokens != 2 {
		t.Fatalf("output tokens = %d, want %d", detail.OutputTokens, 2)
	}
	if detail.TotalTokens != 3 {
		t.Fatalf("total tokens = %d, want %d", detail.TotalTokens, 3)
	}
	if detail.CachedTokens != 4 {
		t.Fatalf("cached tokens = %d, want %d", detail.CachedTokens, 4)
	}
	if detail.ReasoningTokens != 5 {
		t.Fatalf("reasoning tokens = %d, want %d", detail.ReasoningTokens, 5)
	}
}

func TestParseOpenAIUsageNestedCachedTokenDetails(t *testing.T) {
	data := []byte(`{"usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12,"prompt_tokens_details":{"cached_tokens_details":{"read_tokens":7,"write_tokens":3}}}}`)
	detail := ParseOpenAIUsage(data)
	if detail.CachedTokens != 7 {
		t.Fatalf("cached tokens = %d, want %d", detail.CachedTokens, 7)
	}
	if detail.CacheReadInputTokens != 7 {
		t.Fatalf("cache read tokens = %d, want %d", detail.CacheReadInputTokens, 7)
	}
	if detail.CacheCreationInputTokens != 3 {
		t.Fatalf("cache creation tokens = %d, want %d", detail.CacheCreationInputTokens, 3)
	}

	line := []byte(`data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12,"prompt_tokens_details":{"cached_tokens_details":{"read_tokens":7,"write_tokens":3}}}}`)
	streamDetail, ok := ParseOpenAIStreamUsage(line)
	if !ok {
		t.Fatal("expected stream usage to parse")
	}
	if streamDetail.CachedTokens != 7 {
		t.Fatalf("stream cached tokens = %d, want %d", streamDetail.CachedTokens, 7)
	}
	if streamDetail.CacheReadInputTokens != 7 {
		t.Fatalf("stream cache read tokens = %d, want %d", streamDetail.CacheReadInputTokens, 7)
	}
	if streamDetail.CacheCreationInputTokens != 3 {
		t.Fatalf("stream cache creation tokens = %d, want %d", streamDetail.CacheCreationInputTokens, 3)
	}
}

func TestParseOpenAIUsageResponses(t *testing.T) {
	data := []byte(`{"usage":{"input_tokens":10,"output_tokens":20,"total_tokens":30,"input_tokens_details":{"cached_tokens":7},"output_tokens_details":{"reasoning_tokens":9}}}`)
	detail := ParseOpenAIUsage(data)
	if detail.InputTokens != 10 {
		t.Fatalf("input tokens = %d, want %d", detail.InputTokens, 10)
	}
	if detail.OutputTokens != 20 {
		t.Fatalf("output tokens = %d, want %d", detail.OutputTokens, 20)
	}
	if detail.TotalTokens != 30 {
		t.Fatalf("total tokens = %d, want %d", detail.TotalTokens, 30)
	}
	if detail.CachedTokens != 7 {
		t.Fatalf("cached tokens = %d, want %d", detail.CachedTokens, 7)
	}
	if detail.ReasoningTokens != 9 {
		t.Fatalf("reasoning tokens = %d, want %d", detail.ReasoningTokens, 9)
	}
}

func TestParseClaudeUsageSeparatesReadAndCreationTokens(t *testing.T) {
	data := []byte(`{"usage":{"input_tokens":13,"output_tokens":4,"cache_read_input_tokens":22000,"cache_creation_input_tokens":31}}`)
	detail := ParseClaudeUsage(data)
	if detail.CachedTokens != 22000 {
		t.Fatalf("cached tokens = %d, want %d", detail.CachedTokens, 22000)
	}
	if detail.CacheReadInputTokens != 22000 {
		t.Fatalf("cache read tokens = %d, want %d", detail.CacheReadInputTokens, 22000)
	}
	if detail.CacheCreationInputTokens != 31 {
		t.Fatalf("cache creation tokens = %d, want %d", detail.CacheCreationInputTokens, 31)
	}

	line := []byte(`data: {"usage":{"input_tokens":13,"output_tokens":4,"cache_read_input_tokens":22000,"cache_creation_input_tokens":31}}`)
	streamDetail, ok := ParseClaudeStreamUsage(line)
	if !ok {
		t.Fatal("expected Claude stream usage to parse")
	}
	if streamDetail.CachedTokens != 22000 {
		t.Fatalf("stream cached tokens = %d, want %d", streamDetail.CachedTokens, 22000)
	}
}

func TestUsageReporterBuildRecordIncludesLatency(t *testing.T) {
	reporter := &UsageReporter{
		provider:    "openai",
		model:       "gpt-5.4",
		requestedAt: time.Now().Add(-1500 * time.Millisecond),
	}

	record := reporter.buildRecord(usage.Detail{TotalTokens: 3}, false)
	if record.Latency < time.Second {
		t.Fatalf("latency = %v, want >= 1s", record.Latency)
	}
	if record.Latency > 3*time.Second {
		t.Fatalf("latency = %v, want <= 3s", record.Latency)
	}
}
