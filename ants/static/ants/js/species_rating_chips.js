(function () {
    function addSpeciesChip(suffix, speciesId, speciesName) {
        var chips = document.getElementById('species-chips-' + suffix);
        if (!chips || chips.querySelector('[data-species-id="' + speciesId + '"]')) return;

        var chip = document.createElement('span');
        chip.className = 'badge bg-secondary d-inline-flex align-items-center gap-1 fw-normal';
        chip.setAttribute('data-species-id', speciesId);

        var label = document.createElement('em');
        label.textContent = speciesName;
        chip.appendChild(label);

        var removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn-close btn-close-white';
        removeBtn.style.fontSize = '0.5rem';
        removeBtn.setAttribute('aria-label', 'Remove');
        removeBtn.setAttribute('data-remove-species', '');
        chip.appendChild(removeBtn);

        var hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'species_id';
        hidden.value = speciesId;
        chip.appendChild(hidden);

        // Keep chips sorted alphabetically so it's easy to see which species are still missing.
        var existing = chips.querySelectorAll('[data-species-id]');
        var nextSibling = null;
        for (var i = 0; i < existing.length; i++) {
            var existingName = existing[i].querySelector('em').textContent;
            if (speciesName.localeCompare(existingName, undefined, { sensitivity: 'base' }) < 0) {
                nextSibling = existing[i];
                break;
            }
        }
        chips.insertBefore(chip, nextSibling);
    }

    document.addEventListener('click', function (e) {
        // Suggestion selected: add a chip, clear + refocus the search box, close dropdown
        var suggestBox = e.target.closest('[id^="species-suggest-"]');
        var suggestBtn = e.target.closest('[data-species-id]');
        if (suggestBox && suggestBtn) {
            var suffix = suggestBox.id.replace('species-suggest-', '');
            var search = document.getElementById('species-search-' + suffix);
            addSpeciesChip(suffix, suggestBtn.dataset.speciesId, suggestBtn.dataset.speciesName);
            if (search) { search.value = ''; search.focus(); }
            suggestBox.innerHTML = '';
            return;
        }
        // Chip removal
        var removeBtn = e.target.closest('[data-remove-species]');
        if (removeBtn) {
            var chip = removeBtn.closest('[data-species-id]');
            if (chip) chip.remove();
            return;
        }
        // Click outside: close all open suggestion dropdowns
        document.querySelectorAll('[id^="species-suggest-"]').forEach(function (box) {
            if (box.innerHTML && !box.contains(e.target)) {
                var suffix = box.id.replace('species-suggest-', '');
                var search = document.getElementById('species-search-' + suffix);
                if (e.target !== search) box.innerHTML = '';
            }
        });
    });

    // Require at least one species chip before letting a rating form submit.
    document.body.addEventListener('htmx:beforeRequest', function (e) {
        var form = e.detail.elt;
        if (!form.matches || !form.matches('[data-species-rating-form]')) return;
        var suffix = form.dataset.speciesSuffix;
        var chips = document.getElementById('species-chips-' + suffix);
        var hint = document.getElementById('species-required-hint-' + suffix);
        if (!chips || chips.children.length === 0) {
            e.preventDefault();
            if (hint) hint.classList.remove('d-none');
        } else if (hint) {
            hint.classList.add('d-none');
        }
    });
})();

// --- Star selector ---
(function () {
    var STAR_LABELS = {
        "1": "Ignored",
        "2": "Hardly interested",
        "3": "Moderately interested",
        "4": "Above average interest",
        "5": "Extremely interested (strong recruitment)"
    };

    function initStarSelector(sel) {
        if (sel.dataset.starSelectorInitialized) return;
        sel.dataset.starSelectorInitialized = "true";

        var labels = sel.querySelectorAll("label.star-select-label");
        var inputs = sel.querySelectorAll("input.star-radio");
        var hint = sel.querySelector(".star-hint");

        function paint(upTo) {
            labels.forEach(function (lbl, idx) {
                var icon = lbl.querySelector("i");
                if (idx < upTo) {
                    icon.className = "bi bi-star-fill text-warning";
                } else {
                    icon.className = "bi bi-star text-secondary";
                }
            });
        }

        function currentVal() {
            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].checked) return parseInt(inputs[i].value, 10);
            }
            return 0;
        }

        labels.forEach(function (lbl, idx) {
            lbl.addEventListener("mouseenter", function () {
                paint(idx + 1);
                if (hint) hint.textContent = STAR_LABELS[String(idx + 1)];
            });
            lbl.addEventListener("mouseleave", function () {
                var val = currentVal();
                paint(val);
                if (hint) hint.textContent = val ? STAR_LABELS[String(val)] : "";
            });
        });

        inputs.forEach(function (inp) {
            inp.addEventListener("change", function () {
                var val = parseInt(this.value, 10);
                paint(val);
                if (hint) hint.textContent = STAR_LABELS[String(val)];
            });
        });

        // Paint any pre-checked value (e.g. when the edit form loads pre-filled).
        paint(currentVal());
    }

    function initAllIn(root) {
        if (!root || !root.querySelectorAll) return;
        if (root.matches && root.matches('.star-selector')) initStarSelector(root);
        root.querySelectorAll('.star-selector').forEach(initStarSelector);
    }

    // Fires for the initial page content and again for every htmx-swapped-in fragment,
    // so the star selector keeps working after the create form re-renders or the edit
    // modal loads a fresh form.
    document.body.addEventListener('htmx:load', function (e) {
        initAllIn(e.target);
    });
    initAllIn(document.body);
})();
