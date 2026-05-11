"""Test rate limiting on /api/ask endpoint."""
import requests
import time

API_URL = "http://localhost:8000/api/ask"

def test_rate_limit():
    """Send requests until rate limited."""
    
    print(" Testing rate limit (10 requests/minute)...\n")
    
    for i in range(12):
        try:
            response = requests.post(
                API_URL,
                json={
                    "query": f"How many days of leave? (test {i+1})",
                    "role": "employee",
                    "limit": 5
                },
                timeout=10
            )
            
            # Check rate limit headers
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            
            if response.status_code == 200:
                print(f" Request {i+1:2d}: Success | Remaining: {remaining}/{limit}")
                
            elif response.status_code == 429:
                data = response.json()
                print(f"\n Request {i+1:2d}: RATE LIMITED!")
                print(f"   Message: {data['detail']['message']}")
                print(f"   Retry after: {data['detail']['retry_after']}s")
                print(f"\n Rate limiting is working correctly!")
                break
                
            else:
                print(f" Request {i+1:2d}: Error {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f" Request {i+1:2d}: Connection error - {e}")
            print("   Make sure the backend is running!")
            break
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.3)
    
    else:
        print("\n Warning: Sent 12 requests without hitting rate limit!")
        print("   Rate limiting might not be working.")

if __name__ == "__main__":
    test_rate_limit()