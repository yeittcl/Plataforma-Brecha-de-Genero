(function () {
  "use strict";

  document.documentElement.classList.add("scroll-anim");

  var revealTargets = document.querySelectorAll(".reveal");

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );
    revealTargets.forEach(function (el) {
      observer.observe(el);
    });
  } else {
    revealTargets.forEach(function (el) {
      el.classList.add("in");
    });
  }

  var toTop = document.getElementById("toTop");
  if (toTop) {
    var shown = false;
    function onScroll() {
      var past = window.scrollY > 200;
      if (past !== shown) {
        shown = past;
        toTop.classList.toggle("show", shown);
      }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    toTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
})();