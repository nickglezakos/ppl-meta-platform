package ctl

import "testing"

func TestParsePSText(t *testing.T) {
	cases := []struct {
		name string
		out  string
		want Status
	}{
		{"empty", "", StatusInactive},
		{"active", "NAME IMAGE STATUS\ngateway Up 2 minutes\nfrontend Up 2 minutes\n", StatusActive},
		{"degraded", "NAME IMAGE STATUS\ngateway Up 2 minutes\n", StatusDegraded},
		{"inactive", "NAME IMAGE STATUS\n", StatusInactive},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := parsePSText(tc.out); got != tc.want {
				t.Fatalf("got %s want %s", got, tc.want)
			}
		})
	}
}

func TestParsePSJSON(t *testing.T) {
	out := `{"Name":"pplmeta-gateway-1","Service":"gateway","State":"running"}
{"Name":"pplmeta-frontend-1","Service":"frontend","State":"running"}`
	if got := parsePSJSON(out); got != StatusActive {
		t.Fatalf("got %s", got)
	}
	if got := parsePSJSON(""); got != StatusInactive {
		t.Fatalf("got %s", got)
	}
}
