#!/usr/bin/env python3
"""Initialize E2E test run: generate UUID, create directory, write meta."""
import uuid, os, sys, yaml
from datetime import datetime, timezone, timedelta

def main(url: str):
    run_id = str(uuid.uuid4())
    base = os.path.expanduser("~/.openclaw/workspace/e2e-tests")
    run_dir = os.path.join(base, run_id)
    screenshots_dir = os.path.join(run_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    tz = timezone(timedelta(hours=8))
    meta = {
        "uuid": run_id,
        "url": url,
        "started_at": datetime.now(tz).isoformat(),
        "status": "initialized"
    }
    with open(os.path.join(run_dir, "meta.yaml"), "w") as f:
        yaml.dump(meta, f, allow_unicode=True)

    print(run_id)

if __name__ == "__main__":
    main(sys.argv[1])
