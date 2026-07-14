#!/usr/bin/env python3
"""Merge results-*.yaml from multiple workers into single results.yaml."""
import sys, os, yaml, glob

def main(run_id: str):
    base = os.path.expanduser("~/.openclaw/workspace/e2e-tests")
    run_dir = os.path.join(base, run_id)

    all_results = []
    for f in sorted(glob.glob(os.path.join(run_dir, "results-*.yaml"))):
        with open(f) as fh:
            data = yaml.safe_load(fh)
            if isinstance(data, list):
                all_results.extend(data)

    all_results.sort(key=lambda r: r.get("id", ""))

    out = os.path.join(run_dir, "results.yaml")
    with open(out, "w") as f:
        yaml.dump(all_results, f, allow_unicode=True, default_flow_style=False)

    print(out)

if __name__ == "__main__":
    main(sys.argv[1])
