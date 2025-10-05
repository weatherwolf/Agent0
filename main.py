from orchestrator import run
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use Thinker Agent with user request
        user_request = " ".join(sys.argv[1:])
        run(user_request)
    else:
        # Use standalone mode
        run()