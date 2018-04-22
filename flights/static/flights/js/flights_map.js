var map = null;
var markers = [];
var flights = [];
var infoWindow = null;
function initMap() {
    var initialPosition = {lat: 25, lng: 0};
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 2,
        center: initialPosition
    });

    // get flights list
    updateMap();
}

function updateMap() {
    // get flights list
    var mcOptions = {gridSize: 50, maxZoom: 12, imagePath: '/static/flights/img/vendor/markerclusterer/'};
    
    // Clear out the old markers.
    markers.forEach(function(marker) {
        marker.setMap(null);
    });
    markers = [];
    $.getJSON( "/flights/list", function(data) {
        var oms = new OverlappingMarkerSpiderfier(map, {
            markersWontMove: true,
            markersWontHide: true,
            basicFormatEvents: true,
            keepSpiderfied: true
        });
        

        for(var i = 0; i < data.length; i++) {
            var flight = data[i]
            flights.push(flight)
        // Create a marker for each place.
            var newMarker = new google.maps.Marker({
                map: map,
                title: flight.ant,
                position: {lat: flight.lat, lng: flight.lng}
            });
      
            markers.push(newMarker);
            newMarker.addListener('click', function() {
                var that = this;
                var markerIndex = markers.indexOf(this);
                $.get(flights[markerIndex].id + '/info-window', function(data) {
                    if(infoWindow) {
                        infoWindow.close();
                    }

                    infoWindow = new google.maps.InfoWindow({
                        content: data
                    });
                    infoWindow.open(map, that);
                })
            });
            
            oms.addMarker(newMarker);
        }

        var mc = new MarkerClusterer(map, markers, mcOptions);
    })
}