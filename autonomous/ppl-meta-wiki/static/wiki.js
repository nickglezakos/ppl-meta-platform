(function () {
  const body = document.body;
  const toggle = document.getElementById("sidebarToggle");
  const backdrop = document.getElementById("sidebarBackdrop");
  const searchInput = document.getElementById("wikiSearch");
  const nav = document.getElementById("sidebarNav");
  const empty = document.getElementById("searchEmpty");
  const hits = document.getElementById("searchHits");

  function setSidebarOpen(open) {
    body.classList.toggle("sidebar-open", open);
    if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  toggle?.addEventListener("click", () => {
    setSidebarOpen(!body.classList.contains("sidebar-open"));
  });
  backdrop?.addEventListener("click", () => setSidebarOpen(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setSidebarOpen(false);
  });

  const indexUrl = document.body.dataset.searchIndex;
  if (!searchInput || !indexUrl) return;

  let pages = [];
  let loaded = false;

  async function ensureIndex() {
    if (loaded) return pages;
    const response = await fetch(indexUrl);
    if (!response.ok) throw new Error("Search index unavailable");
    pages = await response.json();
    loaded = true;
    return pages;
  }

  function currentAudience() {
    return document.body.dataset.audience || "";
  }

  function filterNav(query) {
    if (!nav) return;
    const q = query.trim().toLowerCase();
    const groups = [...nav.querySelectorAll(".nav-group")];
    let visible = 0;

    if (groups.length) {
      for (const group of groups) {
        const parent = group.querySelector(".nav-group-link");
        const children = [...group.querySelectorAll(".nav-child")];
        const parentShow = !q || (parent?.dataset.title || "").toLowerCase().includes(q);
        let childVisible = 0;
        for (const link of children) {
          const show = !q || (link.dataset.title || "").toLowerCase().includes(q);
          link.classList.toggle("is-hidden", !show);
          if (show) childVisible += 1;
        }
        const groupShow = parentShow || childVisible > 0;
        group.classList.toggle("is-hidden", !groupShow);
        if (q && childVisible > 0) {
          group.classList.add("is-open");
          const toggle = group.querySelector(".nav-group-toggle");
          if (toggle) toggle.setAttribute("aria-expanded", "true");
        }
        if (groupShow) visible += 1 + childVisible;
      }
      const home = nav.querySelector('a[href="/"]');
      if (home) {
        const showHome = !q || (home.dataset.title || "").toLowerCase().includes(q);
        home.classList.toggle("is-hidden", !showHome);
        if (showHome) visible += 1;
      }
    } else {
      const links = [...nav.querySelectorAll("a[data-title]")];
      for (const link of links) {
        const title = (link.dataset.title || "").toLowerCase();
        const show = !q || title.includes(q);
        link.classList.toggle("is-hidden", !show);
        if (show) visible += 1;
      }
    }
    empty?.classList.toggle("is-visible", Boolean(q) && visible === 0 && (!hits || hits.childElementCount === 0));
  }

  nav?.addEventListener("click", (event) => {
    const toggle = event.target.closest(".nav-group-toggle");
    if (!toggle || !nav.contains(toggle)) return;
    const group = toggle.closest(".nav-group");
    if (!group) return;
    const open = !group.classList.contains("is-open");
    group.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  function renderHits(query, results) {
    if (!hits) return;
    hits.innerHTML = "";
    if (!query || results.length === 0) {
      hits.classList.remove("is-visible");
      return;
    }
    hits.classList.add("is-visible");
    const label = document.createElement("div");
    label.className = "sidebar-label";
    label.textContent = "Search results";
    hits.appendChild(label);
    for (const page of results.slice(0, 12)) {
      const a = document.createElement("a");
      a.className = "search-hit";
      a.href = page.url;
      a.innerHTML = `<strong>${escapeHtml(page.title)}</strong><span>${escapeHtml(page.section)} · ${escapeHtml(snippet(page.text, query))}</span>`;
      hits.appendChild(a);
    }
  }

  function snippet(text, query) {
    const lower = text.toLowerCase();
    const q = query.toLowerCase();
    const idx = lower.indexOf(q);
    if (idx < 0) return text.slice(0, 90);
    const start = Math.max(0, idx - 28);
    const end = Math.min(text.length, idx + q.length + 52);
    const prefix = start > 0 ? "…" : "";
    const suffix = end < text.length ? "…" : "";
    return prefix + text.slice(start, end).replace(/\s+/g, " ") + suffix;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  let timer = null;
  searchInput.addEventListener("input", () => {
    const query = searchInput.value;
    filterNav(query);
    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const all = await ensureIndex();
        const q = query.trim().toLowerCase();
        if (!q) {
          renderHits("", []);
          empty?.classList.remove("is-visible");
          return;
        }
        const audience = currentAudience();
        const results = all.filter((page) => {
          if (audience && page.sectionSlug !== audience && page.sectionSlug !== "home") {
            // Prefer current section, but still allow cross-site hits
          }
          const hay = `${page.title} ${page.text}`.toLowerCase();
          return hay.includes(q);
        });
        // Rank: current audience first, then title match, then others
        results.sort((a, b) => {
          const aScore =
            (audience && a.sectionSlug === audience ? 0 : 2) +
            (a.title.toLowerCase().includes(q) ? 0 : 1);
          const bScore =
            (audience && b.sectionSlug === audience ? 0 : 2) +
            (b.title.toLowerCase().includes(q) ? 0 : 1);
          return aScore - bScore;
        });
        renderHits(q, results);
        const navVisible = nav
          ? [...nav.querySelectorAll("a[data-title]:not(.is-hidden)")].length
          : 0;
        empty?.classList.toggle("is-visible", navVisible === 0 && results.length === 0);
      } catch (error) {
        console.warn(error);
      }
    }, 120);
  });
})();
