"""
generate_site.py
Scrapes ipowatch.in, updates CSV files, fetches listing prices via Yahoo Finance,
then writes a self-contained index.html for the Netlify static site.
Run twice daily via GitHub Actions (9am and 4pm IST).
"""
import re, json, time, requests
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import pandas as pd
from bs4 import BeautifulSoup

BASE      = Path(__file__).parent
MASTER    = BASE / "ipo_master.csv"
UPDATES   = BASE / "ipo_updates.csv"
OUT_HTML  = BASE / "index.html"

HEADERS   = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
MONTHS    = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
             "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
SNAPSHOTS = ["pre-apply", "day1", "day2", "day3", "final", "listing"]
_NULL     = {"", "nan", "nat", "none", "null", "n/a", "-"}
MASTER_COLS = ["IPO_ID","Name","Type","Exchange","Price_Low","Price_High",
               "Lot_Size","Open_Date","Close_Date","Listing_Date","Issue_Size_Cr"]
UPDATE_COLS = ["IPO_ID","Snapshot","Recorded_At","Retail_Sub","HNI_Sub",
               "QIB_Sub","Total_Sub","GMP","Listing_Price","Notes"]

# ── helpers ──────────────────────────────────────────────────────────────────

def _cd(s) -> str:
    s = str(s).strip().lower()
    return "" if s in _NULL else s

def _get(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"  WARN {url}: {e}")
        return None

def _parse_gmp(s) -> str:
    s = re.sub(r"[₹,\s]", "", str(s))
    if s in ("-","–","","0"): return "0"
    try: float(s); return s
    except: return ""

def _parse_price_band(s) -> Tuple[str,str]:
    s = re.sub(r"[₹,]", "", str(s)).strip()
    if " to " in s:
        p = s.split(" to ")
        try: return p[0].strip(), p[1].strip()
        except: return "",""
    s = re.sub(r"[^0-9.]","",s)
    return (s,s) if s else ("","")

def _parse_date_range(s: str, year: int) -> Tuple[str,str]:
    s = s.strip().lower().replace(",","")
    m = re.match(r"(\d+)-(\d+)\s+([a-z]+)", s)
    if m:
        d1,d2,mon = int(m.group(1)),int(m.group(2)),m.group(3)[:3]
        mo = MONTHS.get(mon,0)
        if mo:
            return f"{year}-{mo:02d}-{d1:02d}", f"{year}-{mo:02d}-{d2:02d}"
    return "",""

def _make_slug(name: str) -> str:
    return "-".join(re.sub(r"[^a-z0-9 ]","",name.lower()).split())

def _phase(row) -> str:
    today = date.today()
    try:
        od = _cd(row["Open_Date"]); cd = _cd(row["Close_Date"])
        ld = _cd(row.get("Listing_Date",""))
        if not od or not cd: return "pre-apply"
        open_d  = date.fromisoformat(od)
        close_d = date.fromisoformat(cd)
        list_d  = date.fromisoformat(ld) if ld else None
        if open_d > close_d: return "pre-apply"
    except: return "pre-apply"
    if today < open_d: return "pre-apply"
    if today == open_d: return "day1"
    if today == open_d + timedelta(days=1): return "day2"
    if open_d + timedelta(days=2) <= today <= close_d: return "day3"
    if today > close_d and (list_d is None or today < list_d): return "final"
    if list_d and today >= list_d: return "listing"
    return "final"

def _next_id(df) -> int:
    ids = pd.to_numeric(df["IPO_ID"], errors="coerce").dropna()
    return int(ids.max()) + 1 if len(ids) else 1

# ── scrapers ─────────────────────────────────────────────────────────────────

def fetch_gmp_list(year: int) -> dict:
    soup = _get("https://ipowatch.in/ipo-grey-market-premium/")
    if not soup: return {}
    result = {}
    tables = soup.find_all("table")
    for tbl_idx, typ in [(0,"Mainboard"),(1,"SME")]:
        if tbl_idx >= len(tables): continue
        for row in tables[tbl_idx].find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["th","td"])]
            if len(cells) < 6: continue
            name = cells[0].strip()
            if not name or name == "IPO Name": continue
            pl,ph = _parse_price_band(cells[3])
            od,cd = _parse_date_range(cells[5], year)
            result[name] = {"type":typ,"price_low":pl,"price_high":ph,
                            "open_date":od,"close_date":cd,
                            "gmp":_parse_gmp(cells[1]),"status":cells[6].lower() if len(cells)>6 else ""}
    return result

