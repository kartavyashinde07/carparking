function toggleSlotRow(rowId) {
        let el = document.getElementById(rowId);
        if (el.style.display === "none") {
            el.style.display = "table-row-group";
        } else {
            el.style.display = "none";
        }
    }

    function filterTable(inputId, tableId) {
        let input = document.getElementById(inputId);
        let filter = input.value.toUpperCase();
        let table = document.getElementById(tableId);
        let tr = table.getElementsByTagName("tr");
        for (let i = 1; i < tr.length; i++) {
            let td = tr[i].getElementsByTagName("td")[0]; // searching the first column (Vehicle ID)
            if (td) {
                let txtValue = td.textContent || td.innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    tr[i].style.display = "";
                } else {
                    tr[i].style.display = "none";
                }
            }       
        }
    }

    async function confirmOfflinePayment(id) {
        if (!confirm("Confirm you have received the cash payment from the customer?")) return;
        try {
            let res = await fetch(`/api/confirm_offline_payment/${id}`, { method: 'POST' });
            let data = await res.json();
            if (data.success) {
                window.location.reload();
            } else {
                alert("Action failed!");
            }
        } catch (e) {
            alert("Connection error.");
        }
    }

    async function confirmArrival(id) {
        if (!confirm("Confirm customer has arrived and parked?")) return;
        try {
            let res = await fetch(`/api/confirm_arrival/${id}`, { method: 'POST' });
            let data = await res.json();
            if (data.success) {
                window.location.reload();
            } else {
                alert("Action failed: " + data.message);
            }
        } catch (e) {
            alert("Connection error.");
        }
    }

    let pMap;
    let selectedPMarker;

    function openParkingModal() {
        document.getElementById('add-parking-modal').classList.add('active');
        
        if (!pMap) {
            setTimeout(() => {
                pMap = L.map('partner-map').setView([20.0110, 73.7903], 14); // Default Nashik
                
                L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                    attribution: '© OpenStreetMap contributors',
                    subdomains: 'abcd',
                    maxZoom: 19
                }).addTo(pMap);

                pMap.on('click', async function(e) {
                    const lat = e.latlng.lat;
                    const lng = e.latlng.lng;
                    
                    document.getElementById('form-lat').value = lat;
                    document.getElementById('form-lng').value = lng;
                    
                    document.getElementById('coord-status').innerHTML = `<span style="color: #00ff88;">Selected: ${lat.toFixed(4)}, ${lng.toFixed(4)}</span> <span style="font-size: 0.7rem;">(Fetching address...)</span>`;
                    document.getElementById('submit-btn').disabled = false;
                    document.getElementById('submit-btn').style.background = 'rgba(0, 242, 255, 0.2)';

                    focusMapOn(lat, lng);

                    try {
                        let res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`);
                        let data = await res.json();
                        if (data && data.display_name) {
                            document.getElementById('location-name-input').value = data.display_name;
                            document.getElementById('coord-status').innerHTML = `<span style="color: #00ff88;">Selected: ${lat.toFixed(4)}, ${lng.toFixed(4)}</span>`;
                        }
                    } catch (err) {
                        console.error("Reverse geocoding failed", err);
                    }
                });
            }, 100);
        }
    }

    async function searchLocation() {
        let query = document.getElementById('location-name-input').value;
        if (!query) return;
        
        document.getElementById('coord-status').innerHTML = `<span style="color: var(--text-muted);">Searching map for address...</span>`;
        
        try {
            let res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
            let data = await res.json();
            
            if (data && data.length > 0) {
                let lat = parseFloat(data[0].lat);
                let lng = parseFloat(data[0].lon);
                
                document.getElementById('form-lat').value = lat;
                document.getElementById('form-lng').value = lng;
                
                document.getElementById('coord-status').innerHTML = `<span style="color: #00ff88;">Found: ${lat.toFixed(4)}, ${lng.toFixed(4)}</span>`;
                document.getElementById('submit-btn').disabled = false;
                document.getElementById('submit-btn').style.background = 'rgba(0, 242, 255, 0.2)';
                
                focusMapOn(lat, lng);
            } else {
                document.getElementById('coord-status').innerHTML = `<span style="color: #ff0055;">Address not found on map.</span>`;
            }
        } catch (err) {
            console.error("Geocoding failed", err);
            document.getElementById('coord-status').innerHTML = `<span style="color: #ff0055;">Search error.</span>`;
        }
    }

    function focusMapOn(lat, lng) {
        if (selectedPMarker) {
            pMap.removeLayer(selectedPMarker);
        }
        selectedPMarker = L.marker([lat, lng]).addTo(pMap);
        pMap.setView([lat, lng], 16);
    }

    function closeParkingModal() {
        document.getElementById('add-parking-modal').classList.remove('active');
    }