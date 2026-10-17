#!/usr/bin/env python3
"""Pull the two live city sources into pipeline/cache/ (gitignored). County parcels come from
bricks' snapshots (~/Desktop/bricks/data/{hennepin,ramsey}_gis.duckdb)."""
import json, urllib.parse, urllib.request
from pathlib import Path

C = Path(__file__).resolve().parent / "cache"
C.mkdir(exist_ok=True)


def pull(url, where, out):
    rows, off = [], 0
    while True:
        p = dict(where=where, outFields="*", f="json", resultOffset=off, resultRecordCount=2000, returnGeometry="false")
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(p).encode())))
        fs = [f["attributes"] for f in d["features"]]
        rows += fs
        if not d.get("exceededTransferLimit") or not fs:
            break
        off += len(fs)
    (C / out).write_text(json.dumps(rows))
    print(out, len(rows))


pull("https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/Active_Rental_Licenses/FeatureServer/0/query", "1=1", "rental.json")
pull("https://services1.arcgis.com/9meaaHE3uiba0zr8/arcgis/rest/services/Certificate_of_Occupancy_-_Residential/FeatureServer/0/query", "UNITS>=3", "stp_cofo.json")