def fetch_subscription() -> dict:
    soup = _get("https://ipowatch.in/ipo-subscription/")
    if not soup: return {}
    result = {}
    tables = soup.find_all("table")
    if not tables: return {}
    for row in tables[0].find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["th","td"])]
        if len(cells) < 7: continue
        name = cells[0].strip()
        try:
            result[name] = {
                "retail": float(cells[5]) if cells[5] not in ("-","") else 0.0,
                "hni":    float(cells[4]) if cells[4] not in ("-","") else 0.0,
                "qib":    float(cells[3]) if cells[3] not in ("-","") else 0.0,
                "total":  float(cells[6]) if cells[6] not in ("-","") else 0.0,
            }
        except: pass
    return result

def fetch_sme_upcoming(year: int) -> dict:
    soup = _get("https://ipowatch.in/upcoming-sme-ipo/")
    if not soup: return {}
    result = {}
    tables = soup.find_all("table")
    if not tables: return {}
    for row in tables[0].find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["th","td"])]
        if len(cells) < 4: continue
        name = cells[0].strip()
        if not name or name == "IPO": continue
        pl,ph = _parse_price_band(cells[3])
        od,cd = _parse_date_range(cells[1], year)
        platform = cells[4] if len(cells)>4 else ""
        exch = "NSE SME" if "NSE" in platform.upper() else "BSE SME" if "BSE" in platform.upper() else platform
        result[name] = {"price_low":pl,"price_high":ph,"open_date":od,"close_date":cd,
                        "issue_size": re.sub(r"[^0-9.]","",str(cells[2])),"exchange":exch}
    return result

def fetch_ipo_gmp_history(slug: str, open_d: date, close_d: date, list_d: Optional[date]) -> Dict[str,str]:
    soup = _get(f"https://ipowatch.in/{slug}-ipo-gmp/")
    if not soup: return {}
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if not rows: continue
        hdrs = [td.get_text(strip=True) for td in rows[0].find_all(["td","th"])]
        if "Date" not in hdrs or "IPO GMP" not in hdrs: continue
        points = []
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
            if len(cells) < 2: continue
            gv = _parse_gmp(cells[1])
            if not gv or gv == "0": continue
            m = re.match(r"(\d+)\s+([a-z]+)", cells[0].strip().lower())
            if not m: continue
            mon_n = MONTHS.get(m.group(2)[:3], 0)
            if not mon_n: continue
            try: pt = date(open_d.year, mon_n, int(m.group(1)))
            except: continue
            points.append((pt, gv))
        if not points: return {}
        snap_map: Dict[str, list] = {}
        for pt, gv in points:
            if pt < open_d: snap = "pre-apply"
            elif pt == open_d: snap = "day1"
            elif pt == open_d + timedelta(days=1): snap = "day2"
            elif open_d + timedelta(days=2) <= pt <= close_d: snap = "day3"
            elif pt > close_d and (list_d is None or pt < list_d): snap = "final"
            elif list_d and pt >= list_d: snap = "listing"
            else: snap = "final"
            snap_map.setdefault(snap, []).append(gv)
        return {s: v[0] for s, v in snap_map.items()}
    return {}

def fetch_ipo_sub_history(slug: str) -> Dict[str, Dict[str,str]]:
    soup = _get(f"https://ipowatch.in/{slug}-ipo-subscription-status/")
    if not soup: return {}
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if not rows: continue
        hdrs = [td.get_text(strip=True) for td in rows[0].find_all(["td","th"])]
        if "Day 1" not in hdrs: continue
        day_cols = {h: i for i,h in enumerate(hdrs)}
        cat_data: Dict[str,list] = {}
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
            if cells: cat_data[cells[0]] = cells[1:]
        result: Dict[str,Dict[str,str]] = {}
        for snap, col_name in [("day1","Day 1"),("day2","Day 2"),("day3","Day 3")]:
            if col_name not in day_cols: continue
            ci = day_cols[col_name] - 1
            def _get_cat(cat: str, ci=ci) -> str:
                for k, v in cat_data.items():
                    if k.lower() == cat.lower() and ci < len(v):
                        val = v[ci].replace(",","").strip()
                        try: float(val); return val
                        except: pass
                return ""
            result[snap] = {"retail":_get_cat("RII"),"hni":_get_cat("NII"),
                            "qib":_get_cat("QIB"),"total":_get_cat("Total")}
        return result
    return {}

# ── listing price via Yahoo Finance ──────────────────────────────────────────

