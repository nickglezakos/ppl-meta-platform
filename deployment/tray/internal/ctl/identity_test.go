package ctl

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/nickglezakos/ppl-meta-platform/deployment/tray/internal/config"
)

func TestParseEnvAdvertise(t *testing.T) {
	raw := []byte("\uFEFF# comment\r\nADVERTISE_HOST=\"192.168.9.13\"\r\nEYENET_HEADSCALE_URL=https://vpn.eyenet-vision.com\r\n")
	env := parseEnv(raw)
	if got := advertiseHost(env["ADVERTISE_HOST"]); got != "192.168.9.13" {
		t.Fatalf("advertise %q", got)
	}
	if env["EYENET_HEADSCALE_URL"] != "https://vpn.eyenet-vision.com" {
		t.Fatalf("headscale %q", env["EYENET_HEADSCALE_URL"])
	}
}

func TestAdvertiseHostStripsPort(t *testing.T) {
	if got := advertiseHost("10.1.2.3:3000"); got != "10.1.2.3" {
		t.Fatalf("got %q", got)
	}
}

func TestEyeNetIPv4OnlyWhenHeadscale(t *testing.T) {
	eyenet := map[string]any{
		"ControlURL": "https://vpn.eyenet-vision.com",
		"Self": map[string]any{
			"TailscaleIPs": []any{"100.64.0.24", "fd7a:115c:a1e0::1"},
		},
	}
	if !isEyeNetControl(controlURL(nil, eyenet), defaultHeadscaleURL) {
		t.Fatal("expected eyenet control")
	}
	if got := firstIPv4(tailscaleIPs(eyenet)); got != "100.64.0.24" {
		t.Fatalf("vpn %q", got)
	}

	foreign := map[string]any{
		"ControlURL": "https://controlplane.tailscale.com",
		"Self": map[string]any{
			"TailscaleIPs": []any{"100.101.128.40"},
		},
	}
	if isEyeNetControl(controlURL(nil, foreign), defaultHeadscaleURL) {
		t.Fatal("personal tailscale must not count as EyeNet VPN")
	}
}

func TestReadEnvFromInstallDir(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, ".env"), []byte("ADVERTISE_HOST=192.168.1.20\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	c := New(&config.Config{InstallDir: dir, Mode: config.ModeNative, EnvFile: ".env"})
	if got := c.readEnv()["ADVERTISE_HOST"]; got != "192.168.1.20" {
		t.Fatalf("got %q", got)
	}
}
