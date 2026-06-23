# solareal
Calculate how much solar energy you can harvest from a roof

<img width="927" height="870" alt="Udklip" src="https://github.com/user-attachments/assets/c87915b1-607c-43b6-bcd9-326295361077" />


Et webbaseret værktøj til analyse af tagflader baseret på Dataforsyningens højdemodel (DHM).
Funktioner

Tegn polygon på tagflade
Beregn:

Taghældning (median)
Retning (aspect)
2D og 3D areal
Simpelt solpotentiale (kWh/år)



Datagrundlag

DHM (overflademodel) via WCS
Ortofoto + bygningslag (WMS)

Teknologi

Leaflet (frontend)
Flask/Python (backend analyse)
Rasterio + NumPy (terrænberegninger)

Forbehold

Ingen skyggeanalyse
Simplificeret solmodel
Resultater er estimater

```text
/projekt-root
│
├── app.py               # Flask backend
│
├── /static
│   ├── app.js          # Leaflet frontend (kort, draw, fetch)
│   ├── style.css       # Styling (kort + labels + UI)
│
├── /templates
│   └── index.html      # HTML (kortcontainer + scripts)
│
├── analysis.py         # Backend analyse og beregner (WCS, numpy)
```

Token skal rekvireres fra Dataforsyningen.dk
