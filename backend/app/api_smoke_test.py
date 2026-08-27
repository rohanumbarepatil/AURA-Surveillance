import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, path, expected_status=200):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            
            if status == expected_status:
                print(f"[SUCCESS] {method} {path} - OK ({status})")
                return json.loads(body) if body else None
            else:
                print(f"[FAIL] {method} {path} - Failed (Expected {expected_status}, got {status})")
                return None
    except urllib.error.HTTPError as e:
        if e.code == expected_status:
            print(f"[SUCCESS] {method} {path} - OK ({e.code})")
        else:
            print(f"[FAIL] {method} {path} - Failed (Expected {expected_status}, got {e.code})")
        return None
    except Exception as e:
        print(f"[FAIL] {method} {path} - Exception: {e}")
        return None

def run_tests():
    print("=" * 60)
    print("AURA SURVEILLANCE - API SMOKE TEST")
    print("=" * 60)
    
    # Wait a bit for server to pick up changes
    time.sleep(2)
    
    # 1. Health
    test_endpoint("GET", "/api/health")
    
    # 2. Events Stats
    stats = test_endpoint("GET", "/api/events/stats")
    if stats:
        print(f"   Stats: Total={stats.get('total_events')}, Active={stats.get('active_events')}")
        
    # 3. Events List
    events = test_endpoint("GET", "/api/events")
    
    # 4. Active Events
    test_endpoint("GET", "/api/events/active")
    
    # 5. Cameras
    test_endpoint("GET", "/api/cameras")
    
    # 6. Single Event and Resolve (if events exist)
    if events and len(events) > 0:
        event_id = events[0].get("event_id")
        print(f"   Found event to test: {event_id}")
        
        # Single Event
        test_endpoint("GET", f"/api/events/{event_id}")
        
        # Resolve Event
        test_endpoint("PATCH", f"/api/events/{event_id}/resolve")
    else:
        print("   No events found to test single/resolve endpoints. Skipping.")
        
    print("=" * 60)
    print("API SMOKE TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
