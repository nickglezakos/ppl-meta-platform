package config_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/nickglezakos/ppl-meta-platform/deployment/tray/internal/config"
)

func TestWriteLoadRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "tray.json")
	cfg := &config.Config{
		InstallDir:  "/home/user/eyenet-platform",
		Mode:        config.ModeNative,
		Project:     "pplmeta",
		ComposeFile: "docker-compose.yml",
		EnvFile:     ".env",
		UIURL:       "http://127.0.0.1:3000",
		Version:     "2.25.82",
	}
	if err := config.Write(path, cfg); err != nil {
		t.Fatal(err)
	}
	got, err := config.Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if got.InstallDir != cfg.InstallDir || got.Mode != config.ModeNative {
		t.Fatalf("got %+v", got)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatal(err)
	}
}
