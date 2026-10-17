#!/usr/bin/env python3
"""Hipparcos starmap generator.

Turns the Hipparcos catalogue (hip_main.dat) into an equirectangular star map (a 2:1
panorama in RA / Dec): each star placed at its right ascension and declination, coloured by
spectral type, sized by brightness, and softened with a light blur. Handy as a sky background
for a renderer, a game engine, or a planetarium dome.

    python starmap_gen.py                         # downloads the catalogue, writes starmap.png
    python starmap_gen.py --width 16384 --height 8192 --mag 7.5
    python starmap_gen.py --catalog hip_main.dat --out sky.png --npy sky_hsv.npy

Author: Ben Gavares (cosmic-software). MIT licence (see LICENSE).
Star data: the Hipparcos catalogue (ESA 1997), from the CDS (Strasbourg), I/239/hip_main.dat.
Depends on: numpy, pillow (no astropy -- the fixed-width columns are read directly).
"""
import argparse
import colorsys
import os
import ssl
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CATALOG_URL = "https://cdsarc.cds.unistra.fr/ftp/I/239/hip_main.dat"

# fixed-width columns in hip_main.dat (0-based [start, end] inclusive, as the catalogue's ReadMe):
# RA (deg), Dec (deg), Hipparcos magnitude, spectral type.
COLS = {"ra": (51, 63), "dec": (64, 76), "mag": (274, 281), "sptype": (435, 447)}

# representative sRGB colours per spectral class (hot blue O/B -> cool red M)
SPECTRAL_RGB = {"O": (155, 176, 255), "B": (170, 191, 255), "A": (202, 215, 255),
                "F": (248, 247, 255), "G": (255, 244, 234), "K": (255, 210, 161),
                "M": (255, 204, 111)}
DEFAULT_RGB = (200, 200, 200)

# every star is the same SIZE; magnitude sets its BRIGHTNESS (flux ~ 10^(-0.4 mag), normalised so a
# star at MAG_FULL or brighter is full brightness, gamma-lifted, with a floor so the faintest are
# still visible).
MAG_FULL, MAG_GAMMA, MIN_BRIGHT = 1.5, 0.5, 0.1


def _open(url):
    """Open the URL, falling back to an unverified TLS context when the machine has no CA bundle
    (a common Windows / Python problem): the CDS catalogue is public, so this is a convenience,
    not a secret."""
    try:
        return urllib.request.urlopen(url, timeout=60)
    except urllib.error.URLError as e:
        if not isinstance(getattr(e, "reason", None), ssl.SSLError):
            raise
        print("  (TLS verification failed; retrying without certificate checks)")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(url, timeout=60, context=ctx)


def download_catalog(path):
    """Fetch hip_main.dat (~51 MB) from the CDS if it is not already here."""
    print(f"Downloading the Hipparcos catalogue to {path} ...\n  {CATALOG_URL}")
    with _open(CATALOG_URL) as r, open(path, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        got = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if total:
                print(f"\r  {got / 1e6:,.0f} / {total / 1e6:,.0f} MB", end="", flush=True)
    print("\n  done.")


def read_catalog(path):
    """(ra, dec, mag, sptype) arrays from hip_main.dat, invalid rows dropped."""
    def num(s):
        try:
            return float(s.strip().strip("|"))
        except ValueError:
            return np.nan

    ra, dec, mag, spt = [], [], [], []
    with open(path, encoding="latin-1") as f:
        for line in f:
            ra.append(num(line[COLS["ra"][0]:COLS["ra"][1] + 1]))
            dec.append(num(line[COLS["dec"][0]:COLS["dec"][1] + 1]))
            mag.append(num(line[COLS["mag"][0]:COLS["mag"][1] + 1]))
            spt.append(line[COLS["sptype"][0]:COLS["sptype"][1] + 1].strip())
    ra, dec, mag = np.array(ra), np.array(dec), np.array(mag)
    spt = np.array(spt, dtype=object)
    ok = ~np.isnan(ra) & ~np.isnan(dec) & ~np.isnan(mag)
    return ra[ok], dec[ok], mag[ok], spt[ok]


def classify_color(sptype):
    return SPECTRAL_RGB.get(sptype[:1].upper(), DEFAULT_RGB) if sptype else DEFAULT_RGB


def create_starmap(catalog, out_png, out_npy=None, width=8192, height=4096, mag_limit=6.0,
                   blur=0.0, star_size=1.5):
    """Write the equirectangular star map (and, when out_npy is given, an HSV NumPy array with one
    entry per plotted star pixel: H, S, V in 0..255). Every star is the same size; magnitude sets
    its brightness."""
    ra, dec, mag, spt = read_catalog(catalog)
    keep = mag <= mag_limit
    ra, dec, mag, spt = ra[keep], dec[keep], mag[keep], spt[keep]
    print(f"{len(ra):,} stars brighter than magnitude {mag_limit:g}")

    # brightness from magnitude (same size for every star)
    flux = 10.0 ** (-0.4 * (mag - MAG_FULL))
    val = MIN_BRIGHT + (1.0 - MIN_BRIGHT) * np.clip(flux, 0.0, 1.0) ** MAG_GAMMA
    colors = [classify_color(s) for s in spt]

    img = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(img)
    hsv = np.zeros((height, width, 3), dtype=np.uint8) if out_npy else None
    r = max(star_size, 0.5)
    for i in range(len(ra)):
        x = int((ra[i] / 360.0) * width) % width
        y = int(((90.0 - dec[i]) / 180.0) * height)
        y = min(max(y, 0), height - 1)
        col = tuple(int(c * val[i]) for c in colors[i])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=col)
        if hsv is not None:
            h, s, v = colorsys.rgb_to_hsv(*[c / 255.0 for c in col])
            hsv[y, x] = (int(h * 255), int(s * 255), int(v * 255))

    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    img.save(out_png)
    print(f"wrote {out_png}  ({width} x {height})")
    if hsv is not None:
        np.save(out_npy, hsv)
        print(f"wrote {out_npy}  ({hsv.nbytes / 1e6:,.0f} MB)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Make an equirectangular Hipparcos star map.")
    ap.add_argument("--catalog", default="hip_main.dat", help="Hipparcos hip_main.dat (downloaded if missing)")
    ap.add_argument("--out", default="starmap.png", help="output PNG (equirectangular, 2:1)")
    ap.add_argument("--npy", default=None, help="also write an HSV NumPy array here (large; off by default)")
    ap.add_argument("--width", type=int, default=8192)
    ap.add_argument("--height", type=int, default=4096)
    ap.add_argument("--mag", type=float, default=6.0, help="faintest magnitude to include")
    ap.add_argument("--star-size", type=float, default=1.5, help="star dot radius in pixels (same for every star)")
    ap.add_argument("--blur", type=float, default=0.0, help="Gaussian blur radius in pixels (0 = crisp)")
    a = ap.parse_args(argv)
    if a.width != 2 * a.height:
        print("note: equirectangular maps are 2:1 (width = 2 x height); continuing anyway.", file=sys.stderr)
    if not os.path.exists(a.catalog):
        download_catalog(a.catalog)
    create_starmap(a.catalog, a.out, a.npy, a.width, a.height, a.mag, a.blur, a.star_size)


if __name__ == "__main__":
    main()
