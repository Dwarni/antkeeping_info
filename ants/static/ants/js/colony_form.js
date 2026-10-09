(function () {
    // --- Species autocomplete (create mode only) ---
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('#species-suggestions [data-species-id]');
        if (btn) {
            var search = document.getElementById('species-search');
            var hidden = document.getElementById('id_species');
            if (search) search.value = btn.dataset.speciesName;
            if (hidden) hidden.value = btn.dataset.speciesId;
            var suggestions = document.getElementById('species-suggestions');
            if (suggestions) suggestions.innerHTML = '';
            return;
        }
        var suggestions = document.getElementById('species-suggestions');
        var search = document.getElementById('species-search');
        if (suggestions && suggestions.innerHTML &&
                !suggestions.contains(e.target) &&
                e.target !== search) {
            suggestions.innerHTML = '';
        }
    });

    document.addEventListener('input', function (e) {
        if (e.target && e.target.id === 'species-search') {
            var hidden = document.getElementById('id_species');
            if (hidden) hidden.value = '';
        }
    });
})();
