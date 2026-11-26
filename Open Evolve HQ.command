#!/bin/zsh
set -eu
cd -- "${0:A:h}"
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
if ! command -v python3 >/dev/null; then
  print 'Install Python 3, then double-click this launcher again. See docs/SETUP.md.'
  exit 1
fi
if [[ ! -f node_modules/three/build/three.module.js || ! -d node_modules/@fontsource-variable/geist ]]; then
  if ! command -v npm >/dev/null; then
    print 'Install Node.js, then double-click this launcher again. See docs/SETUP.md.'
    exit 1
  fi
  npm ci --ignore-scripts --no-audit --no-fund
fi
url='http://127.0.0.1:8739/'
if curl --noproxy '*' --silent --fail --max-time 2 "${url}api/providers" >/dev/null; then
  open "$url"
else
  exec python3 office/server.py --open
fi
