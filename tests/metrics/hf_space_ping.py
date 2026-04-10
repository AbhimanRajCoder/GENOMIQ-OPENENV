import requests
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class PingMetric(BaseModel):
    score: float
    passed: bool
    details: str
    response_time: float = 0.0

def validate_hf_space_ping(hf_space_url: str) -> PingMetric:
    """Pings HF Space /reset endpoint, checks 200 OK."""
    if not hf_space_url:
        return PingMetric(score=0, passed=False, details="HF_SPACE_URL not provided.")

    hf_space_url = hf_space_url.rstrip("/")
    reset_endpoint = f"{hf_space_url}/reset"
    
    start_time = time.time()
    try:
        # POST /reset with empty JSON body {}
        response = requests.post(reset_endpoint, json={}, timeout=30)
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            # Check for JSON response and expected observation
            try:
                data = response.json()
                if "observation" in data or "task_name" in data:
                    return PingMetric(
                        score=100.0, 
                        passed=True, 
                        details=f"HF Space /reset returned 200 OK in {response_time:.2f}s.",
                        response_time=response_time
                    )
                else:
                    return PingMetric(
                        score=50, 
                        passed=False, 
                        details=f"HF Space /reset returned 200 OK but response shape is unexpected: {data.keys()}",
                        response_time=response_time
                    )
            except Exception as e:
                return PingMetric(
                    score=60, 
                    passed=False, 
                    details=f"HF Space /reset returned 200 OK but JSON parsing failed: {str(e)}",
                    response_time=response_time
                )
        else:
            return PingMetric(
                score=0, 
                passed=False, 
                details=f"HF Space /reset returned HTTP {response.status_code}. Response: {response.text[:200]}",
                response_time=response_time
            )
            
    except requests.exceptions.Timeout:
        return PingMetric(score=0, passed=False, details="HF Space /reset timed out (30s).")
    except requests.exceptions.ConnectionError:
        return PingMetric(score=0, passed=False, details=f"Failed to connect to HF Space at {reset_endpoint}.")
    except Exception as e:
        return PingMetric(score=0, passed=False, details=f"Error pinging HF Space: {str(e)}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    res = validate_hf_space_ping(url)
    import json
    print(res.model_dump_json(indent=2))
