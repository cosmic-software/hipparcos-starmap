# Hipparcos starmap

Generate an **equirectangular star map** from the Hipparcos catalogue — a 2:1 panorama in right
ascension / declination, with each star placed at its real sky position, coloured by spectral
type and sized by brightness. Drop it on a sky sphere or a world background in a renderer, a game
engine, or a planetarium dome.

**Author:** Ben Gavares (cosmic-software).

## Ready-made map

Don't want to run anything? Grab **[`starmap_hipparcos_8k.png`](starmap_hipparcos_8k.png)** --
8192 x 4096, stars to magnitude 6.5 (~8,000 stars), generated with the defaults below.

## Use it

Needs **Python 3.8+**, `numpy` and `pillow`:

```
python -m pip install numpy pillow
python starmap_gen.py
```

The first run downloads the Hipparcos catalogue (`hip_main.dat`, ~51 MB) from the CDS if it is not
already present, then writes `starmap.png`. Options:

```
python starmap_gen.py --width 16384 --height 8192      # higher resolution (2:1)
python starmap_gen.py --mag 7.5                        # include fainter stars
python starmap_gen.py --blur 0                          # crisp points, no glow
python starmap_gen.py --catalog hip_main.dat --out sky.png --npy sky_hsv.npy
```

| Option | Meaning | Default |
| --- | --- | --- |
| `--catalog` | path to `hip_main.dat` (downloaded if missing) | `hip_main.dat` |
| `--out` | output PNG (equirectangular, 2:1) | `starmap.png` |
| `--npy` | also write an HSV NumPy array (one entry per star pixel; **large**) | off |
| `--width` / `--height` | image size (keep 2:1) | `8192 × 4096` |
| `--mag` | faintest magnitude to include (6 ≈ naked-eye limit) | `6.0` |
| `--star-size` | star dot radius in px (same for every star) | `1.5` |
| `--blur` | Gaussian blur radius, px (0 = crisp) | `0.0` |

The PNG is mostly black with sparse stars, so it compresses small (a few MB even at high
resolution). The optional `--npy` array is uncompressed and can be hundreds of MB to gigabytes at
large sizes — leave it off unless you need per-star HSV data.

## How it maps

- RA → x (`x = ra / 360 × width`), Dec → y (`y = (90 − dec) / 180 × height`), so the image is the
  sky unwrapped: RA 0–360° left to right, Dec +90° (north) at the top to −90° (south) at the bottom.
- Stars brighter than `--mag` are kept; **every star is the same size** (`--star-size`),
  and **magnitude sets its brightness** (brighter = brighter dot, not bigger).
- Colour comes from the spectral class: O/B blue, A white, F/G yellow-white to yellow, K orange,
  M red — the usual stellar colour sequence.

## Star data and credit

Star positions, magnitudes and spectral types are from the **Hipparcos catalogue** (ESA, 1997),
served by the **CDS, Strasbourg** as catalogue `I/239` (`hip_main.dat`):
<https://cdsarc.cds.unistra.fr/ftp/I/239/>. Please cite the Hipparcos mission (ESA 1997, *The
Hipparcos and Tycho Catalogues*, ESA SP-1200) and the CDS when you use the data. This project only
reads the public catalogue; it does not redistribute it.

## Licence

MIT — see [LICENSE](LICENSE). The code is MIT; the star **data** is the ESA/CDS Hipparcos
catalogue under its own terms (free for research and non-commercial use with attribution).
