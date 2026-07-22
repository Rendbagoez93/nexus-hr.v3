/*
 * dashboard.js
 * Behaviour for the authenticated dashboard shell:
 *   - sidebar collapse toggle (persists to localStorage)
 *   - mobile menu toggle
 *   - tab switching with URL hash sync and WAI-ARIA contract
 *   - scroll-reveal for stat cards and dashboard cards
 *
 * Vanilla JS, no dependencies. Follows docs/ui-ux-brief.md §9 motion rules.
 */

(function () {
  "use strict";

  const SHELL = document.querySelector(".app-shell");
  const SIDEBAR = document.getElementById("sidebar");
  const SIDEBAR_TOGGLE = document.getElementById("sidebar-toggle");
  const TOPBAR_MENU = document.getElementById("topbar-menu");
  const TAB_BUTTONS = Array.from(document.querySelectorAll(".tab-btn"));
  const TAB_PANELS = Array.from(document.querySelectorAll(".tab-panel"));

  /* ── Sidebar collapse ────────────────────────────────────────────────── */
  const SIDEBAR_KEY = "nexus.sidebarCollapsed";

  function readSidebarState() {
    try {
      return localStorage.getItem(SIDEBAR_KEY) === "true";
    } catch (e) {
      return false;
    }
  }

  function writeSidebarState(collapsed) {
    try {
      localStorage.setItem(SIDEBAR_KEY, collapsed ? "true" : "false");
    } catch (e) {
      /* localStorage may be unavailable; fail silently. */
    }
  }

  function applySidebarState(collapsed) {
    if (!SHELL) return;
    SHELL.classList.toggle("is-sidebar-collapsed", collapsed);
    if (SIDEBAR_TOGGLE) {
      SIDEBAR_TOGGLE.setAttribute("aria-expanded", collapsed ? "false" : "true");
      SIDEBAR_TOGGLE.setAttribute(
        "aria-label",
        collapsed ? "Expand sidebar" : "Collapse sidebar"
      );
    }
  }

  function toggleSidebar() {
    if (!SHELL) return;
    const nextCollapsed = !SHELL.classList.contains("is-sidebar-collapsed");
    applySidebarState(nextCollapsed);
    writeSidebarState(nextCollapsed);
  }

  applySidebarState(readSidebarState());

  if (SIDEBAR_TOGGLE) {
    SIDEBAR_TOGGLE.addEventListener("click", toggleSidebar);
  }

  if (TOPBAR_MENU) {
    TOPBAR_MENU.addEventListener("click", toggleSidebar);
  }

  /* ── Tab switching ───────────────────────────────────────────────────── */
  function activateTab(tabId) {
    if (!tabId) return;

    let matchedPanel = null;
    let matchedButton = null;

    TAB_BUTTONS.forEach((btn) => {
      const isMatch = btn.dataset.tabId === tabId;
      btn.classList.toggle("is-active", isMatch);
      btn.setAttribute("aria-selected", isMatch ? "true" : "false");
      btn.tabIndex = isMatch ? 0 : -1;
      if (isMatch) matchedButton = btn;
    });

    TAB_PANELS.forEach((panel) => {
      const isMatch = panel.id === tabId;
      panel.classList.toggle("is-active", isMatch);
      if (isMatch) {
        panel.removeAttribute("hidden");
        matchedPanel = panel;
      } else {
        panel.setAttribute("hidden", "");
      }
    });

    /* Sync sidebar link active state */
    document.querySelectorAll(".sidebar-link[data-tab-target]").forEach((link) => {
      const isMatch = link.dataset.tabTarget === tabId;
      link.classList.toggle("is-active", isMatch);
    });

    /* Sync URL hash without scrolling */
    if (window.history && window.history.replaceState) {
      const newHash = "#" + tabId;
      if (window.location.hash !== newHash) {
        window.history.replaceState(null, "", newHash);
      }
    }

    if (matchedButton) matchedButton.focus({ preventScroll: true });
    if (matchedPanel) matchedPanel.scrollIntoView({ block: "nearest" });
  }

  TAB_BUTTONS.forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      activateTab(btn.dataset.tabId);
    });
  });

  document.querySelectorAll(".sidebar-link[data-tab-target]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      activateTab(link.dataset.tabTarget);
    });
  });

  /* Initialise from URL hash if present, else default to Overview. */
  const initialTab =
    window.location.hash && window.location.hash.startsWith("#tab-")
      ? window.location.hash.slice(1)
      : "tab-overview";

  activateTab(initialTab);

  /* ── Scroll reveal ───────────────────────────────────────────────────── */
  const revealTargets = document.querySelectorAll(".reveal");
  if (revealTargets.length && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    revealTargets.forEach((target) => observer.observe(target));
  }
})();