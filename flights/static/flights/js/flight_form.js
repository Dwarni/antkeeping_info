function initMap() {
    var uluru = {lat: 0, lng: 0};
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 1,
        center: uluru,
        mapTypeId: 'terrain'
    });
    var input = document.getElementById('id_address');
    var markers = [];
    var markerIcon = {
        url: '/static/flights/img/marker.png',
        anchor: new google.maps.Point(8, 8)
    };
    var searchBox = new google.maps.places.SearchBox(input);
    // Listen for the event fired when the user selects a prediction and retrieve
    // more details for that place.

    function clearMarkers() {
        // Clear out the old markers.
        markers.forEach(function(marker) {
            marker.setMap(null);
        });
        markers = [];
    }


    if (input.value) {
        getAndSetLatLong(input.value);
    }

    function getAndSetLatLong(address) {
        if(address) {
            address = address.replace(/\s/g, '+');
            var url = 'https://maps.googleapis.com/maps/api/geocode/json?address='+ address + '&key=' + apiKey;
            console.log(url);
            $.getJSON(url, function(data) {
                if (data.status === 'OK') {
                    addMarkers(data.results, false);
                    map.setCenter(data.results[0].geometry.location);
                    map.setZoom(10);
                }
            })
        }
    }

    function addMarkers(places, fitBounds) {
        if (places.length == 0) {
            return;
        }

        clearMarkers();

        // For each place, get the icon, name and location.
        var bounds = new google.maps.LatLngBounds();
        places.forEach(function(place) {
            if (!place.geometry) {
                console.log("Returned place contains no geometry");
                return;
            }

            // Create a marker for each place.
            markers.push(new google.maps.Marker({
                map: map,
                icon: markerIcon,
                title: place.name,
                position: place.geometry.location
            }));

            if (fitBounds) {
                if (place.geometry.viewport) {
                    // Only geocodes have viewport.
                    bounds.union(place.geometry.viewport);
                } else {
                    bounds.extend(place.geometry.location);
                }
            }
        });
        if (fitBounds) {
            map.fitBounds(bounds); 
        }
    }
    searchBox.addListener('places_changed', function() {
        var places = searchBox.getPlaces();
        addMarkers(places, true);
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