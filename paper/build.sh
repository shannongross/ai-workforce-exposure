#!/usr/bin/env bash
# Builds paper.pdf from main.tex. Intermediate files go to build/.
set -e
cd "$(dirname "$0")"
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
cp build/main.pdf paper.pdf
echo "Wrote paper.pdf"
