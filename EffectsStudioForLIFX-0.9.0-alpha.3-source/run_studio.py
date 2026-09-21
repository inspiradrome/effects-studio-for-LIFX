"""Developer entry point for Effects Studio for LIFX."""

from __future__ import annotations

import argparse
import multiprocessing
import sys
import threading
import webbrowser
from pathlib import Path

from effects_studio import __version__

# PyInstaller's multiprocessing hook must run before importing networking
# packages that may inspect or initialize multiprocessing support.
multiprocessing.freeze_support()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-lifx", action="store_true", help="run the GUI without lamp output")
    parser.add_argument("--serial", help="override the saved LIFX Tube serial")
    parser.add_argument("--ip", help="override the saved LIFX Tube IPv4 address")
    parser.add_argument("--brightness", type=float, help="Tube brightness from 0 to 1")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.smoke_test:
        _smoke_test()
        return

    # Keep the packaging smoke test independent of the networking stack, and
    # defer its comparatively expensive imports until a real launch.
    from effects_studio.lifx_output import TubeOutputConfig, load_saved_config
    from effects_studio.server import create_app

    if args.brightness is not None and not 0 < args.brightness <= 1:
        parser.error("--brightness must be greater than 0 and no more than 1")
    if bool(args.serial) != bool(args.ip):
        parser.error("--serial and --ip must be supplied together")

    if not args.no_browser:
        url = f"http://{args.host}:{args.port}"
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()

    output_config = None
    if not args.no_lifx:
        saved_config = load_saved_config()
        if args.serial and args.ip:
            output_config = TubeOutputConfig(
                serial=args.serial.lower(),
                ip=args.ip,
                brightness=args.brightness if args.brightness is not None else 0.72,
            )
        elif saved_config:
            output_config = TubeOutputConfig(
                serial=saved_config.serial,
                ip=saved_config.ip,
                brightness=(
                    args.brightness if args.brightness is not None else saved_config.brightness
                ),
            )
        elif args.brightness is not None:
            parser.error("--brightness needs a saved Tube or explicit --serial and --ip")

    app = create_app(output_config)
    app.run(
        host=args.host,
        port=args.port,
        access_log=False,
        single_process=True,
    )


def _smoke_test() -> None:
    if getattr(sys, "frozen", False):
        static_dir = Path(sys._MEIPASS) / "effects_studio" / "static"  # type: ignore[attr-defined]
    else:
        static_dir = Path(__file__).resolve().parent / "effects_studio" / "static"
    required_assets = (
        "index.html",
        "app.css",
        "library.css",
        "workshop.css",
        "i18n.js",
        "app.js",
    )
    missing = [name for name in required_assets if not (static_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"Missing packaged web assets: {', '.join(missing)}")
    if sys.stdout is not None:
        print(f"Effects Studio for LIFX {__version__}: smoke test passed")


if __name__ == "__main__":
    main()
