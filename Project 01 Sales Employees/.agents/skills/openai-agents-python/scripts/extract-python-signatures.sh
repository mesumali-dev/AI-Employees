#!/bin/bash
# Extract Python API signatures using awk
# Finds function definitions, class definitions, decorators

set -euo pipefail

MAX_SIGS="${1:-3}"

# Use awk to find Python-specific patterns
awk -v max="$MAX_SIGS" '
  BEGIN { count = 0 }

  # Class definitions
  /^class [A-Za-z_][A-Za-z0-9_]*(\(|:)/ {
    if (count < max) {
      print "- `" $0 "`"
      count++
    }
  }

  # Function/method definitions
  /^(async )?def [a-z_][a-z0-9_]*\(/ {
    if (count < max) {
      print "- `" $0 "`"
      count++
    }
  }

  # Decorated functions (capture decorator + def)
  /^@[a-z_]+/ {
    decorator = $0
    getline
    if (/^(async )?def / && count < max) {
      print "- `" decorator " " $0 "`"
      count++
    }
  }

  # Type aliases
  /^[A-Z][a-zA-Z0-9_]* = / {
    if (count < max) {
      print "- `" $0 "`"
      count++
    }
  }
'
