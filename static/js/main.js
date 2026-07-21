/*
 * main.js
 * Shared behaviour for public pages: nav scroll state, scroll-reveal
 * animations, and the mobile nav toggle. See docs/ui-ux-brief.md §9.
 */

document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector(".site-nav");
  if (nav) {
    const updateNavState = () => {
      nav.classList.toggle("is-scrolled", window.scrollY > 40);
    };
    updateNavState();
    window.addEventListener("scroll", updateNavState, { passive: true });
  }

  const revealTargets = document.querySelectorAll(".reveal");
  if (revealTargets.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealTargets.forEach((target) => observer.observe(target));
  }
});
