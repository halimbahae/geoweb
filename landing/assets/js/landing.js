// GeoWeb landing — Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
// Tiny progressive enhancement: reveal-on-scroll for sections.
(function () {
  "use strict";
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
