package helps

import (
	"github.com/tidwall/gjson"
	"testing"
)

func TestCacheMissIsNotWriteOrHit(t *testing.T) {
	u := gjson.Parse(`{"prompt_tokens":1000,"prompt_cache_hit_tokens":800,"prompt_cache_miss_tokens":200}`)
	if got := parseOpenAICachedTokens(u); got != 800 {
		t.Fatalf("hit=%d, want 800", got)
	}
	if got := parseOpenAICacheCreationTokens(u); got != 0 {
		t.Fatalf("write=%d, want 0", got)
	}
}

func TestCacheWriteNotDiscounted(t *testing.T) {
	if got := combinedCachedInputTokens(800, 200); got != 800 {
		t.Fatalf("hit=%d", got)
	}
	u := gjson.Parse(`{"prompt_tokens_details":{"cached_tokens_details":{"read_tokens":0,"write_tokens":200}}}`)
	if got := parseOpenAICacheReadTokens(u); got != 0 {
		t.Fatalf("write treated as read: %d", got)
	}
}

func TestOpenAIUsagePreservesEvidenceAndNoDoubleReasoning(t *testing.T) {
	for _, data := range []string{
		`{"usage":{"prompt_tokens":1000,"completion_tokens":100,"completion_tokens_details":{"reasoning_tokens":60}}}`,
		`{"usage":{"prompt_tokens":1000,"completion_tokens":100,"completion_tokens_details":{"reasoning_tokens":60},"prompt_tokens_details":{"cached_tokens":0}}}`,
	} {
		d := ParseOpenAIUsage([]byte(data))
		if d.TotalTokens != 1100 {
			t.Fatalf("reasoning double counted: %d", d.TotalTokens)
		}
		if d.RawUsage == "" {
			t.Fatal("raw usage lost")
		}
		want := gjson.Get(data, "usage.prompt_tokens_details.cached_tokens").Exists()
		if d.CacheUsageReported != want {
			t.Fatal("missing confused with zero")
		}
	}
}
