Functional Requirements
1. Real-World Task Simulation
The environment must represent tasks that humans actually perform in real settings—no games or toy problems.
Examples include email triage, code review, data cleaning, scheduling, customer support, and content moderation.

2. OpenEnv Specification Compliance
The environment must fully implement the OpenEnv interface, including:
Typed Observation, Action, and Reward models using Pydantic
step(action) → returns (observation, reward, done, info)
reset() → returns the initial observation
state() → returns the current state
An openenv.yaml file containing metadata
The implementation must successfully pass validation via openenv validate.

3. Minimum of Three Tasks with Agent Graders
Provide at least three tasks, each with a clearly defined objective
Tasks should span increasing difficulty: easy → medium → hard
Each task must include a programmatic grader that assigns a score between 0.0 and 1.0
Grading criteria must be clear, deterministic, and reproducible

4. Meaningful Reward Function
The reward function must provide feedback throughout the task trajectory, not just at completion
It should reward incremental progress toward the objective
It must penalize undesirable behaviors such as infinite loops or destructive actions

5. Baseline Inference Script
Include an inference script that uses the OpenAI API client to evaluate a model within the environment
API credentials must be read from environment variables (HF_TOKEN)
The script should produce a reproducible baseline score across all tasks

Non-Functional Requirements
1. Deployment on Hugging Face Spaces
The environment must be deployable as a containerized Hugging Face Space
It should be tagged with openenv

2. Containerized Execution
Provide a working Dockerfile
The environment must build and run successfully using:
docker build
docker run

3. Documentation
The README must include:
Environment overview and motivation
Definitions of action and observation spaces
Task descriptions with expected difficulty levels
Setup and usage instructions
Baseline performance scores


Additional Guideline: Meta OpenEnv Hackathon: Guidelines

🚀 Hackathon Submission Guidelines (OpenEnv RL Challenge)
1. Project Structure
Your inference script must be named inference.py
It must be located in the root directory of your project



2. LLM Usage Requirements
You must use the OpenAI Client for all LLM calls
Do not use alternative SDKs or direct HTTP calls



3. Required Environment Variables
Your inference.py must read the following environment variables:
API_BASE_URL
Description: API endpoint for the LLM
Requirement: Must include a default value
MODEL_NAME
Description: Model identifier used for inference
Requirement: Must include a default value
HF_TOKEN
Description: Hugging Face API token
Requirement: Mandatory (no default required)

4. INFERENCE OUTPUT FORMAT
The script must emit exactly three line types to stdout, in this order:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>



  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw last_action_error string, or null if none.
    - All fields on a single line with no newlines within a line.
  Example:
    [START] task=click-test env=miniwob model=Qwen3-VL-30B
    [STEP] step=1 action=click('123') reward=0.00 done=false error=null
    [STEP] step=2 action=fill('456','text') reward=0.00 done=false error=null
    [STEP] step=3 action=click('789') reward=1.00 done=true error=null
    [END] success=true steps=3 rewards=0.00,0.00,1.00
✅ Example (inference.py)
import os
from openai import OpenAI

# Read environment variables with defaults where required
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# Initialize OpenAI client
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

def run_inference(prompt: str):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    response = response.choices[0].message.content
    # Print output based on above given format


if __name__ == "__main__":
    print(run_inference("Hello from OpenEnv!"))

4. Hugging Face Space Guidelines
Building a Hugging Face Space can take significant time, especially if multiple spaces are active
To avoid delays:
Turn off all unnecessary spaces
Keep only your primary submission space running

5. Submission Validation Rules
The system will check if your Hugging Face Space is live
If your space is not in a running state, your submission will fail automatically
Before submitting:
Ensure your space is fully built
Confirm it is in the “Running” state

6. Hardware Requirements
Your solution will be executed inside a Docker container with limited resources
It must run within the following constraints:
2 vCPU
8 GB RAM
👉 Ensure your model, dependencies, and runtime fit within these limits. Submissions exceeding these constraints may fail during evaluation.

6. Resubmissions
You are allowed to resubmit your project multiple times
If your submission fails validation, you can:
Fix the issues
Ensure your Hugging Face Space is running
Submit again
👉 There is no penalty for resubmitting, so iterate until your submission passes all checks.

⚠️ Common Failure Cases (Avoid These)
inference.py not in root directory
Missing default values for API_BASE_URL or MODEL_NAME
Missing HF_TOKEN
Hugging Face Space still building during submission
Space stopped due to multiple active deployments

🚀  Reference projects to guide you
Here are some strong examples from the San Francisco edition to help you understand how to structure your environment:
Calendar Environment Server
https://github.com/meta-pytorch/OpenEnv/tree/main/envs/calendar_env
Reasoning Gym Environment Server
https://github.com/meta-pytorch/OpenEnv/tree/main/envs/reasoning_gym_env
TB2 Environment Server
https://github.com/meta-pytorch/OpenEnv/tree/main/envs/tbench2_env
CARLA Environment Server
https://github.com/meta-pytorch/OpenEnv/tree/main/envs/carla_env
REPL Environment Server
https://github.com/meta-pytorch/OpenEnv/tree/main/envs/repl_env
Use these as direction, not as templates. Focus on understanding structure and approach.

