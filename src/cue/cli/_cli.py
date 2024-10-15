import sys


def main() -> int:
    try:
        print("cue cli")
        return 0
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
