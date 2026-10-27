package ctl

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/nickglezakos/ppl-meta-platform/deployment/tray/internal/config"
)

const defaultHeadscaleURL = "https://vpn.eyenet-vision.com"

// Identity is what the tray shows beside platform status.
type Identity struct {
	Host      string
	Advertise string
	VPN       string
}

// Identity reads the host name, ADVERTISE_HOST, and the EyeNet mesh IPv4
// when this machine's tailscaled is logged into EyeNet Headscale.
func (c *Controller) Identity(ctx context.Context) Identity {
	id := Identity{Host: hostName()}
	if c == nil || c.Cfg == nil || strings.TrimSpace(c.Cfg.InstallDir) == "" {
		return id
	}
	env := c.readEnv()
	id.Advertise = advertiseHost(env["ADVERTISE_HOST"])
	vpnCtx, cancel := context.WithTimeout(ctx, 6*time.Second)
	defer cancel()
	id.VPN = c.eyeNetVPN(vpnCtx, env)
	return id
}

func hostName() string {
	name, err := os.Hostname()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(name)
}

func (c *Controller) readEnv() map[string]string {
	path := c.Cfg.EnvFile
	if path == "" || !filepath.IsAbs(path) {
		name := c.Cfg.EnvFile
		if name == "" {
			if c.Cfg.Mode == config.ModeWSL {
				name = ".env.windows"
			} else {
				name = ".env"
			}
		}
		path = filepath.Join(c.Cfg.InstallDir, name)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return map[string]string{}
	}
	return parseEnv(data)
}

func parseEnv(data []byte) map[string]string {
	data = bytesTrimBOM(data)
	out := map[string]string{}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(strings.TrimRight(line, "\r"))
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, val, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		key = strings.TrimSpace(key)
		val = strings.TrimSpace(val)
		if len(val) >= 2 {
			if (val[0] == '"' && val[len(val)-1] == '"') || (val[0] == '\'' && val[len(val)-1] == '\'') {
				val = val[1 : len(val)-1]
			}
		}
		out[key] = val
	}
	return out
}

func bytesTrimBOM(data []byte) []byte {
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		return data[3:]
	}
	return data
}

func advertiseHost(v string) string {
	v = strings.Trim(strings.TrimSpace(v), `"'`)
	host, port, ok := strings.Cut(v, ":")
	if !ok || strings.Contains(port, ":") {
		return v
	}
	if _, err := strconv.Atoi(port); err == nil {
		return host
	}
	return v
}

func (c *Controller) eyeNetVPN(ctx context.Context, env map[string]string) string {
	socket := env["EYENET_TS_SOCKET_HOST"]
	if socket == "" {
		socket = env["EYENET_TS_SOCKET"]
	}
	if socket == "" {
		socket = "/var/run/tailscale/tailscaled.sock"
	}
	statusOut, statusErr := c.runTailscale(ctx, socket, "status", "--json")
	status := parseJSONObject(statusOut)
	if status == nil && statusErr != nil {
		return ""
	}
	prefsOut, _ := c.runTailscale(ctx, socket, "debug", "prefs")
	prefs := parseJSONObject(prefsOut)
	expected := env["EYENET_HEADSCALE_URL"]
	if strings.TrimSpace(expected) == "" {
		expected = defaultHeadscaleURL
	}
	if !isEyeNetControl(controlURL(prefs, status), expected) {
		return ""
	}
	return firstIPv4(tailscaleIPs(status))
}

func (c *Controller) runTailscale(ctx context.Context, socket string, args ...string) (string, error) {
	full := append([]string{"--socket", socket}, args...)
	switch c.Cfg.Mode {
	case config.ModeWSL:
		wslArgs := append([]string{"-d", c.Cfg.WslDistro, "-u", "root", "--", "tailscale"}, full...)
		return c.run(ctx, "wsl", wslArgs...)
	default:
		out, err := c.run(ctx, "tailscale", full...)
		if err == nil {
			return out, nil
		}
		sudoArgs := append([]string{"-n", "tailscale"}, full...)
		out2, err2 := c.run(ctx, "sudo", sudoArgs...)
		if err2 != nil {
			return out + out2, err
		}
		return out2, nil
	}
}

func parseJSONObject(out string) map[string]any {
	raw := jsonObject(out)
	if raw == "" {
		return nil
	}
	var m map[string]any
	if err := json.Unmarshal([]byte(raw), &m); err != nil {
		return nil
	}
	return m
}

func jsonObject(out string) string {
	i := strings.Index(out, "{")
	j := strings.LastIndex(out, "}")
	if i >= 0 && j > i {
		return out[i : j+1]
	}
	return ""
}

func controlURL(prefs, status map[string]any) string {
	if u := stringField(prefs, "ControlURL", "controlURL"); u != "" {
		return strings.TrimRight(u, "/")
	}
	if u := stringField(status, "ControlURL"); u != "" {
		return strings.TrimRight(u, "/")
	}
	if tailnet, ok := status["CurrentTailnet"].(map[string]any); ok {
		combined := strings.ToLower(stringField(tailnet, "MagicDNSSuffix") + " " + stringField(tailnet, "Name"))
		if strings.Contains(combined, "eyenet") {
			return defaultHeadscaleURL
		}
	}
	self, _ := status["Self"].(map[string]any)
	blob := strings.ToLower(stringField(self, "DNSName") + " " + stringField(self, "HostName"))
	if strings.Contains(blob, "eyenet") {
		return defaultHeadscaleURL
	}
	return ""
}

func isEyeNetControl(actual, expected string) bool {
	actual = strings.TrimRight(strings.ToLower(strings.TrimSpace(actual)), "/")
	expected = strings.TrimRight(strings.ToLower(strings.TrimSpace(expected)), "/")
	if actual == "" {
		return false
	}
	if expected != "" && actual == expected {
		return true
	}
	return strings.Contains(actual, "vpn.eyenet-vision.com")
}

func tailscaleIPs(status map[string]any) []string {
	self, _ := status["Self"].(map[string]any)
	raw, _ := self["TailscaleIPs"].([]any)
	out := make([]string, 0, len(raw))
	for _, item := range raw {
		ip, _ := item.(string)
		ip = strings.TrimSpace(ip)
		if ip != "" {
			out = append(out, ip)
		}
	}
	return out
}

func firstIPv4(ips []string) string {
	for _, ip := range ips {
		if !strings.Contains(ip, ":") {
			return ip
		}
	}
	return ""
}

func stringField(m map[string]any, keys ...string) string {
	if m == nil {
		return ""
	}
	for _, key := range keys {
		v, _ := m[key].(string)
		v = strings.TrimSpace(v)
		if v != "" {
			return v
		}
	}
	return ""
}
