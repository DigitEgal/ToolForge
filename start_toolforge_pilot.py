"""Entry point: python start_toolforge_pilot.py"""
import sys
import traceback

if __name__ == '__main__':
    try:
        if sys.version_info < (3, 10):
            raise RuntimeError('Python 3.10 oder neuer erforderlich; empfohlen: dein vorhandenes Python 3.11.')
        from toolforge_pilot.gui import main
        main()
    except Exception:
        traceback.print_exc()
        print('\nStart fehlgeschlagen. Bitte die vollständige Fehlermeldung weitergeben.')
        sys.exit(1)