def _screener_symbol(name: str) -> str:
    query = re.sub(r"[^a-z0-9 ]","",name.lower()).split()[0]
    try:
        r = requests.get(f"https://www.screener.in/api/company/search/?q={query}&v=3&fts=1",
                         headers=HEADERS, timeout=8)
        for item in r.json():
            url_path = item.get("url","")
            if not url_path or "search" in url_path: continue
            m = re.search(r"/company/([A-Z0-9]+)/?", url_path)
            if m: return m.group(1)
    except: pass
    return ""

def _yahoo_open(symbol: str, listing_date_s: str) -> str:
    try:
        ld = date.fromisoformat(listing_date_s)
        import time as _t
        t0 = int(_t.mktime((ld.year,ld.month,ld.day,0,0,0,0,0,0)))
        t1 = int(_t.mktime((ld.year,ld.month,ld.day,23,59,0,0,0,0)))
        for sfx in [".NS",".BO"]:
            url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}{sfx}"
                   f"?interval=1d&period1={t0}&period2={t1}")
            r = requests.get(url, headers={**HEADERS,"Accept":"application/json"}, timeout=10)
            if r.status_code != 200: continue
            res = r.json().get("chart",{}).get("result",[None])[0]
            if not res: continue
            opens = res.get("indicators",{}).get("quote",[{}])[0].get("open",[])
            valid = [x for x in opens if x]
            if valid: return str(round(valid[0],2))
    except: pass
    return ""

