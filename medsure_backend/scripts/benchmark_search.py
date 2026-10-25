"""Benchmark search performance before vs after optimization."""
import time
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
SEARCH_TERMS = ["paracetamol", "Dolo", "Crocin", "amoxicillin", "cefuroxime"]
RUNS_PER_TERM = 3  # Average over multiple runs to reduce cold-cache noise

def measure(client, term):
    times = []
    total_matched = None
    top_result = None
    status = None
    for _ in range(RUNS_PER_TERM):
        t0 = time.perf_counter()
        resp = client.get(f"{BASE_URL}/api/medicines/search", params={"q": term, "limit": 5})
        dur = (time.perf_counter() - t0) * 1000
        times.append(dur)
        if resp.status_code == 200:
            data = resp.json()
            total_matched = data.get("pagination", {}).get("total", 0)
            items = data.get("data", [])
            top_result = items[0]["brand_name"] if items else None
        status = resp.status_code
    return {
        "term": term,
        "status": status,
        "avg_ms": round(sum(times) / len(times), 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "total_matched": total_matched,
        "top_result": top_result,
    }

def run():
    print("=" * 65)
    print("  MedSure Search Performance Benchmark (Post-Optimization)")
    print("=" * 65)
    with httpx.Client(timeout=60.0) as client:
        # Warm-up
        client.get(f"{BASE_URL}/api/medicines/search", params={"q": "test", "limit": 1})

        results = []
        for term in SEARCH_TERMS:
            r = measure(client, term)
            results.append(r)
            print(f"  [{r['status']}] q={r['term']:<15}  "
                  f"avg={r['avg_ms']:>7.1f}ms  "
                  f"min={r['min_ms']:>7.1f}ms  "
                  f"matched={r['total_matched']:>7,}  "
                  f"top='{r['top_result']}'")

    avg_all = round(sum(r["avg_ms"] for r in results) / len(results), 1)
    print("-" * 65)
    print(f"  Average across all queries: {avg_all} ms")
    print("=" * 65)

if __name__ == "__main__":
    run()
