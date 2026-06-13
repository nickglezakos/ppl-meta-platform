{{flutter_js}}
{{flutter_build_config}}

(function () {
  const host = window.location.hostname;
  const secureByHost = host === "localhost" || host === "127.0.0.1";
  const secureContext = window.isSecureContext || secureByHost;

  const loadOptions = {
    // On insecure contexts (for example untrusted LAN HTTP/HTTPS), skip
    // service worker registration so the app can still boot.
    serviceWorkerSettings: secureContext
      ? { serviceWorkerVersion: {{flutter_service_worker_version}} }
      : null,
  };

  _flutter.loader.load(loadOptions);
})();
