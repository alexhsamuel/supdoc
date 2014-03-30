PYTHON_HOME=$HOME/sw/Python-3.4.0b1
export PATH=$PYTHON_HOME/bin:$PATH

BASE=$HOME/dev/apidoc
export PYTHONPATH=$BASE/src/python
export PATH=$BASE/bin:$PATH

# alias py3=$PYTHON_HOME/bin/python3
function py3() { /Library/Frameworks/Python.framework/Versions/3.4/bin/python3 -q "$@"; }
