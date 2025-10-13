#!/usr/bin/env bash

set -euo pipefail

if ! command -v mmdc >/dev/null 2>&1; then
  echo "Mermaid CLI (mmdc) is not installed. Install with: npm install -g @mermaid-js/mermaid-cli" >&2
  exit 1
fi

shopt -s nullglob

CONFIG_DEFAULT='{
  "args": ["--no-sandbox", "--disable-setuid-sandbox"]
}'

CONFIG="${MERMAID_PUPPETEER_CONFIG:-docs/diagrams/puppeteer-config.json}"

if [[ ! -f "$CONFIG" ]]; then
  mkdir -p "$(dirname "$CONFIG")"
  printf '%s\n' "$CONFIG_DEFAULT" > "$CONFIG"
fi

declare -a targets=()

if (( $# > 0 )); then
  for arg in "$@"; do
    if [[ -f "$arg" ]]; then
      targets+=("$arg")
    else
      echo "Skipping missing file: $arg" >&2
    fi
  done
else
  shopt -s globstar
  for pattern in docs/diagrams/**/*.mmd docs/diagrams/**/*.md; do
    for file in $pattern; do
      targets+=("$file")
    done
  done
fi

if (( ${#targets[@]} == 0 )); then
  echo "No Mermaid diagram sources found." >&2
  exit 0
fi

render_mmd() {
  local input="$1"
  local dir base output
  dir="$(dirname "$input")"
  base="$(basename "$input" .mmd)"
  output="${dir}/${base}.svg"

  mmdc -p "$CONFIG" -i "$input" -o "$output"
  echo "Rendered ${input} -> ${output}"
}

render_markdown() {
  local input="$1"
  local dir base tmp count svg target suffix

  if ! grep -q '```mermaid' "$input"; then
    echo "No mermaid code blocks in ${input}; skipping." >&2
    return
  fi

  dir="$(dirname "$input")"
  base="$(basename "$input" .md)"
  tmp="$(mktemp -d)"

  mmdc -p "$CONFIG" -i "$input" -o "$tmp"

  count=0
  for svg in "$tmp"/*.svg; do
    ((count++))
    suffix=""
    if (( count > 1 )); then
      suffix="-${count}"
    fi
    target="${dir}/${base}${suffix}.svg"
    mv "$svg" "$target"
    echo "Rendered ${input} -> ${target}"
  done

  if (( count == 0 )); then
    echo "Mermaid CLI did not emit any SVGs for ${input}" >&2
  fi

  rm -rf "$tmp"
}

for file in "${targets[@]}"; do
  case "$file" in
    *.mmd) render_mmd "$file" ;;
    *.md) render_markdown "$file" ;;
    *) echo "Unsupported file type (expected .mmd or .md): $file" >&2 ;;
  esac
done
