. $(dirname $BASH_ARGV)/cfg.sh
export PATH=$PYTHON_HOME/bin:$PATH
export PYTHONPATH=$PLYNTH:$BASE/src/python:$BASE/test/input/src
function py3() { $PYTHON_HOME/bin/python3 -q "$@"; }
function supdoc() { clear; py3 -m supdoc.terminal "$@" | less -eF; }
