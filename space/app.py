"""Entry point for the Caracat Code Hugging Face Space.

A Space runs on a server somewhere else, which changes what makes sense to
offer. Three things are deliberately absent here, and each for its own reason:

- **Running code is impossible, not merely switched off.** The route is only
  registered when the server is bound to a local address, and a container never
  is. Without that rule, anyone who found the address could run programs on the
  Space.
- **There is no project directory.** The files worth reading live on your own
  machine, not in this container.
- **Conversations are not stored server-side.** One Space is one server: saved
  chats would be shared by everyone who can open the page. They stay in the
  browser tab instead.

For those three, run the interface locally:

    python scripts/serve_interface.py --project-dir ~/your-project

The API key comes from the ``CARACAT_API_KEY`` Space secret. It stays in this
process -- the page never receives it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from caracat_code.interface import InterfaceConfigError, resolve_config  # noqa: E402
from caracat_code.persona import PersonaError, load_persona  # noqa: E402
from caracat_code.server import ServerOptions, create_server, read_index  # noqa: E402

DEFAULT_PORT = 7860  # what Hugging Face expects a Docker Space to listen on


def main() -> int:
    try:
        config = resolve_config(
            host="0.0.0.0",  # a container must accept connections from outside
            port=int(os.environ.get("PORT", DEFAULT_PORT)),
        )
    except InterfaceConfigError as exc:
        print(
            f"Cannot start:\n\n{exc}\n\n"
            "On a Space, set CARACAT_API_KEY under Settings > Variables and "
            "secrets. Add it as a *secret*, not a variable: a variable is "
            "visible to anyone who can see the Space.",
            file=sys.stderr,
        )
        return 2

    try:
        system_prompt = load_persona(HERE / "prompts" / "caracat_persona.md")
    except PersonaError as exc:
        print(f"Cannot start:\n\n{exc}", file=sys.stderr)
        return 2

    options = ServerOptions(
        config=config,
        index_html=read_index(HERE / "interface" / "index.html"),
        system_prompt=system_prompt,
        workspace=None,  # no project files on a hosted server
        conversations=None,  # one server, many visitors: no shared store
    )

    server = create_server(options)
    print(f"Caracat Code on {config.host}:{config.port}")
    print(f"Provider:    {config.api_base}")
    print(f"Personality: {len(system_prompt)} characters")
    print("Running code: disabled (not bound to a local address)")
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
