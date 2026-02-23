
import os
out = os.environ.get("OUTPUT_DIR", ".")
path = os.path.join(out, "results", "test.txt")
os.makedirs(os.path.dirname(path), exist_ok=True)
open(path, "w").write("ok")
