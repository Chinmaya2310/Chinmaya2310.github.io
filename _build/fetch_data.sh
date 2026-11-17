#!/usr/bin/env bash
# Downloads the three raw inputs into _data/raw/. Run from the repo root.
#  1. Jan Aushadhi product list + MRPs  (PMBI, the official API behind janaushadhi.gov.in "Product Portfolio")
#  2. Jan Aushadhi Kendra (store) list   (same API, "Locate Kendra")
#  3. Brand MRPs and compositions        (Indian Medicine Dataset, MIT licence, github.com/junioralive/Indian-Medicine-Dataset)
set -euo pipefail
mkdir -p _data/raw
API=https://janaushadhi.gov.in:8443
TOK=$(curl -s "$API/auth/generateGuestToken" | python3 -c "import sys,json;print(json.load(sys.stdin)['responseBody'])")
H=(-s -A "Mozilla/5.0" -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" -X POST)
curl "${H[@]}" "$API/api/v1/website/getAllProductForWeb" \
  -d '{"pageIndex":0,"pageSize":5000,"searchText":"","columnName":"id","orderBy":"asc"}' -o _data/raw/products.json
curl "${H[@]}" "$API/api/v1/website/getAllKendraByStateDistrict" \
  -d '{"pageIndex":0,"pageSize":30000,"stateId":0,"districtId":0,"pinCode":0,"storeCode":""}' -o _data/raw/kendras.json
curl -sL https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv -o _data/raw/meds.csv
echo "done. next: python3 _build/match.py && python3 _build/build.py"
