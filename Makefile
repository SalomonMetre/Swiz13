# Convenience wrapper around the shell scripts.
.PHONY: all build full install install-system monospace uninstall test specimens clean
all: build
build:            ; ./build.sh
full:             ; ./build.sh --full
install: build    ; ./install.sh
install-system:   ; sudo ./install.sh --system
monospace: build  ; ./install.sh --monospace
uninstall:        ; ./install.sh --uninstall
test:             ; . .venv/bin/activate && python -m unittest discover -s tests
specimens:        ; SPECIMENS=1 ./build.sh
clean:            ; rm -rf .venv scripts/__pycache__ tests/__pycache__
