import argparse
import sys

import argcomplete


def setup_root_parser(root_parser: argparse.ArgumentParser):
    args = sys.argv[1:]
    if "--" in args:
        idx = args.index("--")
        pre_args = args[:idx]
        post_args = args[idx + 1 :]
    else:
        pre_args = args
        post_args = []

    argcomplete.autocomplete(root_parser)
    args, unknown_args = root_parser.parse_known_args(pre_args)

    if unknown_args:
        root_parser.error(f"Unknown arguments before '--': {unknown_args}")

    if not args.command:
        root_parser.print_help()
        sys.exit(1)

    args.func(**vars(args), extra_args=post_args)
