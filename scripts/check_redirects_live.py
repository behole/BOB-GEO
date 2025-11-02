#!/usr/bin/env python3
import sys
import requests

def main():
    ok = True
    for path in ("ai.txt", "llms.txt"):
        url = f"https://brushonblock.com/{path}"
        try:
            r = requests.get(url, timeout=20)
            print(f"{path} -> {r.status_code} ({len(r.content)} bytes)")
            if r.status_code != 200:
                ok = False
        except Exception as e:
            print(f"{path} -> request failed: {e}")
            ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

