. $(dirname $BASH_ARGV)/cfg.sh
export PATH=$PYTHON_HOME/bin:$PATH
export PYTHONPATH=$PLYNTH:$BASE/src/python
function py3() { $PYTHON_HOME/bin/python3 -q "$@"; }
