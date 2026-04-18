"""Command modules for the logseq CLI.

Each module exports HANDLERS (dict[str, callable]) and register(subparsers).
The main dispatcher in logseq.py calls register() on each module in a fixed
order and dispatches by the args.func set_default on each subparser.
"""
