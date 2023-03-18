#! /bin/env python3

from SmplCompiler import SmplCompiler, SmplCDebug
from IRVis import IRVis

import argparse
import os


def getArgs():
    parser = argparse.ArgumentParser(description="SMPL compiler")
    parser.add_argument("-i", dest="src", type=str,
                        required=True, help="source file")
    parser.add_argument("-d", dest="debug", type=str,
                        help="debug output from the tokenizer")
    parser.add_argument("-v", action="store_true",
                        dest="verbose", default=False, help="verbose mode")
    return parser.parse_args()


def main() -> None:
    # Get args
    args = getArgs()
    debug = args.debug if args.debug else "debug.txt"

    # Run compiler
    smplCompiler = SmplCompiler(args.src, debug=SmplCDebug(file=debug))
    smplCompiler.computation()
    smplCompiler.debug.dump()

    # Visualiation of blocks
    vis_file = os.path.join(
        "graph", os.path.splitext(os.path.basename(args.src))[0] + ".dot")
    vis = IRVis(filename=vis_file, debug=args.verbose)
    smplCompiler.vis(vis)
    vis.render()


if __name__ == "__main__":
    main()
