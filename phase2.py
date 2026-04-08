import subprocess
import sys
import re

EPS = 1e-6

def fail(msg):
    print("\n❌ Phase 2 Failed")
    print(msg)
    print("\nPhase 2 is fail-fast. Fix this and resubmit.\n")
    sys.exit(1)

def pass_msg():
    print("\n✅ Phase 2 Passed — All task scores valid\n")

def extract_scores(output: str):
    """
    Extract scores from inference logs.
    Supports patterns like:
    [END] score=0.234
    score: 0.234
    """
    scores = []

    # match floats between 0 and 1
    matches = re.findall(r"(?:score\s*[:=]\s*)([0-9]*\.?[0-9]+)", output)

    for m in matches:
        try:
            scores.append(float(m))
        except:
            pass

    return scores

def main():
    print("🔍 Running inference.py...\n")

    try:
        result = subprocess.run(
            [sys.executable, "inference.py"],
            capture_output=True,
            text=True,
            timeout=1200  # 20 min limit
        )
    except subprocess.TimeoutExpired:
        fail("Inference exceeded 20 min runtime limit")

    output = result.stdout + "\n" + result.stderr

    print("📄 Inference Output (last 20 lines):\n")
    print("\n".join(output.splitlines()[-20:]))

    if result.returncode != 0:
        fail("Inference script crashed or returned non-zero exit code")

    scores = extract_scores(output)

    if len(scores) < 3:
        fail("Less than 3 task scores found (minimum required = 3)")

    print("\n📊 Extracted Scores:", scores)

    # 🚨 STRICT VALIDATION
    for i, s in enumerate(scores):
        if not (0 < s < 1):
            fail(f"Task {i+1} score out of range: {s} (must be strictly between 0 and 1)")

    # 🚨 variance check (important hidden check)
    if len(set(scores)) == 1:
        fail("All task scores are identical → grader is constant (disqualification risk)")

    print("\n📈 Score variance OK")

    pass_msg()


if __name__ == "__main__":
    main()