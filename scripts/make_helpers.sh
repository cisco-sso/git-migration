#!/usr/bin/env bash
set -euo pipefail

CACHE_DIR=.cache

function main() {
    # Ensure cache directory exists
    if [[ ! -d ${CACHE_DIR} ]]; then
	rm -rf ${CACHE_DIR} && mkdir -p ${CACHE_DIR}
    fi

    # Just launch the parameters passed as: function var-args...
    $@
}

#####################################################################
# Run the main program
main "$@"
