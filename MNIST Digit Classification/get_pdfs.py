import requests, zipfile, os, re, gdown

links = {
 "Application of Derivatives": "jtbwLR4o", "Area Under Curves": "TtbwLOVi",
 "Basic of Mathematics": "stbwLUtK", "Binomial Theorem": "ftbwLOld",
 "Circle": "VtbwLYMQ", "Complex Number": "BtbwLIy2",
 "Continuity and Differentiability": "OtbwLO2j", "Definite Integration": "RtbwLOAK",
 "Determinants": "2tbwLYWF", "Differential Equations": "ctbwLYAd",
 "Differentiation": "mtbwLIUT", "Ellipse": "xtbwLYT1", "Functions": "utbwLPji",
 "Hyperbola": "DtbwLI7x", "Indefinite Integration": "3tbwLPXx",
 "Inverse Trigonometric Functions": "2tbwLU1y", "Limits": "4tbwLAoR",
 "Limits, Continuity and Differentiability": "ptbwLOp8", "Matrices": "mtbwLICE",
 "Parabola": "1tbwLIoJ", "Permutation Combination": "ctbwLVeJ",
 "Probability": "UtbwLBpI", "Quadratic Equation": "PtbwLXVE",
 "Sequences and Series": "TtbwLXFV", "Sets and Relations": "9tbwLCjZ",
 "Statistics": "PtbwLVke", "Straight Lines": "ttbwLVx4",
 "Three Dimensional Geometry": "1tbwLVo6", "Trigonometric Equations": "XtbwLCKB",
 "Trigonometric Ratios and Identities": "ntbwLX5e", "Vector Algebra": "HtbwLVbU",
}

os.makedirs("pdfs", exist_ok=True)
with zipfile.ZipFile("JEE_Main_2026_Jan_Maths.zip", "w") as z:
    for i, (name, code) in enumerate(links.items(), 1):
        # Follow the short link to find the Google Drive address
        r = requests.get(f"https://cutt.ly/{code}", allow_redirects=False, timeout=30)
        drive_url = r.headers.get("Location", "")
        m = re.search(r"/d/([\w-]+)", drive_url)
        if not m:
            print("SKIP", name, "->", drive_url or r.status_code)
            continue
        out = f"pdfs/{i:02d} {name}.pdf"
        try:
            gdown.download(id=m.group(1), output=out, quiet=True)
            z.write(out, os.path.basename(out))
            print("OK  ", name)
        except Exception as e:
            print("FAIL", name, "-", e)
print("Done: JEE_Main_2026_Jan_Maths.zip")