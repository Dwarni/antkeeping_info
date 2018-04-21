function initMap() {
    var uluru = {lat: 0, lng: 0};
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 1,
        center: uluru
    });
    var input = document.getElementById('id_address');
    var markers = [];
    var searchBox = new google.maps.places.SearchBox(input);
    // Listen for the event fired when the user selects a prediction and retrieve
    // more details for that place.
    searchBox.addListener('places_changed', function() {
        var places = searchBox.getPlaces();

        if (places.length == 0) {
            return;
        }

        // Clear out the old markers.
        markers.forEach(function(marker) {
            marker.setMap(null);
        });
        markers = [];

        // For each place, get the icon, name and location.
        var bounds = new google.maps.LatLngBounds();
        places.forEach(function(place) {
            if (!place.geometry) {
                console.log("Returned place contains no geometry");
                return;
            }
            var icon = {
                url: place.icon,
                size: new google.maps.Size(71, 71),
                origin: new google.maps.Point(0, 0),
                anchor: new google.maps.Point(17, 34),
                scaledSize: new google.maps.Size(25, 25)
            };

            // Create a marker for each place.
            markers.push(new google.maps.Marker({
                map: map,
                icon: icon,
                title: place.name,
                position: place.geometry.location
            }));

            if (place.geometry.viewport) {
                // Only geocodes have viewport.
                bounds.union(place.geometry.viewport);
            } else {
                bounds.extend(place.geometry.location);
            }
        });
        map.fitBounds(bounds);
    });  
}
$( document ).ready(function () {
    var temperatureField = $( '#id_temperature' );
    var temperatureUnitSelect = $( '#id_temperature_unit' );
    var temperature = undefined;
    var temperatureUnit = undefined;
    $('#flightForm').bind("keypress", function(e) {
        if (e.keyCode == 13) {
            return false;
        }
    });

    function initTemperatureField() {
        updateSavedTemperature();
        addTemperatureChangeListener();
        addTemperatureUnitChangeListener();
    }

    function addTemperatureUnitChangeListener() {
        temperatureUnitSelect.change(function() {
            var unit = $( this ).val();
            var newTemperature = null;

            if(unit === temperatureUnit) {
                temperatureField.val(temperature);
            } else if(unit === 'C') {
                newTemperature = Math.round((temperature - 32) * 5/9);
                temperatureField.val(newTemperature);
            } else {
                newTemperature = Math.round(temperature * 9/5 + 32);
                temperatureField.val(newTemperature)
            }
        });    
    }

    function addTemperatureChangeListener() {
        temperatureField.change(function() {
            updateSavedTemperature();
        });
    }

    function updateSavedTemperature() {
        var temperatureValue = temperatureField.val();
        var temperatureUnitValue = temperatureUnitSelect.val();
        temperature = temperatureValue;
        temperatureUnit = temperatureUnitValue;
    }

    //initTemperatureField();
});