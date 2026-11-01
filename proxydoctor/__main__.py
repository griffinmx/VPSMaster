from .cli import main

try:
    main()
except KeyboardInterrupt:
    import sys
    print('\n已中止 / Interrupted',file=sys.stderr)
    sys.exit(130)
