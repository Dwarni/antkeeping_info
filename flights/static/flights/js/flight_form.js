(function () {
    const BING_API_KEY = document.currentScript.getAttribute('BingApiKey');
    class Map {
        constructor(mapDivId, minZoom, maxZoom, tileUrl, osmAttrib) {
            this._bingApiKey = BING_API_KEY
            this.map = L.map(mapDivId)
                .setView([51.505, -0.09], 2)

            this.initBingLayer()

            this.marker = null
        }

        initBingLayer() {
            const options = {
                bingMapsKey: this._bingApiKey,
                imagerySet: 'Road',
            }
            L.tileLayer.bing(options).addTo(this.map)
        }

        addMarker(lat, lng) {
            if(this.marker) {
                this.map.removeLayer(this.marker)
            }
    
            this.marker = L.marker([lat, lng]).addTo(this.map)
            this.map.setView(this.marker.getLatLng(), 14);
        }
    }

    class FlightFormApp {
        constructor() {
            const tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
            // const tileUrl = 'https://{s}.tile.openstreetmap.de/tiles/osmde/{z}/{x}/{y}.png'
            const osmAttrib = 'Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors';
            const minZoom = 2
            const maxZoom = 17

            const getCurrentLocationButtonId = 'getCurrentLocationButton'
            const locationRadioId = 'id_id_location_type_0_1'
            const gpsCoordinatesRadioId = 'id_id_location_type_0_2'
            
            const addressContainerId = 'addressContainer'
            const addressInputId = 'id_address'
            
            const gpsContainerId = 'gpsContainer'
            const latInputId = 'id_latitude'
            const lngInputId = 'id_longitude'

            const formId = 'flightForm'

            this.map = new Map('map', minZoom, maxZoom, tileUrl, osmAttrib)
            
            this.disableFormDefaultAction(formId)
            
            this.initGetCurrentLocationButton(getCurrentLocationButtonId)
            this.initAddressInput(addressInputId)
            this.initLocationDivs(addressContainerId, gpsContainerId)
            this.initLocationTypeRadios(locationRadioId, gpsCoordinatesRadioId)
            this.initLatLongInput(latInputId, lngInputId)
        }

        formatAddress(address) {

        }

        initGetCurrentLocationButton(getCurrentLocationButtonId) {
            this.getCurrentLocationButton = document.getElementById(getCurrentLocationButtonId)
            this.getCurrentLocationButton.onclick = e => {
                this.getAndSetCurrentLocation()
            }
        }

        initAddressInput(addressInputId) {
            this.addressInput = document.getElementById(addressInputId)
            const handleLocationInput = (location) => { this.getAndSetLatLong(location) }
            this.addressInput.onchange = e => {
                handleLocationInput(e.target.value)
            }

            this.addressInput.onkeypress = e => {
                if (e.keyCode === 13) {
                    handleLocationInput(e.target.value)
                }
            }
        }

        initLocationDivs(addressContainerId, gpsContainerId) {
            this.addressContainer = document.getElementById(addressContainerId)
            this.gpsContainer = document.getElementById(gpsContainerId)
        }

        initLocationTypeRadios(locationRadioId, gpsCoordinatesRadioId) {
            this.locationRadio = document.getElementById(locationRadioId)
            this.gpsCoordinatesRadio = document.getElementById(gpsCoordinatesRadioId)

            const clickHandler = e => {
                this.handleLocationTypeChange(e.target.value)
            }

            this.locationRadio.onclick = clickHandler
            this.gpsCoordinatesRadio.onclick = clickHandler

            if(this.locationRadio.checked) {
                this.handleLocationTypeChange(this.locationRadio.value)
            } else {
                this.handleLocationTypeChange(this.gpsCoordinatesRadio.value)
            }

        }

        initLatLongInput(latInputId, lngInputId) {
            this.latitudeInput = document.getElementById(latInputId)
            this.longitudeInput = document.getElementById(lngInputId)


            
            const handleLatLongInput = () => { 
                const lat = this.latitudeInput.value
                const lng = this.longitudeInput.value

                if(lat && lng) {
                    this.setLatLng(lat, lng)
                }
            }
            const handleEnterPress = e => {
                if (e.keyCode === 13) {
                    handleLatLongInput()
                }    
            }
            const handleOnChange = e => {
                handleLatLongInput()    
            }
            this.latitudeInput.onkeypress = handleEnterPress
            this.latitudeInput.onchange = handleOnChange
            this.longitudeInput.onkeypress = handleEnterPress
            this.longitudeInput.onchange = handleOnChange

            // Check if initial value was set and if yes set marker
            const lat = this.latitudeInput.value
            const lng = this.longitudeInput.value
            if(lat && lng) {
                this.map.addMarker(lat, lng)
            }
        }

        handleLocationTypeChange(locationType) {
            const hiddenClassName = 'hidden'
            if(locationType === 'ADDR') {
                this.addressContainer.classList.remove(hiddenClassName)
                this.gpsContainer.classList.add(hiddenClassName)
            } else {
                this.addressContainer.classList.add(hiddenClassName)
                this.gpsContainer.classList.remove(hiddenClassName)
            }
        }

        disableFormDefaultAction(formId) {
            const flightForm = document.getElementById(formId)
            flightForm.onkeypress = e => {
                if (e.keyCode === 13) {
                    return false
                }
            }
        }

        getAndSetCurrentLocation() {
            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(position => {
                    const lat = position.coords.latitude
                    const lng = position.coords.longitude
                    this.fillLatLongFields(lat, lng)
                    this.gpsCoordinatesRadio.click();
                    this.setLatLng(lat, lng);
                }, error => {
                    if (error.code == error.PERMISSION_DENIED) {
                        alert("Can't get current position since you denied access to your location")
                    }
                });
            } else {
                alert('geolocation is not supported by your browser')
            }
        }

        setLatLng(lat, lng) {
            const url = this.getReverseGeocodingUrl(lat, lng)
            fetch(url)
                .then(response => {
                    if(!response.ok) {
                        throw('Could not get data from reverse geocoding service')    
                    }

                    return response.json()
                })
                .then(json => {
                    this.addressInput.value = json.resourceSets[0].resources[0].name
                })
            
            this.map.addMarker(lat, lng)
        }

        getGeocodingUrl(address, limit) {
            const geocodingUrl = 'https://dev.virtualearth.net/REST/v1/Locations'
            address = address.replace(/\s/g, '+');
            return `${geocodingUrl}?q=${address}&maxResults=${limit}&key=${BING_API_KEY}`
        }

        getReverseGeocodingUrl(lat, lng) {
            const reverseGeocodingUrl = 'https://dev.virtualearth.net/REST/v1/Locations'
            return `${reverseGeocodingUrl}/${lat},${lng}?key=${BING_API_KEY}`
        }

        getAndSetLatLong(address) {
            // constants for geocoding
            const limit = 1

            if (address) {
                const url = this.getGeocodingUrl(address, limit);
                this.addressInput.disabled = true
                fetch(url)
                    .then(response => {
                        if(!response.ok) {
                            throw('Could not get data from geocoding service')
                        }
    
                        return response.json()
                    })
                    .then(json => {
                        // searchInput.value = json[0].display_name
                        const firstResource = json.resourceSets[0].resources[0]
                        const lat = firstResource.point.coordinates[0]
                        const lng = firstResource.point.coordinates[1]
                        this.map.addMarker(lat, lng)
                        this.fillLatLongFields(lat, lng)
                        this.addressInput.value = firstResource.name
                        this.addressInput.disabled = false
                    })
            }
        }

        fillLatLongFields(lat, lng) {
            this.latitudeInput.value = lat
            this.longitudeInput.value = lng
        }
    }

    window.onload = function() {
        new FlightFormApp()
    }
})();