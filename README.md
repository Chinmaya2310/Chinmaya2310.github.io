# Generic Bachat

Find the cheaper Jan Aushadhi generic for a branded medicine, see the saving per tablet, and locate the nearest Jan Aushadhi Kendra.

Live: https://chinmaya2310.github.io/generic-bachat/

## Data
- Jan Aushadhi products, MRPs and Kendra list: official PMBI API behind janaushadhi.gov.in (fetched 17 Nov 2026)
- Brand prices and compositions: [Indian Medicine Dataset](https://github.com/junioralive/Indian-Medicine-Dataset) (MIT)

## Build
```bash
bash _build/fetch_data.sh      # raw data -> _data/raw/
python3 _build/match.py        # brand <-> generic matching -> _data/matched.json
python3 _build/build.py        # static pages, JSON search index, sitemap
```
Static site, no backend: GitHub Pages serves the generated HTML and JSON.

Not medical advice. Not affiliated with PMBI or the Government of India.
