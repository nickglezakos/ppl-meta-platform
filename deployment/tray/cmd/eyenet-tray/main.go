package main

import (
	"context"
	"embed"
	"fmt"
	"log"
	"os"
	"runtime"
	"sync"
	"time"

	"github.com/getlantern/systray"
	"github.com/nickglezakos/ppl-meta-platform/deployment/tray/internal/config"
	"github.com/nickglezakos/ppl-meta-platform/deployment/tray/internal/ctl"
)

// Set via -ldflags "-X main.version=2.25.82"
var version = "dev"

//go:embed assets/*
var assetFS embed.FS

func main() {
	cfgPath := ""
	if len(os.Args) > 1 {
		cfgPath = os.Args[1]
	}
	cfg, err := config.Load(cfgPath)
	if err != nil {
		log.Printf("eyenet-tray: %v (looking for tray.json from installer)", err)
		cfg = &config.Config{
			InstallDir: "",
			Mode:       config.ModeNative,
			UIURL:      "http://127.0.0.1:3000",
			Version:    version,
		}
		if runtime.GOOS == "windows" {
			cfg.Mode = config.ModeWSL
		}
	}
	if cfg.Version == "" {
		cfg.Version = version
	}

	controller := ctl.New(cfg)
	app := &trayApp{ctl: controller, cfg: cfg}
	systray.Run(app.onReady, app.onExit)
}

type trayApp struct {
	ctl *ctl.Controller
	cfg *config.Config

	mu       sync.Mutex
	busy     bool
	mStatus  *systray.MenuItem
	mOpen    *systray.MenuItem
	mStart   *systray.MenuItem
	mStop    *systray.MenuItem
	mRestart *systray.MenuItem
	mQuit    *systray.MenuItem

	iconActive   []byte
	iconInactive []byte
	iconDegraded []byte
}

func (a *trayApp) onReady() {
	a.iconActive = mustAsset("icon-active")
	a.iconInactive = mustAsset("icon-inactive")
	a.iconDegraded = mustAsset("icon-degraded")

	systray.SetTitle("EyeNet")
	systray.SetTooltip(fmt.Sprintf("EyeNet %s — starting…", a.cfg.Version))
	systray.SetIcon(a.iconInactive)

	a.mStatus = systray.AddMenuItem("Status: …", "Platform status")
	a.mStatus.Disable()
	systray.AddSeparator()
	a.mOpen = systray.AddMenuItem("Open UI", "Open EyeNet web UI")
	a.mStart = systray.AddMenuItem("Start platform", "docker compose up -d")
	a.mStop = systray.AddMenuItem("Stop platform", "docker compose down")
	a.mRestart = systray.AddMenuItem("Restart platform", "down + up + reregister")
	systray.AddSeparator()
	a.mQuit = systray.AddMenuItem("Quit", "Exit EyeNet tray")

	go a.pollLoop()
	go a.menuLoop()
}

func (a *trayApp) onExit() {}

func (a *trayApp) menuLoop() {
	for {
		select {
		case <-a.mOpen.ClickedCh:
			_ = a.ctl.OpenUI()
		case <-a.mStart.ClickedCh:
			a.runAction("Starting…", func(ctx context.Context) error { return a.ctl.Start(ctx) })
		case <-a.mStop.ClickedCh:
			a.runAction("Stopping…", func(ctx context.Context) error { return a.ctl.Stop(ctx) })
		case <-a.mRestart.ClickedCh:
			a.runAction("Restarting…", func(ctx context.Context) error { return a.ctl.Restart(ctx) })
		case <-a.mQuit.ClickedCh:
			systray.Quit()
			return
		}
	}
}

func (a *trayApp) runAction(label string, fn func(context.Context) error) {
	a.mu.Lock()
	if a.busy {
		a.mu.Unlock()
		return
	}
	a.busy = true
	a.mu.Unlock()

	systray.SetTooltip(fmt.Sprintf("EyeNet %s — %s", a.cfg.Version, label))
	go func() {
		defer func() {
			a.mu.Lock()
			a.busy = false
			a.mu.Unlock()
			a.refreshStatus()
		}()
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
		defer cancel()
		if a.cfg.InstallDir == "" {
			log.Printf("eyenet-tray: no install_dir in config")
			return
		}
		if err := fn(ctx); err != nil {
			log.Printf("eyenet-tray: %v", err)
		}
	}()
}

func (a *trayApp) pollLoop() {
	a.refreshStatus()
	t := time.NewTicker(15 * time.Second)
	defer t.Stop()
	for range t.C {
		a.refreshStatus()
	}
}

func (a *trayApp) refreshStatus() {
	a.mu.Lock()
	busy := a.busy
	a.mu.Unlock()
	if busy {
		return
	}
	if a.cfg.InstallDir == "" {
		a.applyStatus(ctl.StatusInactive, "not configured")
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	st, _, err := a.ctl.Status(ctx)
	if err != nil {
		a.applyStatus(ctl.StatusInactive, "unreachable")
		return
	}
	a.applyStatus(st, string(st))
}

func (a *trayApp) applyStatus(st ctl.Status, _ string) {
	label := "Inactive"
	icon := a.iconInactive
	switch st {
	case ctl.StatusActive:
		label = "Active"
		icon = a.iconActive
	case ctl.StatusDegraded:
		label = "Degraded"
		icon = a.iconDegraded
	}
	systray.SetIcon(icon)
	systray.SetTooltip(fmt.Sprintf("EyeNet %s — %s", a.cfg.Version, label))
	a.mStatus.SetTitle(fmt.Sprintf("Status: %s", label))
}

func mustAsset(base string) []byte {
	ext := ".png"
	if runtime.GOOS == "windows" {
		ext = ".ico"
	}
	// embed path is relative to this file: ../../assets → stored as assets/...
	name := "assets/" + base + ext
	b, err := assetFS.ReadFile(name)
	if err == nil && len(b) > 0 {
		return b
	}
	// Fallback PNG
	return []byte{
		0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
		0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xde, 0x00, 0x00, 0x00,
		0x0c, 0x49, 0x44, 0x41, 0x54, 0x08, 0xd7, 0x63, 0xf8, 0xcf, 0xc0, 0x00,
		0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xfe, 0xd4, 0xef, 0x00, 0x00,
		0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
	}
}
