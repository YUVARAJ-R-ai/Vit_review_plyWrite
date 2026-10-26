{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "vit-feedback-dev";

  buildInputs = [
    pkgs.python312Full
    pkgs.uv
    pkgs.brave
  ];

  shellHook = ''
    export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
    if [ ! -d ".venv" ]; then
      echo "Creating virtualenv..."
      uv venv .venv
    fi
    source .venv/bin/activate
  '';
}
