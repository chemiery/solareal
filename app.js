// -----------------------------
// MAP INIT (tilfældig startsted)
// -----------------------------
var defaultZoom = 15;

var startViews = [
    [55.88, 10.70],
    [55.36, 10.72],
    [55.42, 10.72],
    [55.49, 10.84]
];

var randomCoords = startViews[Math.floor(Math.random() * startViews.length)];

var map = L.map('map').setView(randomCoords, defaultZoom);


// -----------------------------
// BASELAYERS
// -----------------------------
L.tileLayer.wms(
    "https://api.dataforsyningen.dk/orto_foraar_DAF?token=XXXXXXXXXXXXX",
    {
        layers: "orto_foraar",
        format: "image/png",
        transparent: true,
        minZoom: 5,
        maxZoom: 24,
        attribution: "© Dataforsyningen"
    }
).addTo(map);

L.tileLayer.wms(
    "https://api.dataforsyningen.dk/wms/building_inspire?token=XXXXXXXXXXXXXXXXXX",
    {
        layers: "BU.Building",
        format: "image/png",
        transparent: true,
        opacity: 0.45,
        minZoom: 18,
        maxZoom: 24,
        attribution: "© Dataforsyningen"
    }
).addTo(map);


var northArrow = L.control({ position: "topleft" });

northArrow.onAdd = function () {
    var div = L.DomUtil.create("div", "north-arrow");

    div.innerHTML = `
    <div style="font-size:18px; text-align:center;">
        N
    </div>
    <div style="font-size:24px;">▲</div>
`;
    div.style.fontSize = "24px";
    div.style.background = "white";
    div.style.padding = "6px";
    div.style.borderRadius = "6px";
    div.style.boxShadow = "0 0 5px rgba(0,0,0,0.3)";

    return div;
};

northArrow.addTo(map);



// -----------------------------
// INFO BUTTON
// -----------------------------
var infoControl = L.control({ position: "topright" });

infoControl.onAdd = function () {
    var div = L.DomUtil.create("div", "info-button");
    div.innerHTML = "ℹ️";

    div.style.background = "white";
    div.style.padding = "8px";
    div.style.cursor = "pointer";
    div.style.borderRadius = "6px";
    div.style.boxShadow = "0 0 5px rgba(0,0,0,0.3)";
    div.style.fontSize = "18px";

    div.onclick = function (e) {
        L.DomEvent.stopPropagation(e);

        alert(
            "Taganalyse\n\n" +
            "Datakilde:\nDHM (0.4 m)\n\n" +
            "Metode:\n- Gradient\n- Aspect\n- 3D areal\n\n" +
            "Solmodel:\n- 1000 kWh/m²/år\n- 35° optimal\n\n" +
            "Antagelser:\n- Ingen skygge\n- Skyfrit\n\n" +
            "Data: © Dataforsyningen"
        );
    };

    return div;
};

infoControl.addTo(map);


// -----------------------------
// DRAW TOOL
// -----------------------------
var drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

var drawControl = new L.Control.Draw({
    draw: {
        polygon: {
            allowIntersection: false,
            showArea: false
        },
        rectangle: false,
        circle: false,
        marker: false,
        polyline: false
    },
    edit: {
        featureGroup: drawnItems
    }
});

map.addControl(drawControl);


// -----------------------------
// DRAW CREATED
// -----------------------------
map.on(L.Draw.Event.CREATED, function (e) {
    drawnItems.clearLayers();
    drawnItems.addLayer(e.layer);
});


// -----------------------------
// DIRECTION HELPER
// -----------------------------
function directionName(deg) {
    if (deg >= 337.5 || deg < 22.5) return "Nord";
    if (deg < 67.5) return "Nordøst";
    if (deg < 112.5) return "Øst";
    if (deg < 157.5) return "Sydøst";
    if (deg < 202.5) return "Syd";
    if (deg < 247.5) return "Sydvest";
    if (deg < 292.5) return "Vest";
    return "Nordvest";
}


// -----------------------------
// CALCULATE
// -----------------------------
function calculate() {

    var layers = drawnItems.getLayers();
    if (layers.length === 0) {
        alert("Tegn en polygon først");
        return;
    }

    var geojson = layers[0].toGeoJSON();

    fetch("/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(geojson)
    })
    .then(res => res.json())
    .then(data => {

        if (data.error) {
            alert(data.error);
            return;
        }

        var html = `
			<b>Hældning</b><br><br>
			Taghældning: ${data.median}°<br>

			<b>Retning</b><br>
			${data.aspect_median}° (${directionName(data.aspect_median)})<br><br>

			<b>Areal</b><br>
			Tegnet areal: ${data.area_2d} m²<br>
			Tagareal: ${data.area_3d} m²<br><br>

			<b>Solpotentiale</b><br>
			Energi: ${data.energy_kwh ? data.energy_kwh.toLocaleString() : "-"} kWh/år<br>
			Faktor: ${data.solar_factor ?? "-"}<br>
		`;


        L.popup()
            .setLatLng(drawnItems.getBounds().getCenter())
            .setContent(html)
            .openOn(map);
    });
}
