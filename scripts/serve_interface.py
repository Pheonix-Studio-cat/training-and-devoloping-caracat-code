#!/usr/bin/env python3
"""Serve the local Caracat Code interface.

Starts a small web server on your own machine that serves the page in
``interface/index.html`` and forwards chat requests to an OpenAI-compatible
provider. The API key stays in this process: the browser never receives it.

    export CARACAT_API_KEY='...'
    python scripts/serve_interface.py

Then open http://127.0.0.1:8765 in a browser.

Any OpenAI-compatible endpoint works, including local runtimes:

    python scripts/serve_interface.py --api-base http://localhost:11434/v1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running the script directly from a checkout, without installing.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from caracat_code.conversations import (  # noqa: E402
    ConversationError,
    ConversationStore,
    default_store_path,
)
from caracat_code.interface import (  # noqa: E402
    DEFAULT_API_BASE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    InterfaceConfigError,
    resolve_config,
)
from caracat_code.persona import (  # noqa: E402
    DEFAULT_PERSONA_PATH,
    PersonaError,
    load_persona,
)
from caracat_code.server import (  # noqa: E402
    ServerOptions,
    create_server,
    read_index,
)
from caracat_code.workspace import Workspace, WorkspaceError  # noqa: E402

INDEX_PATH = Path(__file__).resolve().parent.parent / "interface" / "index.html"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve the local Caracat Code interface.",
        epilog=(
            "The API key is read from CARACAT_API_KEY and is never sent to the "
            "browser. There is no flag for it on purpose: a key passed on the "
            "command line ends up in your shell history."
        ),
    )
    parser.add_argument(
        "--api-base",
        help=(
            "OpenAI-compatible base URL "
            f"(default: {DEFAULT_API_BASE}, or CARACAT_API_BASE)."
        ),
    )
    parser.add_argument(
        "--model",
        help="Model to preselect, e.g. a Qwen3-Coder-Next identifier from your "
        "provider. Can also be chosen in the interface.",
    )
    parser.add_argument("--host", help=f"Address to bind to (default: {DEFAULT_HOST}).")
    parser.add_argument(
        "--port", type=int, help=f"Port to listen on (default: {DEFAULT_PORT})."
    )

    persona = parser.add_argument_group("personality")
    persona.add_argument(
        "--persona",
        type=Path,
        help=f"Personality file to load (default: {DEFAULT_PERSONA_PATH}).",
    )
    persona.add_argument(
        "--no-persona",
        action="store_true",
        help="Start without a default system prompt.",
    )

    project = parser.add_argument_group("project files")
    project.add_argument(
        "--project-dir",
        type=Path,
        help=(
            "Directory Caracat Code may read from. Nothing outside it is "
            "reachable. Files that hold credentials are refused by name, and "
            "everything else is scanned before it is sent anywhere."
        ),
    )
    saving = parser.add_argument_group("conversations")
    saving.add_argument(
        "--conversations-dir",
        type=Path,
        help=(
            "Where conversations are stored "
            f"(default: {default_store_path()}). Deliberately outside the "
            "repository, so they are never committed by accident."
        ),
    )
    saving.add_argument(
        "--no-save", action="store_true", help="Do not store conversations at all."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = resolve_config(
            api_base=args.api_base,
            model=args.model,
            host=args.host,
            port=args.port,
        )
    except InterfaceConfigError as exc:
        print(f"Cannot start the interface:\n\n{exc}", file=sys.stderr)
        return 2

    system_prompt: str | None = None
    if not args.no_persona:
        try:
            system_prompt = load_persona(args.persona)
        except PersonaError as exc:
            print(f"Cannot start the interface:\n\n{exc}", file=sys.stderr)
            return 2

    workspace: Workspace | None = None
    if args.project_dir is not None:
        try:
            workspace = Workspace.open(args.project_dir)
        except WorkspaceError as exc:
            print(f"Cannot start the interface:\n\n{exc}", file=sys.stderr)
            return 2

    conversations: ConversationStore | None = None
    if not args.no_save:
        try:
            conversations = ConversationStore.open(args.conversations_dir)
        except ConversationError as exc:
            print(f"Cannot start the interface:\n\n{exc}", file=sys.stderr)
            return 2

    try:
        index_html = read_index(INDEX_PATH)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    options = ServerOptions(
        config=config,
        index_html=index_html,
        system_prompt=system_prompt,
        workspace=workspace,
        conversations=conversations,
    )

    if not config.is_local_only:
        print(
            f"WARNING: binding to {config.host} makes this interface reachable "
            "from other machines. Anyone who can reach it can spend your API "
            "key. Use the default 127.0.0.1 unless you know you want this.",
            file=sys.stderr,
        )

    server = create_server(options)
    persona_note = f"{len(system_prompt)} characters" if system_prompt else "(none)"
    print(f"Caracat Code interface: http://{config.host}:{config.port}")
    print(f"Provider:    {config.api_base}")
    print(f"Model:       {config.model or '(choose one in the interface)'}")
    print(f"Personality: {persona_note}")
    print(
        f"Project:     {workspace.root if workspace else '(none, use --project-dir)'}"
    )
    print(f"Saved chats: {conversations.root if conversations else '(off)'}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
