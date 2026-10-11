// GeoWeb landing — Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
(function () {
  "use strict";

  // ---- theme (dark / light) ------------------------------------------------
  var THEME_KEY = "geoweb:theme";
  function preferredTheme() {
    var saved = null;
    try { saved = localStorage.getItem(THEME_KEY); } catch (e) {}
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  function paintTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.textContent = theme === "light" ? "☀️" : "🌙";
      btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
    }
  }
  paintTheme(preferredTheme());
  var themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      paintTheme(next);
      try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
    });
  }

  // ---- copy buttons on every code block ------------------------------------
  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
  }
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(function () { fallbackCopy(text); });
    }
    fallbackCopy(text);
    return Promise.resolve();
  }
  document.querySelectorAll("pre.term").forEach(function (pre) {
    var wrap = pre.parentElement;
    if (!wrap || !wrap.classList.contains("code")) {
      wrap = document.createElement("div");
      wrap.className = "code";
      pre.parentNode.insertBefore(wrap, pre);
      wrap.appendChild(pre);
    }
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "Copy";
    btn.setAttribute("aria-label", "Copy to clipboard");
    btn.addEventListener("click", function () {
      copyText(pre.textContent.replace(/\s+$/, ""));
      btn.classList.add("done");
      btn.textContent = "Copied ✓";
      setTimeout(function () {
        btn.classList.remove("done");
        btn.textContent = "Copy";
      }, 1600);
    });
    wrap.appendChild(btn);
  });

  // ---- MCP agent tabs ------------------------------------------------------
  var tabs = document.querySelectorAll(".agent-tab");
  var panes = document.querySelectorAll(".agent-pane");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      var agent = tab.getAttribute("data-agent");
      tabs.forEach(function (t) { t.classList.toggle("active", t === tab); });
      panes.forEach(function (p) { p.classList.toggle("active", p.getAttribute("data-agent") === agent); });
    });
  });

  // ---- reveal-on-scroll ----------------------------------------------------
  var targets = document.querySelectorAll("section .card, figure.shot, .steps li");
  if (!("IntersectionObserver" in window)) return;
  targets.forEach(function (el) {
    el.style.opacity = "0";
    el.style.transform = "translateY(10px)";
    el.style.transition = "opacity .5s ease, transform .5s ease";
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      e.target.style.opacity = "1";
      e.target.style.transform = "none";
      io.unobserve(e.target);
    });
  }, { rootMargin: "0px 0px -60px 0px", threshold: 0.05 });
  targets.forEach(function (el) { io.observe(el); });
})();
