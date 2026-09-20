package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// Mode selects how compose is invoked.
type Mode string

const (
	ModeWSL    Mode = "wsl"
	ModeNative Mode = "native"
)

// Config is written by installers; tray does not invent install paths.
type Config struct {
	InstallDir  string `json:"install_dir"`
	Mode        Mode   `json:"mode"`
	WslDistro   string `json:"wsl_distro"`
	Project     string `json:"project"`
	ComposeFile string `json:"compose_file"`
	EnvFile     string `json:"env_file"`
	UIURL       string `json:"ui_url"`
	Version     string `json:"version"`
	Reregister  string `json:"reregister_script,omitempty"`
}

func DefaultPath() string {
	if runtime.GOOS == "windows" {
		pd := os.Getenv("ProgramData")
		if pd == "" {
			pd = `C:\ProgramData`
		}
		return filepath.Join(pd, "EyeNet", "tray.json")
	}
	home, _ := os.UserHomeDir()
	candidates := []string{
		filepath.Join(home, "eyenet-platform", "tray", "tray.json"),
		filepath.Join(home, ".config", "eyenet", "tray.json"),
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	return candidates[0]
}

func Load(path string) (*Config, error) {
	if path == "" {
		path = DefaultPath()
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config %s: %w", path, err)
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse config %s: %w", path, err)
	}
	cfg.applyDefaults()
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func (c *Config) applyDefaults() {
	if c.Mode == "" {
		if runtime.GOOS == "windows" {
			c.Mode = ModeWSL
		} else {
			c.Mode = ModeNative
		}
	}
	if c.WslDistro == "" {
		c.WslDistro = "eyenet"
	}
	if c.Project == "" {
		c.Project = "pplmeta"
	}
	if c.UIURL == "" {
		c.UIURL = "http://127.0.0.1:3000"
	}
	if c.ComposeFile == "" {
		if c.Mode == ModeWSL {
			c.ComposeFile = "docker-compose.windows-installer.yml"
		} else {
			c.ComposeFile = "docker-compose.yml"
		}
	}
	if c.EnvFile == "" {
		if c.Mode == ModeWSL {
			c.EnvFile = ".env.windows"
		} else {
			c.EnvFile = ".env"
		}
	}
}

func (c *Config) Validate() error {
	if strings.TrimSpace(c.InstallDir) == "" {
		return fmt.Errorf("install_dir is required")
	}
	switch c.Mode {
	case ModeWSL, ModeNative:
	default:
		return fmt.Errorf("mode must be %q or %q", ModeWSL, ModeNative)
	}
	return nil
}

// Write writes cfg to path (used by installer helpers / tests).
func Write(path string, cfg *Config) error {
	cfg.applyDefaults()
	if err := cfg.Validate(); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0o644)
}
