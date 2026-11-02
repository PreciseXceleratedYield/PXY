# PXY® — PreciseXceleratedYield
# Copyright © 2026 PreciseXceleratedYield. All rights reserved.
#
# This file is maintained in the PXY Git repository.
# The PXY installer intentionally replaces ~/.bashrc with this file.

# Non-interactive shells do not need a login banner or interactive environment.
case "$-" in
    *i*) ;;
    *) return ;;
esac

printf '\n'
printf '%s\n' 'PXY® — PreciseXceleratedYield'
printf '%s\n' 'Copyright © 2026 PreciseXceleratedYield. All rights reserved.'
printf '\n'

PXY_ENV_ACTIVATE="$HOME/env/bin/activate"

if [ -r "$PXY_ENV_ACTIVATE" ]; then
    if ! source "$PXY_ENV_ACTIVATE"; then
        printf '[PXY] ERROR: Failed to activate Python environment: %s\n' "$PXY_ENV_ACTIVATE" >&2
    elif [ "${VIRTUAL_ENV:-}" != "$HOME/env" ]; then
        printf '[PXY] ERROR: Unexpected Python environment: %s\n' "${VIRTUAL_ENV:-not active}" >&2
    fi
else
    printf '[PXY] ERROR: Python virtual environment not found: %s\n' "$PXY_ENV_ACTIVATE" >&2
    printf '[PXY] Run the PXY installation environment setup before using PXY.\n' >&2
fi

unset PXY_ENV_ACTIVATE

# Show the exact legal notice maintained by syscprtpxy.py on interactive login.
PXY_COPYRIGHT_SCRIPT="$HOME/PXY/pxy/sys/syscprtpxy.py"
if [ -f "$PXY_COPYRIGHT_SCRIPT" ] && [ -x "$HOME/env/bin/python3" ]; then
    ( cd "$HOME/PXY/pxy/sys" && "$HOME/env/bin/python3" syscprtpxy.py ) || \
        printf '[PXY] WARNING: Could not display copyright notice.\n' >&2
fi
unset PXY_COPYRIGHT_SCRIPT
