package cliproxy

import (
	"testing"

	"github.com/router-for-me/CLIProxyAPI/v6/internal/config"
)

func TestBuildCodexConfigModelsMarksModelsAsCodex(t *testing.T) {
	models := buildCodexConfigModels(&config.CodexKey{
		Models: []config.CodexModel{{Name: "gpt-5.3-codex"}},
	})

	if len(models) != 1 {
		t.Fatalf("buildCodexConfigModels() returned %d models, want 1", len(models))
	}
	if models[0].ID != "gpt-5.3-codex" {
		t.Fatalf("model ID = %q, want %q", models[0].ID, "gpt-5.3-codex")
	}
	if models[0].OwnedBy != "openai" {
		t.Fatalf("model OwnedBy = %q, want %q", models[0].OwnedBy, "openai")
	}
	if models[0].Type != "codex" {
		t.Fatalf("model Type = %q, want %q", models[0].Type, "codex")
	}
}
