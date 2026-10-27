package main

import "testing"

func TestStatusIconsEmbedded(t *testing.T) {
	for _, name := range []string{
		"assets/icon-active.png",
		"assets/icon-inactive.png",
		"assets/icon-degraded.png",
		"assets/icon-active.ico",
		"assets/icon-inactive.ico",
		"assets/icon-degraded.ico",
	} {
		b, err := assetFS.ReadFile(name)
		if err != nil {
			t.Fatalf("read %s: %v", name, err)
		}
		if len(b) < 8 {
			t.Fatalf("%s too small (%d bytes)", name, len(b))
		}
	}
}
