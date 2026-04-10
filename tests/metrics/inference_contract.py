import ast
import os
import subprocess
import sys
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Add project root to sys.path to allow absolute imports from tests package
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from tests.metrics.stdout_format import validate_stdout

class ContractMetric(BaseModel):
    score: float
    passed: bool
    details: str
    checks: Dict[str, bool] = {}

def validate_inference_contract(repo_path: str = ".") -> ContractMetric:
    """Validates inference.py exists in repo root, reads correct env vars, uses OpenAI client."""
    inference_path = os.path.join(repo_path, "inference.py")
    if not os.path.exists(inference_path):
        return ContractMetric(score=0, passed=False, details="inference.py not found in repo root.")

    checks = {
        "api_base_url_default": False,
        "model_name_default": False,
        "hf_token_no_default": False,
        "openai_import": False,
        "openai_client_create": False,
    }

    try:
        with open(inference_path, "r") as f:
            tree = ast.parse(f.read())

        # Scan AST for os.getenv calls and openai usage
        for node in ast.walk(tree):
            # Check for os.getenv calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "getenv":
                    # Check first argument
                    if node.args and isinstance(node.args[0], ast.Constant):
                        env_var = node.args[0].value
                        if env_var == "API_BASE_URL":
                            # Check if it has a default value (second argument)
                            if len(node.args) > 1 or node.keywords:
                                checks["api_base_url_default"] = True
                        elif env_var == "MODEL_NAME":
                            if len(node.args) > 1 or node.keywords:
                                checks["model_name_default"] = True
                        elif env_var == "HF_TOKEN":
                            # HF_TOKEN must have NO default value (mandatory)
                            if len(node.args) == 1 and not node.keywords:
                                checks["hf_token_no_default"] = True
            
            # Check for openai import
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "openai":
                        checks["openai_import"] = True
            if isinstance(node, ast.ImportFrom):
                if node.module == "openai" or node.module == "openai.resources.chat.completions":
                    checks["openai_import"] = True
            
            # Check for client.chat.completions.create call
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "create":
                    # Check if it's chat.completions.create
                    if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "completions":
                        checks["openai_client_create"] = True

        # Scoring logic
        score = sum(20 for k, v in checks.items() if v)
        passed = all(checks.values()) and score >= 80
        
        details = "Inference contract is valid." if passed else f"Contract issues: {', '.join(k for k, v in checks.items() if not v)}"
        
        # Additionally, validate stdout format (dry run with mocked environment)
        # Note: this might fail if LLM is not available, but let's try it for format
        # Use stdout_format module to validate the actual output format
        stdout_res = validate_stdout(inference_path)
        if not stdout_res.passed:
            score -= 20
            details += f" | Stdout format check failed: {stdout_res.details}"

        score = max(0, score)
        return ContractMetric(score=score, passed=passed, details=details, checks=checks)

    except Exception as e:
        return ContractMetric(score=0, passed=False, details=f"Error parsing inference.py: {str(e)}")

if __name__ == "__main__":
    res = validate_inference_contract()
    import json
    print(res.model_dump_json(indent=2))
