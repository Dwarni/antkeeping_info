$( document ).ready(function() {
    function addFilter(inputElement, listElement, noSpeciesFoundWarning) {
        inputElement.on( "keyup", function() {
            var searchText = $( this ).val().toLowerCase();
            applyFilter(searchText, listElement, noSpeciesFoundWarning);
        })
    }
    function applyFilter(searchText, listElement, noSpeciesFoundWarning) {
        var visibleElements = 0;
        listElement.children().filter(function() {
            var currentText = $( this ).text().toLowerCase();
            var found = currentText.indexOf(searchText) > -1;
            $( this ).toggle(found);
            if(found) {
                visibleElements++;
            }
        })

        noSpeciesFoundWarning.toggle( visibleElements == 0 );
    }

    var antSearchInput = $( "#antSearchInput" );
    var antList = $( "#antList" );
    var noSpeciesFoundWarning = $( "#noSpeciesFoundWarning" );
    addFilter(antSearchInput, antList, noSpeciesFoundWarning);
});