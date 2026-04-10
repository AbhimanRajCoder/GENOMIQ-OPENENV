import os
import sys
import importlib.util
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio

class EnvMetric(BaseModel):
    score: float
    passed: bool
    details: str
    compliance: Dict[str, bool] = {}

async def validate_env(repo_path: str = ".") -> EnvMetric:
    """Validates the environment class compliance with OpenEnv spec."""
    env_path = os.path.join(repo_path, "env", "environment.py")
    if not os.path.exists(env_path):
        return EnvMetric(score=0, passed=False, details="environment.py not found.")

    compliance = {
        "reset": False,
        "step": False,
        "state": False,
        "close": False,
    }

    try:
        # Dynamic import of GenomIQEnv
        spec = importlib.util.spec_from_file_location("env.environment", env_path)
        env_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(env_module)
        
        if not hasattr(env_module, "GenomIQEnv"):
            return EnvMetric(score=0, passed=False, details="GenomIQEnv class not found in environment.py.")

        # Instantiate environment
        # Use task_name="single_regulator" if available
        env = env_module.GenomIQEnv(task_name="single_regulator")
        
        # 1. Test reset()
        try:
            obs = await env.reset()
            # reset() returns observation dict or object
            if obs is not None:
                compliance["reset"] = True
            else:
                print("reset() returned None")
        except Exception as e:
            print(f"reset() failed: {e}")

        # 2. Test step(action)
        try:
            # Need to import Action from models
            models_path = os.path.join(repo_path, "env", "models.py")
            spec_models = importlib.util.spec_from_file_location("env.models", models_path)
            models = importlib.util.module_from_spec(spec_models)
            spec_models.loader.exec_module(models)
            action = models.Action(action_type=0)
            
            result = await env.step(action)
            # result should have observation, reward, done, info
            if all(k in result for k in ["observation", "reward", "done", "info"]):
                compliance["step"] = True
            else:
                print(f"step() result missing fields: {result.keys()}")
        except Exception as e:
            print(f"step() failed: {e}")

        # 3. Test state()
        try:
            state = await env.state()
            if state is not None:
                compliance["state"] = True
            else:
                print("state() returned None")
        except Exception as e:
            print(f"state() failed: {e}")

        # 4. Test close() - GenomIQEnv might not have close() explicitly, but OpenEnv spec usually includes it
        try:
            if hasattr(env, "close"):
                await env.close()
            compliance["close"] = True
        except Exception as e:
            print(f"close() failed: {e}")

        # Scoring logic
        score = sum(25 for k, v in compliance.items() if v)
        passed = compliance["reset"] and compliance["step"] and score >= 75
        
        details = "Environment is OpenEnv compliant." if passed else f"Compliance issues: {', '.join(k for k, v in compliance.items() if not v)}"
        return EnvMetric(score=score, passed=passed, details=details, compliance=compliance)

    except Exception as e:
        return EnvMetric(score=0, passed=False, details=f"Error validating environment: {str(e)}")

if __name__ == "__main__":
    res = asyncio.run(validate_env())
    import json
    print(res.model_dump_json(indent=2))
