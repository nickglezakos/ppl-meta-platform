#!/bin/bash

# Generate local HTTPS certs for nginx LAN development.
# Prefers mkcert when available; falls back to OpenSSL self-signed cert.

set -euo pipefail

CERT_FILE="/tmp/ppl-meta-local-dev.crt"
KEY_FILE="/tmp/ppl-meta-local-dev.key"
META_FILE="/tmp/ppl-meta-local-dev-meta.env"

detect_lan_ip() {
    if [[ -n "${PPL_META_LAN_IP:-}" ]]; then
        echo "$PPL_META_LAN_IP"
        return
    fi

    local ip=""
    if [[ "$(uname -s)" == "Darwin" ]]; then
        local iface
        iface="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"
        if [[ -n "$iface" ]]; then
            ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
        fi
    else
        ip="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"
    fi

    if [[ -z "$ip" ]]; then
        ip="127.0.0.1"
    fi
    echo "$ip"
}

LAN_IP="$(detect_lan_ip)"
HOST_SHORT="$(hostname -s 2>/dev/null || hostname)"
HOST_LOCAL="${HOST_SHORT}.local"

mkdir -p "$(dirname "$CERT_FILE")"

if command -v mkcert >/dev/null 2>&1; then
    mkcert -install >/dev/null 2>&1 || true
    mkcert \
        -cert-file "$CERT_FILE" \
        -key-file "$KEY_FILE" \
        localhost 127.0.0.1 "$LAN_IP" "$HOST_SHORT" "$HOST_LOCAL"
    CERT_MODE="mkcert"
else
    TMP_OPENSSL_CONF="$(mktemp)"
    cat >"$TMP_OPENSSL_CONF" <<EOF
[req]
prompt = no
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = PPL Meta Local Dev

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = ${HOST_SHORT}
DNS.3 = ${HOST_LOCAL}
IP.1 = 127.0.0.1
IP.2 = ${LAN_IP}
EOF

    openssl req -x509 -nodes -newkey rsa:2048 -days 7 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -config "$TMP_OPENSSL_CONF" \
        -extensions v3_req >/dev/null 2>&1
    rm -f "$TMP_OPENSSL_CONF"
    CERT_MODE="openssl-self-signed"
fi

chmod 600 "$KEY_FILE"

cat >"$META_FILE" <<EOF
LAN_IP=${LAN_IP}
HOST_SHORT=${HOST_SHORT}
HOST_LOCAL=${HOST_LOCAL}
CERT_FILE=${CERT_FILE}
KEY_FILE=${KEY_FILE}
CERT_MODE=${CERT_MODE}
EOF

echo "LAN_IP=${LAN_IP}"
echo "HOST_LOCAL=${HOST_LOCAL}"
echo "CERT_MODE=${CERT_MODE}"
