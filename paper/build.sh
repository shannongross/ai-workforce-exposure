#!/usr/bin/env bash
# Builds the paper PDF from main.tex. Intermediate files go to build/.
set -e
cd "$(dirname "$0")"
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
cp build/main.pdf gross-2026-ai-exposure.pdf
echo "Wrote gross-2026-ai-exposure.pdf"
