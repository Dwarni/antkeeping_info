(function () {
    function selectSpecies(suffix, speciesId, speciesName) {
        var hidden = document.getElementById('species-id-' + suffix);
        var search = document.getElementById('species-search-' + suffix);
        if (hidden) hidden.value = speciesId;
        if (search) search.value = speciesName;
    }

    document.addEventListener('click', function (e) {
        // Suggestion selected: apply it, close the dropdown
        var suggestBox = e.target.closest('[id^="species-suggest-"]');
        var suggestBtn = e.target.closest('[data-species-id]');
        if (suggestBox && suggestBtn) {
            var suffix = suggestBox.id.replace('species-suggest-', '');
            selectSpecies(suffix, suggestBtn.dataset.speciesId, suggestBtn.dataset.speciesName);
            suggestBox.innerHTML = '';
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

    // Typing in the species search box invalidates the previously picked
    // species, forcing re-selection from the dropdown before the form can submit.
    document.addEventListener('input', function (e) {
        if (!e.target.id || e.target.id.indexOf('species-search-') !== 0) return;
        var suffix = e.target.id.replace('species-search-', '');
        var hidden = document.getElementById('species-id-' + suffix);
        if (hidden) hidden.value = '';
    });

    // Require a species to be picked before letting a vote form submit.
    document.body.addEventListener('htmx:beforeRequest', function (e) {
        var form = e.detail.elt;
        if (!form.matches || !form.matches('[data-species-vote-form]')) return;
        var suffix = form.dataset.speciesSuffix;
        var hint = document.getElementById('species-required-hint-' + suffix);
        var hidden = document.getElementById('species-id-' + suffix);
        var hasSpecies = !!(hidden && hidden.value);
        if (!hasSpecies) {
            e.preventDefault();
            if (hint) hint.classList.remove('d-none');
        } else if (hint) {
            hint.classList.add('d-none');
        }
    });
})();
