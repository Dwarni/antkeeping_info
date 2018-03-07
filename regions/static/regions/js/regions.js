(function() {
    var countrySelect = $( "#countrySelect" );
    countrySelect.change(function() {
        var countryCode = countrySelect.val();
        var newUrl = countriesUrl;
        if(countryCode) {
            newUrl = newUrl + countryCode;
        }
        window.location.href = newUrl;
    })
})();