def auto_listing_prices(df_master: pd.DataFrame, df_updates: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    today_s = date.today().isoformat()
    log: List[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Match on explicit Listing_Date OR computed Close + 6
    listed = df_master[df_master.apply(lambda r: _listing_date(r) == today_s, axis=1)]
    for _, row in listed.iterrows():
        ipo_id = row["IPO_ID"]
        already = df_updates[
            (df_updates["IPO_ID"] == ipo_id) &
            (df_updates["Snapshot"] == "listing") &
            (df_updates["Listing_Price"].astype(str).str.strip().isin(["","0"]) == False)
        ]
        if not already.empty: continue
        sym = _screener_symbol(row["Name"])
        if not sym:
            log.append(f"  ⚠ {row['Name']}: no ticker found"); continue
        lp = _yahoo_open(sym, today_s)
        if not lp:
            log.append(f"  ⏳ {row['Name']} ({sym}): price not yet available"); continue
        gmp_row = df_updates[(df_updates["IPO_ID"]==ipo_id)&(df_updates["Snapshot"]=="final")]
        gmp_val = gmp_row.sort_values("Recorded_At").iloc[-1]["GMP"] if not gmp_row.empty else ""
        new_upd = {"IPO_ID":ipo_id,"Snapshot":"listing","Recorded_At":now,
                   "Retail_Sub":"","HNI_Sub":"","QIB_Sub":"","Total_Sub":"",
                   "GMP":gmp_val,"Listing_Price":lp,"Notes":f"auto-yahoo-{sym}"}
        df_updates = pd.concat([df_updates, pd.DataFrame([new_upd])], ignore_index=True)
        log.append(f"  ⭐ {row['Name']} ({sym}): ₹{lp}")
    return df_updates, log

# ── master update ─────────────────────────────────────────────────────────────

def update_master(df_master: pd.DataFrame, df_updates: pd.DataFrame, year: int) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    log: List[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Fetching GMP list…")
    gmp_data = fetch_gmp_list(year)
    print("Fetching subscription…")
    sub_data = fetch_subscription()
    print("Fetching SME upcoming…")
    sme_data = fetch_sme_upcoming(year)
    time.sleep(0.5)

    existing_lc = set(df_master["Name"].str.strip().str.lower())
    candidates = {**gmp_data}
    for name, info in sme_data.items():
        candidates.setdefault(name, {"type":"SME"}).update(info)

    nxt = _next_id(df_master)
    for name, info in candidates.items():
        name_lc = name.strip().lower()
        match = df_master[df_master["Name"].str.strip().str.lower() == name_lc]
        if match.empty:
            new_row = {"IPO_ID":str(nxt),"Name":name.strip(),
                       "Type":info.get("type","Mainboard"),
                       "Exchange":info.get("exchange","NSE+BSE" if info.get("type","")=="Mainboard" else "NSE SME"),
                       "Price_Low":info.get("price_low",""),"Price_High":info.get("price_high",""),
                       "Lot_Size":"","Open_Date":info.get("open_date",""),
                       "Close_Date":info.get("close_date",""),"Listing_Date":"",
                       "Issue_Size_Cr":info.get("issue_size","")}
            df_master = pd.concat([df_master, pd.DataFrame([new_row])], ignore_index=True)
            ipo_id = str(nxt); nxt += 1
            log.append(f"Added: {name}")
        else:
            ipo_id = match.iloc[0]["IPO_ID"]
            idx = match.index[0]
            for col, val in [("Price_Low",info.get("price_low","")),
                              ("Price_High",info.get("price_high","")),
                              ("Open_Date",info.get("open_date","")),
                              ("Close_Date",info.get("close_date",""))]:
                if val and not str(df_master.at[idx,col]).strip():
                    df_master.at[idx,col] = val

        m_row  = df_master[df_master["IPO_ID"]==ipo_id].iloc[0]
        snap   = _phase(m_row)
        sub    = sub_data.get(name, {})
        gmp    = info.get("gmp","")
        # Don't insert a listing row if LP already exists — auto_listing_prices handles that
        if snap == "listing":
            has_lp = not df_updates[
                (df_updates["IPO_ID"]==ipo_id) & (df_updates["Snapshot"]=="listing") &
                (df_updates["Listing_Price"].astype(str).str.strip().isin(["","0"])==False)
            ].empty
            if has_lp:
                continue
        if sub or gmp:
            df_updates = pd.concat([df_updates, pd.DataFrame([{
                "IPO_ID":ipo_id,"Snapshot":snap,"Recorded_At":now,
                "Retail_Sub":sub.get("retail",""),"HNI_Sub":sub.get("hni",""),
                "QIB_Sub":sub.get("qib",""),"Total_Sub":sub.get("total",""),
                "GMP":gmp,"Listing_Price":"","Notes":"auto-fetched"
            }])], ignore_index=True)

    return df_master, df_updates, log

# ── HTML generation ───────────────────────────────────────────────────────────

SNAP_LABEL = {"pre-apply":"Upcoming","day1":"Day 1","day2":"Day 2",
              "day3":"Day 3","final":"Closed","listing":"Listed"}
SNAP_ICON  = {"pre-apply":"🔵","day1":"🟢","day2":"🟢","day3":"🟢","final":"🟡","listing":"⭐"}

def _fmt_x(v) -> str:
    try: f=float(v); return f"{f:.2f}x" if f else "—"
    except: return "—"

def _fmt_gmp(gmp, ph) -> str:
    try:
        g=float(gmp); p=float(ph)
        if p<=0: return f"₹{g:+.0f}"
        pct=g/p*100; sign="+" if g>=0 else ""
        return f"₹{sign}{g:.0f} ({sign}{pct:.1f}%)"
    except: return "—"

def _fmt_gain(lp, ph) -> str:
    try:
        l=float(lp); p=float(ph)
        gain=(l-p)/p*100; sign="+" if gain>=0 else ""
        return f"₹{l:.0f} ({sign}{gain:.1f}%)"
    except: return "—"

def _best_snap(ipo_id: str, df_upd: pd.DataFrame, snap: str):
    rows = df_upd[(df_upd["IPO_ID"]==ipo_id)&(df_upd["Snapshot"]==snap)]
    if rows.empty: return {}
    return rows.sort_values("Recorded_At").iloc[-1].to_dict()

def _latest_gmp(ipo_id: str, df_upd: pd.DataFrame) -> str:
    rows = df_upd[df_upd["IPO_ID"]==ipo_id].copy()
    rows = rows[rows["Snapshot"].isin(["pre-apply","day1","day2","day3","final"])]
    rows = rows[rows["GMP"].astype(str).str.strip().isin(["","0"])==False]
    if rows.empty: return ""
    snap_ord={s:i for i,s in enumerate(SNAPSHOTS)}
    rows["_o"]=rows["Snapshot"].map(snap_ord).fillna(99)
    return rows.sort_values(["_o","Recorded_At"],ascending=[False,False]).iloc[0]["GMP"]

def _latest_lp(ipo_id: str, df_upd: pd.DataFrame) -> str:
    rows = df_upd[(df_upd["IPO_ID"]==ipo_id)&(df_upd["Snapshot"]=="listing")]
    rows = rows[rows["Listing_Price"].astype(str).str.strip().isin(["","0"])==False]
    if rows.empty: return ""
    return rows.sort_values("Recorded_At").iloc[-1]["Listing_Price"]

def _listing_date(row) -> str:
    """Return explicit listing date or compute Close + 6 days (SEBI T+6 rule)."""
    ld = _cd(row.get("Listing_Date", ""))
    if ld:
        return ld
    cd = _cd(row.get("Close_Date", ""))
    if not cd:
        return ""
    try:
        return (date.fromisoformat(cd) + timedelta(days=6)).isoformat()
    except:
        return ""

def build_ipo_json(df_master: pd.DataFrame, df_updates: pd.DataFrame) -> list:
    """Build a list of dicts for each IPO to embed as JSON in the page."""
    ipos = []
    for _, m in df_master.iterrows():
        p = _phase(m)
        upd_snap = _best_snap(m["IPO_ID"], df_updates, p)
        gmp_val  = _latest_gmp(m["IPO_ID"], df_updates)
        lp_val   = _latest_lp(m["IPO_ID"], df_updates)
        ph       = m["Price_High"]

        # Build snapshot history
        history = []
        for snap in SNAPSHOTS:
            rows = df_updates[(df_updates["IPO_ID"]==m["IPO_ID"])&(df_updates["Snapshot"]==snap)]
            if rows.empty: continue
            # For listing snapshot: prefer row with actual LP; skip if none has LP
            if snap == "listing":
                lp_rows = rows[rows["Listing_Price"].astype(str).str.strip().isin(["","0"])==False]
                if lp_rows.empty:
                    continue
                r = lp_rows.sort_values("Recorded_At").iloc[-1]
            else:
                r = rows.sort_values("Recorded_At").iloc[-1]
            history.append({
                "snap": snap,
                "label": SNAP_LABEL.get(snap, snap),
                "retail": _fmt_x(r["Retail_Sub"]),
                "hni":    _fmt_x(r["HNI_Sub"]),
                "qib":    _fmt_x(r["QIB_Sub"]),
                "total":  _fmt_x(r["Total_Sub"]),
                "gmp":    _fmt_gmp(r["GMP"], ph) if r["GMP"] not in ("","0") else "—",
                "lp":     _fmt_gain(r["Listing_Price"], ph) if r.get("Listing_Price","") not in ("","0") else "—",
                "retail_raw": r["Retail_Sub"], "hni_raw": r["HNI_Sub"],
                "qib_raw": r["QIB_Sub"], "total_raw": r["Total_Sub"],
                "gmp_pct": round(float(r["GMP"])/float(ph)*100, 1) if r["GMP"] not in ("","0") and ph else None,
                "lp_pct": round((float(r["Listing_Price"])-float(ph))/float(ph)*100, 1)
                          if r.get("Listing_Price","") not in ("","0") and ph else None,
            })

        ipos.append({
            "id": m["IPO_ID"], "name": m["Name"], "type": m["Type"],
            "phase": p, "phase_label": SNAP_LABEL.get(p,"?"),
            "phase_icon": SNAP_ICON.get(p,""),
            "price_band": f"₹{m['Price_Low']}–{m['Price_High']}" if m["Price_High"] else "—",
            "price_high": ph,
            "lot_size": m["Lot_Size"] or "—",
            "min_invest": f"₹{float(m['Price_High'])*int(float(m['Lot_Size'])):,.0f}"
                          if m["Price_High"] and m["Lot_Size"] else "—",
            "issue_size": f"₹{m['Issue_Size_Cr']} Cr" if m["Issue_Size_Cr"] else "—",
            "open": m["Open_Date"], "close": m["Close_Date"],
            "listing_date": _listing_date(m),
            "retail": _fmt_x(upd_snap.get("Retail_Sub","")),
            "hni":    _fmt_x(upd_snap.get("HNI_Sub","")),
            "qib":    _fmt_x(upd_snap.get("QIB_Sub","")),
            "total":  _fmt_x(upd_snap.get("Total_Sub","")),
            "gmp":    _fmt_gmp(gmp_val, ph) if gmp_val else "—",
            "listing_price": _fmt_gain(lp_val, ph) if lp_val else "—",
            "history": history,
        })
    return ipos


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IPO Tracker</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root{--bg:#f7f7f5;--card:#fff;--border:#e2e1da;--text:#2c2b27;--sub:#6b6a63;
        --green:#1baf7a;--red:#e34948;--yellow:#f39c12;--blue:#2a78d6;
        --purple:#9b59b6;--orange:#eb6834;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);font-size:14px;}
  header{background:#1a1a2e;color:#fff;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;}
  header h1{font-size:1.3rem;font-weight:700;letter-spacing:.5px;}
  header span{font-size:.75rem;color:#aaa;}
  .tabs{display:flex;background:#fff;border-bottom:2px solid var(--border);padding:0 16px;}
  .tab{padding:12px 20px;cursor:pointer;font-weight:600;color:var(--sub);border-bottom:3px solid transparent;margin-bottom:-2px;}
  .tab.active{color:#1a1a2e;border-color:#1a1a2e;}
  .panel{display:none;padding:16px;} .panel.active{display:block;}
  .filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;}
  .filter-btn{padding:5px 14px;border:1.5px solid var(--border);border-radius:20px;cursor:pointer;font-size:.8rem;background:#fff;color:var(--sub);}
  .filter-btn.active{background:#1a1a2e;color:#fff;border-color:#1a1a2e;}
  table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);}
  th{background:#f0efeb;padding:10px 12px;text-align:left;font-weight:600;font-size:.78rem;color:var(--sub);white-space:nowrap;}
  td{padding:9px 12px;border-top:1px solid var(--border);font-size:.82rem;vertical-align:middle;}
  tr:hover td{background:#f9f8f5;cursor:pointer;}
  .badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.72rem;font-weight:600;}
  .badge-green{background:#e6f7f1;color:#1baf7a;} .badge-blue{background:#e8f0fd;color:#2a78d6;}
  .badge-yellow{background:#fef9e7;color:#f39c12;} .badge-star{background:#fff3cd;color:#e67e22;}
  .pos{color:var(--green);font-weight:600;} .neg{color:var(--red);font-weight:600;}
  .modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:100;align-items:center;justify-content:center;}
  .modal-overlay.open{display:flex;}
  .modal{background:#fff;border-radius:12px;width:min(900px,96vw);max-height:90vh;overflow-y:auto;padding:24px;}
  .modal-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;}
  .modal-head h2{font-size:1.1rem;} .close-btn{background:none;border:none;font-size:1.4rem;cursor:pointer;color:var(--sub);}
  .metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:16px;}
  .metric{background:var(--bg);border-radius:8px;padding:10px 12px;}
  .metric-label{font-size:.7rem;color:var(--sub);margin-bottom:3px;} .metric-val{font-size:.95rem;font-weight:700;}
  .snap-table{width:100%;border-collapse:collapse;margin-bottom:16px;}
  .snap-table th{background:#f0efeb;padding:7px 10px;font-size:.75rem;color:var(--sub);text-align:left;}
  .snap-table td{padding:7px 10px;border-top:1px solid var(--border);font-size:.78rem;}
  .chart-wrap{position:relative;height:250px;margin-bottom:12px;}
  .chart-title{font-size:.8rem;font-weight:600;color:var(--sub);margin-bottom:6px;}
  .empty{text-align:center;padding:40px;color:var(--sub);}
  @media(max-width:600px){th:nth-child(n+6),td:nth-child(n+6){display:none;}}
</style>
</head>
<body>
<header>
  <h1>📈 IPO Tracker</h1>
  <span id="last-updated"></span>
</header>
<div class="tabs">
  <div class="tab active" onclick="switchTab('mainboard',this)">Mainboard</div>
  <div class="tab" onclick="switchTab('sme',this)">SME</div>
</div>
<div id="panel-mainboard" class="panel active">
  <div class="filters" id="filters-mainboard"></div>
  <div id="table-mainboard"></div>
</div>
<div id="panel-sme" class="panel">
  <div class="filters" id="filters-sme"></div>
  <div id="table-sme"></div>
</div>

<div class="modal-overlay" id="modal-overlay" onclick="closeModal(event)">
  <div class="modal" id="modal-content"></div>
</div>

<script>
const DATA = /*DATA_JSON*/;
const UPDATED = "/*UPDATED*/";
document.getElementById("last-updated").textContent = "Updated: " + UPDATED;

const PHASE_ORDER = {"pre-apply":0,"day1":1,"day2":2,"day3":3,"final":4,"listing":5};
const STATUS_FILTERS = {
  "All":     () => true,
  "Active":  r => ["day1","day2","day3"].includes(r.phase),
  "Upcoming":r => r.phase === "pre-apply",
  "Closed":  r => r.phase === "final",
  "Listed":  r => r.phase === "listing",
};

let activeFilters = {mainboard:"All", sme:"All"};

function badgeClass(phase){
  return {day1:"badge-green",day2:"badge-green",day3:"badge-green",
          "pre-apply":"badge-blue",final:"badge-yellow",listing:"badge-star"}[phase]||"badge-blue";
}
function subColor(v){
  const n=parseFloat(v);
  if(isNaN(n)||!v||v==="—") return "";
  return n>=100?"🔥 "+(n.toFixed(2)+"x"): n>=10?"🟢 "+(n.toFixed(2)+"x"): n>=1?"🟡 "+(n.toFixed(2)+"x"):"🔴 "+(n.toFixed(2)+"x");
}
function subDisplay(v){
  const d=subColor(v); return d||"—";
}

function renderTable(type){
  const filter = activeFilters[type];
  const rows = DATA.filter(d=>d.type.toLowerCase()===type && STATUS_FILTERS[filter](d));
  const el = document.getElementById("table-"+type);
  if(!rows.length){el.innerHTML='<div class="empty">No IPOs for this filter.</div>';return;}
  let html = `<table><thead><tr>
    <th>Status</th><th>Company</th><th>Price Band</th><th>Open</th><th>Close</th><th>Listing</th>
    <th>Retail</th><th>HNI</th><th>QIB</th><th>Total</th>
    <th>GMP</th><th>Listing Price</th>
  </tr></thead><tbody>`;
  rows.forEach(r=>{
    html+=`<tr onclick="openModal('${r.id}')">
      <td><span class="badge ${badgeClass(r.phase)}">${r.phase_icon} ${r.phase_label}</span></td>
      <td><b>${r.name}</b></td>
      <td>${r.price_band}</td>
      <td>${r.open}</td><td>${r.close}</td><td>${r.listing_date||"—"}</td>
      <td>${subDisplay(r.retail)}</td>
      <td>${subDisplay(r.hni)}</td>
      <td>${subDisplay(r.qib)}</td>
      <td>${subDisplay(r.total)}</td>
      <td>${r.gmp!=="—"?'<span class="pos">'+r.gmp+'</span>':r.gmp}</td>
      <td>${r.listing_price!=="—"?'<span class="pos">'+r.listing_price+'</span>':r.listing_price}</td>
    </tr>`;
  });
  html+="</tbody></table>";
  el.innerHTML=html;
}

function renderFilters(type){
  const el=document.getElementById("filters-"+type);
  el.innerHTML=Object.keys(STATUS_FILTERS).map(f=>
    `<button class="filter-btn ${activeFilters[type]===f?'active':''}"
      onclick="setFilter('${type}','${f}',this)">${f}</button>`
  ).join("");
}

function setFilter(type,f,btn){
  activeFilters[type]=f;
  document.querySelectorAll("#filters-"+type+" .filter-btn").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active");
  renderTable(type);
}

let charts=[];
function openModal(id){
  const ipo=DATA.find(d=>d.id===id);
  if(!ipo) return;
  charts.forEach(c=>c.destroy()); charts=[];

  const snaps=ipo.history;
  const snapLabels=snaps.map(s=>s.label);

  function metricBox(label,val){
    return `<div class="metric"><div class="metric-label">${label}</div><div class="metric-val">${val}</div></div>`;
  }

  let histTable=`<table class="snap-table"><thead><tr>
    <th>Snapshot</th><th>Retail</th><th>HNI</th><th>QIB</th><th>Total</th>
    <th>GMP (₹ & %)</th><th>Listing (₹ & %)</th>
  </tr></thead><tbody>`;
  snaps.forEach(s=>{
    histTable+=`<tr>
      <td><b>${s.label}</b></td>
      <td>${s.retail}</td><td>${s.hni}</td><td>${s.qib}</td><td>${s.total}</td>
      <td>${s.gmp!=="—"?'<span class="pos">'+s.gmp+'</span>':s.gmp}</td>
      <td>${s.lp!=="—"?'<span class="pos">'+s.lp+'</span>':s.lp}</td>
    </tr>`;
  });
  histTable+="</tbody></table>";

  const modal=document.getElementById("modal-content");
  modal.innerHTML=`
    <div class="modal-head">
      <h2>${ipo.phase_icon} ${ipo.name}</h2>
      <button class="close-btn" onclick="closeModal()">✕</button>
    </div>
    <div class="metrics">
      ${metricBox("Status","<span class='badge "+badgeClass(ipo.phase)+"'>"+ipo.phase_icon+" "+ipo.phase_label+"</span>")}
      ${metricBox("Price Band",ipo.price_band)}
      ${metricBox("Lot Size",ipo.lot_size)}
      ${metricBox("Min Investment",ipo.min_invest)}
      ${metricBox("Issue Size",ipo.issue_size)}
      ${metricBox("Open Date",ipo.open)}
      ${metricBox("Close Date",ipo.close)}
      ${ipo.listing_date?metricBox("Listing Date",ipo.listing_date):""}
    </div>
    ${snaps.length?histTable:'<p class="empty">No snapshot data yet.</p>'}
    ${snaps.length>=1?`
      <div class="chart-title">Subscription Progress (× times)</div>
      <div class="chart-wrap"><canvas id="chart-sub"></canvas></div>
      <div class="chart-title">GMP & Listing Gain (% over issue price)</div>
      <div class="chart-wrap"><canvas id="chart-gmp"></canvas></div>
    `:""}
  `;
  document.getElementById("modal-overlay").classList.add("open");

  if(snaps.length>=1){
    // Subscription chart
    const ctxSub=document.getElementById("chart-sub").getContext("2d");
    charts.push(new Chart(ctxSub,{
      type:"line",
      data:{
        labels:snapLabels,
        datasets:[
          {label:"Retail",data:snaps.map(s=>parseFloat(s.retail_raw)||null),borderColor:"#2a78d6",backgroundColor:"rgba(42,120,214,.1)",tension:.3,pointRadius:5},
          {label:"HNI",   data:snaps.map(s=>parseFloat(s.hni_raw)||null),  borderColor:"#1baf7a",backgroundColor:"rgba(27,175,122,.1)",tension:.3,pointRadius:5},
          {label:"QIB",   data:snaps.map(s=>parseFloat(s.qib_raw)||null),  borderColor:"#eb6834",backgroundColor:"rgba(235,104,52,.1)", tension:.3,pointRadius:5},
          {label:"Total", data:snaps.map(s=>parseFloat(s.total_raw)||null),borderColor:"#9b59b6",backgroundColor:"rgba(155,89,182,.1)",tension:.3,pointRadius:5},
        ]
      },
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{position:"top"}},
        scales:{y:{beginAtZero:true,title:{display:true,text:"Times (×)"}}}
      }
    }));

    // GMP % chart
    const ctxGmp=document.getElementById("chart-gmp").getContext("2d");
    charts.push(new Chart(ctxGmp,{
      type:"bar",
      data:{
        labels:snapLabels,
        datasets:[
          {label:"GMP %",
           data:snaps.map(s=>s.gmp_pct),
           backgroundColor:snaps.map(s=>s.gmp_pct>=0?"rgba(27,175,122,.75)":"rgba(227,73,72,.75)"),
           borderRadius:4},
          {label:"Listing %",
           data:snaps.map(s=>s.lp_pct),
           backgroundColor:"rgba(243,156,18,.8)",
           borderRadius:4},
        ]
      },
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{position:"top"},
          annotation:{annotations:[{type:"line",yMin:0,yMax:0,borderColor:"#555",borderWidth:1,borderDash:[4,4]}]}
        },
        scales:{y:{title:{display:true,text:"% gain over issue price"},
                   ticks:{callback:v=>(v>=0?"+":"")+v+"%"}}}
      }
    }));
  }
}

function closeModal(e){
  if(e && e.target!==document.getElementById("modal-overlay")) return;
  document.getElementById("modal-overlay").classList.remove("open");
  charts.forEach(c=>c.destroy()); charts=[];
}

function switchTab(type,btn){
  document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById("panel-"+type).classList.add("active");
}

// Initial render
["mainboard","sme"].forEach(type=>{
  renderFilters(type);
  renderTable(type);
});
</script>
</body>
</html>
"""

def generate_html(ipos: list, updated: str) -> str:
    json_str = json.dumps(ipos, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("/*DATA_JSON*/", json_str, 1)
    html = html.replace("/*UPDATED*/", updated, 1)
    return html

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    year  = date.today().year
    now_s = datetime.now().strftime("%d %b %Y, %I:%M %p IST")
    print(f"=== IPO Site Generator — {now_s} ===")

    # Load existing data
    df_master  = pd.read_csv(MASTER, dtype=str).fillna("") if MASTER.exists() else pd.DataFrame(columns=MASTER_COLS)
    df_updates = pd.read_csv(UPDATES, dtype=str).fillna("") if UPDATES.exists() else pd.DataFrame(columns=UPDATE_COLS)

    # 1. Fetch and merge live data
    df_master, df_updates, log = update_master(df_master, df_updates, year)
    print(f"Master update: {len(log)} changes")

    # 2. Auto-fetch listing prices for IPOs listing today
    print("Checking listing prices…")
    df_updates, lp_log = auto_listing_prices(df_master, df_updates)
    for msg in lp_log: print(msg)

    # 3. Save CSVs
    df_master[MASTER_COLS].to_csv(MASTER, index=False)
    df_updates[UPDATE_COLS].to_csv(UPDATES, index=False)
    print(f"Saved: {len(df_master)} IPOs, {len(df_updates)} update rows")

    # 4. Generate HTML
    ipos = build_ipo_json(df_master, df_updates)
    html = generate_html(ipos, now_s)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Written: {OUT_HTML} ({len(html)//1024}KB)")

if __name__ == "__main__":
    main()
