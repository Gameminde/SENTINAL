from pathlib import Path
import subprocess, sys, os, json, requests, uuid

SUPABASE_URL = "https://wpdtgfashbtlkdcuachh.supabase.co"
VAL_ID       = str(uuid.uuid4())
USER_ID      = "ba3c9bf1-eac2-40f5-8b81-dee1b7e6cb28"
IDEA         = ("AI-powered code review tool for solo developers and small teams "
                "who can't afford a senior engineer — automatically reviews pull "
                "requests, catches bugs, suggests improvements, and explains why "
                "changes matter, without needing a team member to review")

def load_service_key(env_path: Path = Path("app/.env.local")) -> str:
    if not env_path.exists():
        raise FileNotFoundError(f"{env_path} is required for this live validation smoke test.")

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("SUPABASE_SERVICE_ROLE_KEY="):
            return line.split("=", 1)[1]
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY was not found in app/.env.local.")


def main() -> int:
    service_key = load_service_key()
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    print(f"[OK] user_id = {USER_ID}")
    print(f"[OK] val_id  = {VAL_ID}")

    print("[DB] Inserting validation row...")
    response = requests.post(
        SUPABASE_URL + "/rest/v1/idea_validations",
        json={"id": VAL_ID, "user_id": USER_ID, "idea_text": IDEA, "model": "multi-brain", "status": "queued"},
        headers=headers,
        timeout=10,
    )
    print(f"[DB] Insert: {response.status_code} {response.text[:100]}")
    if response.status_code not in (200, 201):
        print("[FATAL] Insert failed, aborting.")
        return 1

    config = {"validation_id": VAL_ID, "idea": IDEA, "user_id": USER_ID}
    with open("test_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f)

    print(f"\n[>>>] Launching validation...\n{'='*60}")

    env = os.environ.copy()
    env["SUPABASE_URL"] = SUPABASE_URL
    env["SUPABASE_KEY"] = service_key
    env["SUPABASE_SERVICE_KEY"] = service_key
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [sys.executable, "validate_idea.py", "--config-file", "test_config.json"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    if proc.stdout is not None:
        for line in proc.stdout:
            print(line, end="", flush=True)

    proc.wait()
    print(f"\n{'='*60}\n[DONE] Exit code: {proc.returncode}")
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
