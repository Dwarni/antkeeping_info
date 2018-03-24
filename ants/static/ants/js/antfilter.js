$( document ).ready(function() {
    function addFilter(inputElement, tableElement, tableBodyElement, noSpeciesFoundWarning) {
        inputElement.on( "keyup", function() {
            var searchText = $( this ).val().toLowerCase();
            applyFilter(searchText, tableElement, tableBodyElement, noSpeciesFoundWarning);
        })
    }
    function applyFilter(searchText, tableElement, tableBodyElement, noSpeciesFoundWarning) {
        var visibleElements = 0;
        tableBodyElement.children().filter(function() {
            var currentText = $( this ).text().toLowerCase();
            var found = currentText.indexOf(searchText) > -1;
            $( this ).toggle(found);
            if(found) {
                visibleElements++;
            }
        })

        noSpeciesFoundWarning.toggle( visibleElements == 0 );
        tableElement.toggle( visibleElements > 0 );
    }

    var antSearchInput = $( "#antSearchInput" );
    var antTable = $( "#antTable" );
    var antTableBody = $( "#antTableBody" );
    var noSpeciesFoundWarning = $( "#noSpeciesFoundWarning" );
    addFilter(antSearchInput, antTable, antTableBody, noSpeciesFoundWarning);
});