package ctl

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/nickglezakos/ppl-meta-platform/deployment/tray/internal/config"
)

// Status of the platform stack.
type Status string

const (
	StatusInactive Status = "inactive"
	StatusActive   Status = "active"
	StatusDegraded Status = "degraded"
)

// Controller runs compose lifecycle commands.
type Controller struct {
	Cfg *config.Config
}

func New(cfg *config.Config) *Controller {
	return &Controller{Cfg: cfg}
}

func (c *Controller) composeArgs(extra ...string) []string {
	args := []string{
		"compose",
		"--project-name", c.Cfg.Project,
		"--env-file", c.Cfg.EnvFile,
		"-f", c.Cfg.ComposeFile,
	}
	return append(args, extra...)
}

func (c *Controller) wslInstallPath() string {
	// C:\foo\bar -> /mnt/c/foo/bar
	p := filepath.Clean(c.Cfg.InstallDir)
	p = strings.ReplaceAll(p, `\`, `/`)
	if len(p) >= 2 && p[1] == ':' {
		drive := strings.ToLower(string(p[0]))
		return "/mnt/" + drive + p[2:]
	}
	return p
}

func (c *Controller) run(ctx context.Context, name string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Env = os.Environ()
	out, err := cmd.CombinedOutput()
	return string(out), err
}

func (c *Controller) runCompose(ctx context.Context, extra ...string) (string, error) {
	args := c.composeArgs(extra...)
	switch c.Cfg.Mode {
	case config.ModeWSL:
		wslPath := c.wslInstallPath()
		bash := fmt.Sprintf("cd %s && docker %s", shellQuote(wslPath), shellJoin(args))
		return c.run(ctx, "wsl", "-d", c.Cfg.WslDistro, "-u", "root", "--", "bash", "-lc", bash)
	default:
		cmd := exec.CommandContext(ctx, "docker", args...)
		cmd.Dir = c.Cfg.InstallDir
		cmd.Env = os.Environ()
		out, err := cmd.CombinedOutput()
		return string(out), err
	}
}

func shellQuote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func shellJoin(args []string) string {
	parts := make([]string, len(args))
	for i, a := range args {
		parts[i] = shellQuote(a)
	}
	return strings.Join(parts, " ")
}

func (c *Controller) ensureDocker(ctx context.Context) error {
	if c.Cfg.Mode != config.ModeWSL {
		return nil
	}
	_, _ = c.run(ctx, "wsl", "--set-default", c.Cfg.WslDistro)
	_, err := c.run(ctx, "wsl", "-d", c.Cfg.WslDistro, "-u", "root", "--", "systemctl", "start", "docker")
	return err
}

func (c *Controller) ensureKeepalive() {
	if c.Cfg.Mode != config.ModeWSL || runtime.GOOS != "windows" {
		return
	}
	// Detached WSL keepalive so the distro does not idle-exit.
	cmd := exec.Command("wsl", "-d", c.Cfg.WslDistro, "-u", "root", "--", "sleep", "infinity")
	cmd.Stdout = nil
	cmd.Stderr = nil
	_ = cmd.Start()
}

// Status reports Active / Inactive / Degraded.
func (c *Controller) Status(ctx context.Context) (Status, string, error) {
	out, err := c.runCompose(ctx, "ps", "--format", "json")
	if err != nil {
		// Fallback without --format for older compose
		out2, err2 := c.runCompose(ctx, "ps")
		if err2 != nil {
			return StatusInactive, strings.TrimSpace(out + out2), err2
		}
		return parsePSText(out2), strings.TrimSpace(out2), nil
	}
	st := parsePSJSON(out)
	return st, strings.TrimSpace(out), nil
}

func parsePSJSON(out string) Status {
	lines := strings.Split(out, "\n")
	running := 0
	total := 0
	hasGateway := false
	hasFrontend := false
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		total++
		low := strings.ToLower(line)
		if strings.Contains(low, `"state":"running"`) || strings.Contains(low, `"status":"running"`) ||
			strings.Contains(low, `"state":"running"`) {
			running++
		}
		// compose json may use Service / Name
		if strings.Contains(low, "gateway") && (strings.Contains(low, "running") || strings.Contains(low, "up")) {
			hasGateway = true
		}
		if strings.Contains(low, "frontend") && (strings.Contains(low, "running") || strings.Contains(low, "up")) {
			hasFrontend = true
		}
	}
	if total == 0 || running == 0 {
		return StatusInactive
	}
	if hasGateway && hasFrontend {
		return StatusActive
	}
	// Heuristic when service names missing from json: enough running containers
	if running >= 4 {
		return StatusActive
	}
	return StatusDegraded
}

func parsePSText(out string) Status {
	low := strings.ToLower(out)
	if !strings.Contains(low, "up ") && !strings.Contains(low, "running") {
		return StatusInactive
	}
	hasGW := strings.Contains(low, "gateway") && (strings.Contains(low, "up") || strings.Contains(low, "running"))
	hasFE := strings.Contains(low, "frontend") && (strings.Contains(low, "up") || strings.Contains(low, "running"))
	if hasGW && hasFE {
		return StatusActive
	}
	// count Up lines
	ups := 0
	for _, line := range strings.Split(out, "\n") {
		l := strings.ToLower(line)
		if strings.Contains(l, " up ") || strings.HasPrefix(strings.TrimSpace(l), "up") {
			ups++
		}
	}
	if ups == 0 {
		return StatusInactive
	}
	if ups >= 4 {
		return StatusActive
	}
	return StatusDegraded
}

func (c *Controller) Start(ctx context.Context) error {
	if err := c.ensureDocker(ctx); err != nil {
		return fmt.Errorf("start docker: %w", err)
	}
	c.ensureKeepalive()
	out, err := c.runCompose(ctx, "up", "-d")
	if err != nil {
		return fmt.Errorf("compose up: %w\n%s", err, out)
	}
	_ = c.Reregister(ctx)
	return nil
}

func (c *Controller) Stop(ctx context.Context) error {
	out, err := c.runCompose(ctx, "down")
	if err != nil {
		return fmt.Errorf("compose down: %w\n%s", err, out)
	}
	return nil
}

func (c *Controller) Restart(ctx context.Context) error {
	if err := c.Stop(ctx); err != nil {
		return err
	}
	return c.Start(ctx)
}

func (c *Controller) Reregister(ctx context.Context) error {
	script := c.Cfg.Reregister
	if script == "" {
		script = filepath.Join(c.Cfg.InstallDir, "reregister-discovery-services.sh")
	}
	switch c.Cfg.Mode {
	case config.ModeWSL:
		wslPath := c.wslInstallPath()
		rereg := wslPath + "/reregister-discovery-services.sh"
		bash := fmt.Sprintf("cd %s && test -f %s && bash %s || true", shellQuote(wslPath), shellQuote(rereg), shellQuote(rereg))
		_, err := c.run(ctx, "wsl", "-d", c.Cfg.WslDistro, "-u", "root", "--", "bash", "-lc", bash)
		return err
	default:
		if _, err := os.Stat(script); err != nil {
			return nil
		}
		cmd := exec.CommandContext(ctx, "bash", script)
		cmd.Dir = c.Cfg.InstallDir
		return cmd.Run()
	}
}

func (c *Controller) OpenUI() error {
	url := c.Cfg.UIURL
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("cmd", "/c", "start", "", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	return cmd.Start()
}

// ProbeUI returns true if the UI responds quickly.
func (c *Controller) ProbeUI(ctx context.Context) bool {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.Cfg.UIURL, nil)
	if err != nil {
		return false
	}
	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return false
	}
	_ = resp.Body.Close()
	return resp.StatusCode < 500
}
