import time
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(client, method, path, params=None, json_body=None):
    t0 = time.perf_counter()
    if method == "GET":
        resp = client.get(path, params=params)
    elif method == "POST":
        resp = client.post(path, json=json_body)
    duration_ms = (time.perf_counter() - t0) * 1000
    return resp, duration_ms

def run_validations():
    results = []
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1 & 2: Health
        resp, dur = test_endpoint(client, "GET", "/health")
        results.append({
            "check": "GET /health",
            "status": resp.status_code,
            "duration_ms": round(dur, 2),
            "data": resp.json(),
            "ok": resp.status_code == 200 and resp.json().get("status") == "healthy"
        })

        # 3 & 4: Medicine Searches
        search_terms = ["paracetamol", "Dolo", "Crocin", "amoxicillin", "cefuroxime"]
        sample_med_id = None
        sample_med_name = None

        for term in search_terms:
            resp, dur = test_endpoint(client, "GET", "/api/medicines/search", params={"q": term, "limit": 5})
            data = resp.json() if resp.status_code == 200 else {}
            total = data.get("pagination", {}).get("total", 0)
            items = data.get("data", [])
            if items and not sample_med_id:
                sample_med_id = items[0]["medicine_id"]
                sample_med_name = items[0]["brand_name"]

            results.append({
                "check": f"GET /api/medicines/search?q={term}",
                "status": resp.status_code,
                "duration_ms": round(dur, 2),
                "total_matched": total,
                "returned_count": len(items),
                "top_result": items[0]["brand_name"] if items else None,
                "ok": resp.status_code == 200 and total > 0
            })

        # 5: Medicine detail lookup by medicine ID
        if sample_med_id:
            resp, dur = test_endpoint(client, "GET", f"/api/medicines/{sample_med_id}")
            data = resp.json() if resp.status_code == 200 else {}
            results.append({
                "check": f"GET /api/medicines/{sample_med_id} (Detail Lookup)",
                "status": resp.status_code,
                "duration_ms": round(dur, 2),
                "brand_name": data.get("brand_name"),
                "variants_count": len(data.get("variants", [])),
                "ok": resp.status_code == 200 and data.get("medicine_id") == sample_med_id
            })

            # 7: Medicine variants endpoint
            resp_vars, dur_vars = test_endpoint(client, "GET", f"/api/medicines/{sample_med_id}/variants")
            vars_data = resp_vars.json() if resp_vars.status_code == 200 else []
            results.append({
                "check": f"GET /api/medicines/{sample_med_id}/variants",
                "status": resp_vars.status_code,
                "duration_ms": round(dur_vars, 2),
                "variants_returned": len(vars_data),
                "sample_variant": vars_data[0].get("packaging_description") if vars_data else None,
                "ok": resp_vars.status_code == 200 and len(vars_data) > 0
            })

            # 9a: Substitutes endpoint
            resp_sub, dur_sub = test_endpoint(client, "GET", f"/api/medicines/{sample_med_id}/substitutes")
            sub_data = resp_sub.json() if resp_sub.status_code == 200 else []
            results.append({
                "check": f"GET /api/medicines/{sample_med_id}/substitutes",
                "status": resp_sub.status_code,
                "duration_ms": round(dur_sub, 2),
                "substitutes_returned": len(sub_data),
                "ok": resp_sub.status_code == 200
            })

        # 6: Manufacturer search
        resp_mfg, dur_mfg = test_endpoint(client, "GET", "/api/manufacturers/search", params={"q": "Sun", "limit": 5})
        mfg_data = resp_mfg.json() if resp_mfg.status_code == 200 else {}
        results.append({
            "check": "GET /api/manufacturers/search?q=Sun",
            "status": resp_mfg.status_code,
            "duration_ms": round(dur_mfg, 2),
            "total_matched": mfg_data.get("pagination", {}).get("total", 0),
            "returned_count": len(mfg_data.get("data", [])),
            "ok": resp_mfg.status_code == 200 and mfg_data.get("pagination", {}).get("total", 0) > 0
        })

        # 8: GTIN lookup for authentic/demo GTIN
        demo_gtin = "08901234001011"
        resp_gtin, dur_gtin = test_endpoint(client, "GET", f"/api/medicines/by-code/{demo_gtin}")
        gtin_data = resp_gtin.json() if resp_gtin.status_code == 200 else {}
        results.append({
            "check": f"GET /api/medicines/by-code/{demo_gtin}",
            "status": resp_gtin.status_code,
            "duration_ms": round(dur_gtin, 2),
            "brand_name": gtin_data.get("brand_name"),
            "generic_name": gtin_data.get("generic_name"),
            "ok": resp_gtin.status_code == 200 and bool(gtin_data.get("brand_name"))
        })

        # 9b: Regulatory Alerts endpoint
        resp_alerts, dur_alerts = test_endpoint(client, "GET", "/api/alerts", params={"limit": 5})
        alerts_data = resp_alerts.json() if resp_alerts.status_code == 200 else {}
        results.append({
            "check": "GET /api/alerts",
            "status": resp_alerts.status_code,
            "duration_ms": round(dur_alerts, 2),
            "total_alerts": alerts_data.get("pagination", {}).get("total", 0),
            "returned_count": len(alerts_data.get("data", [])),
            "ok": resp_alerts.status_code == 200
        })

        # 11: Pagination verification
        resp_p1, _ = test_endpoint(client, "GET", "/api/medicines/search", params={"q": "paracetamol", "page": 1, "limit": 10})
        resp_p2, _ = test_endpoint(client, "GET", "/api/medicines/search", params={"q": "paracetamol", "page": 2, "limit": 10})
        p1_data = resp_p1.json() if resp_p1.status_code == 200 else {}
        p2_data = resp_p2.json() if resp_p2.status_code == 200 else {}
        p1_ids = [m["medicine_id"] for m in p1_data.get("data", [])]
        p2_ids = [m["medicine_id"] for m in p2_data.get("data", [])]
        disjoint = set(p1_ids).isdisjoint(set(p2_ids)) and len(p1_ids) == 10 and len(p2_ids) == 10
        results.append({
            "check": "Pagination Check (Page 1 vs Page 2, limit=10)",
            "status": resp_p1.status_code,
            "duration_ms": None,
            "p1_count": len(p1_ids),
            "p2_count": len(p2_ids),
            "pages_disjoint": disjoint,
            "total_reported": p1_data.get("pagination", {}).get("total"),
            "ok": disjoint
        })

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_validations()
