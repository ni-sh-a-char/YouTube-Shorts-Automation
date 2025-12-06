import sys
from pathlib import Path

# Ensure project root is available
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scheduler import run_once_and_exit

if __name__ == "__main__":
    print("=== Starting GitHub Actions YouTube Shorts Generation ===")
    try:
        result = run_once_and_exit()
        print("=== Generation Complete ===")
        print(result)
    except Exception as e:
        print("❌ Pipeline failed:")
        print(e)
        raise
