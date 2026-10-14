(function () {
  initScrollUp();
  activatePopovers();
  initNavbarSearchAutocomplete();

  function initScrollUp() {
    var btn = document.getElementById("return-to-top");
    if (!btn) return;
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

  function initNavbarSearchAutocomplete() {
    var input = document.getElementById("navbarSearchInput");
    var menu = document.getElementById("navbarAutocompleteMenu");
    if (!input || !menu) return;

    var debounceTimer = null;
    var currentQuery = "";
    var activeIndex = -1;
    var autocompleteUrl = menu.getAttribute("data-autocomplete-url") || "/search/autocomplete/";

    input.addEventListener("input", function () {
      var q = input.value.trim();
      if (q.length < 2) {
        hideMenu();
        return;
      }
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        fetchSuggestions(q);
      }, 200);
    });

    input.addEventListener("keydown", function (e) {
      if (!menu.classList.contains("show")) return;
      var items = menu.querySelectorAll(".autocomplete-item");
      if (!items.length) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIndex = (activeIndex + 1) % items.length;
        updateActiveItem(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIndex = (activeIndex - 1 + items.length) % items.length;
        updateActiveItem(items);
      } else if (e.key === "Enter" && activeIndex >= 0 && items[activeIndex]) {
        e.preventDefault();
        items[activeIndex].click();
      } else if (e.key === "Escape") {
        hideMenu();
      }
    });

    document.addEventListener("click", function (e) {
      if (!input.contains(e.target) && !menu.contains(e.target)) {
        hideMenu();
      }
    });

    function updateActiveItem(items) {
      items.forEach(function (el, idx) {
        el.classList.toggle("active", idx === activeIndex);
        if (idx === activeIndex) {
          el.scrollIntoView({ block: "nearest" });
        }
      });
    }

    function hideMenu() {
      menu.classList.remove("show");
      menu.innerHTML = "";
      activeIndex = -1;
    }

    function fetchSuggestions(query) {
      currentQuery = query;
      fetch(autocompleteUrl + "?q=" + encodeURIComponent(query))
        .then(function (res) {
          if (!res.ok) throw new Error("Search error");
          return res.json();
        })
        .then(function (data) {
          if (query !== currentQuery) return;
          renderSuggestions(data, query);
        })
        .catch(function () {
          hideMenu();
        });
    }

    function renderSuggestions(data, query) {
      if (!data || data.total === 0) {
        hideMenu();
        return;
      }

      var html = "";

      // Species
      if (data.species && data.species.length > 0) {
        html += '<div class="autocomplete-section-title"><i class="bi bi-bug me-1"></i>Arten</div>';
        data.species.forEach(function (s) {
          html += '<a href="' + s.url + '" class="autocomplete-item">' +
            '<i class="bi bi-bug text-primary fs-6"></i>' +
            '<div class="autocomplete-item-text">' +
              '<div class="autocomplete-item-title fst-italic">' + escapeHtml(s.title) + '</div>' +
              (s.subtitle ? '<div class="autocomplete-item-subtitle">' + escapeHtml(s.subtitle) + '</div>' : '') +
            '</div>' +
          '</a>';
        });
      }

      // Journals
      if (data.journals && data.journals.length > 0) {
        html += '<div class="autocomplete-section-title"><i class="bi bi-journal-bookmark me-1"></i>Haltungsberichte</div>';
        data.journals.forEach(function (j) {
          html += '<a href="' + j.url + '" class="autocomplete-item">' +
            '<i class="bi bi-journal-bookmark text-info fs-6"></i>' +
            '<div class="autocomplete-item-text">' +
              '<div class="autocomplete-item-title">' + escapeHtml(j.title) + '</div>' +
              '<div class="autocomplete-item-subtitle">' + escapeHtml(j.subtitle) + '</div>' +
            '</div>' +
          '</a>';
        });
      }

      // Food
      if (data.food && data.food.length > 0) {
        html += '<div class="autocomplete-section-title"><i class="bi bi-egg-fried me-1"></i>Futter-Datenbank</div>';
        data.food.forEach(function (f) {
          html += '<a href="' + f.url + '" class="autocomplete-item">' +
            '<i class="bi bi-egg-fried text-warning fs-6"></i>' +
            '<div class="autocomplete-item-text">' +
              '<div class="autocomplete-item-title">' + escapeHtml(f.title) + '</div>' +
              '<div class="autocomplete-item-subtitle">' + escapeHtml(f.subtitle) + '</div>' +
            '</div>' +
          '</a>';
        });
      }

      // Regions
      if (data.regions && data.regions.length > 0) {
        html += '<div class="autocomplete-section-title"><i class="bi bi-globe me-1"></i>Länder & Regionen</div>';
        data.regions.forEach(function (r) {
          html += '<a href="' + r.url + '" class="autocomplete-item">' +
            '<i class="bi bi-geo-alt text-primary fs-6"></i>' +
            '<div class="autocomplete-item-text">' +
              '<div class="autocomplete-item-title">' + escapeHtml(r.title) + '</div>' +
              (r.subtitle ? '<div class="autocomplete-item-subtitle">' + escapeHtml(r.subtitle) + '</div>' : '') +
            '</div>' +
          '</a>';
        });
      }

      // Footer
      html += '<div class="autocomplete-footer">' +
        '<a href="/search/?q=' + encodeURIComponent(query) + '" class="text-decoration-none d-block">' +
          'Alle Suchergebnisse anzeigen (' + data.total + ') →' +
        '</a>' +
      '</div>';

      menu.innerHTML = html;
      menu.classList.add("show");
      activeIndex = -1;
    }

    function escapeHtml(str) {
      if (!str) return "";
      var div = document.createElement("div");
      div.textContent = str;
      return div.innerHTML;
    }
  }
})();
