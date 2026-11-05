import traceback
import sys

try:
    import app.main
    print("SUCCESS")
except Exception as e:
    with open("error.txt", "w") as f:
        traceback.print_exc(file=f)
    print("Wrote error to error.txt")
    sys.exit(1)
