(function () {
  initScrollUp();
  activatePopovers();

  function initScrollUp() {
    var btn = document.getElementById("return-to-top");
    window.addEventListener("scroll", function () {
      btn.style.display = window.scrollY >= 250 ? "block" : "none";
    });
    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function activatePopovers() {
    document
      .querySelectorAll('[data-bs-toggle="popover"]')
      .forEach(function (el) {
        new bootstrap.Popover(el);
      });
  }
})();
