$( document ).ready(function() {
    function getNewUrl(url, code) {
        newUrl = url;
        if(code) {
            newUrl = newUrl + code;
        }

        return newUrl;
    }

    function addChangeListener(selectElement, url) {
        selectElement.change(function() {
            var code = selectElement.val();
            var newUrl = getNewUrl(url, code)  
            window.location.href = newUrl;
        });
    }
    $( ".region-select-div" ).each(function() {
        var currentSelect = $( this ).find( ".region-select" );
        var url = $( this ).find( ".region-url" ).val();
        addChangeListener(currentSelect, url);
    });
});