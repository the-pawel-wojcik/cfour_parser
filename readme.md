# CFOUR parser 
Parser of the output of the [CFOUR](https://cfour.uni-mainz.de/) program. 

## Install
Here are the two most straightforward ways of adding and removing
`cfour_parser` to or from your system.

### A. Using pip
Recommendation: Use this method from inside a virtual environment.
```bash
python -m pip install cfour_parser
```

#### uninstall
```bash
python -m pip uninstall cfour_parser
```

### B. Manually
1. Go to your local code directory and download `cfour_parser` there, e.g.,
```bash
cd ~/chemistry/tools/
git clone git@github.com:the-pawel-wojcik/cfour_parser.git 
```
2. After the download make sure that your directory is visible to python, e.g.,
   add at the end of your `.bashrc`
```bash
export PYTHONPATH=~/chemistry/tools/cfour_parser/src:$PYTHONPATH
```

#### uninstall
1. Delete the package files
```bash
rm -fr ~/chemistry/tools/cfour_parser
```
2. Remove the extra lines from your `.bashrc`.


## Use 
The `examples` directory contains a sample CFOUR's output file(s). 

For a quick overview of the output use the `-v` flags
```bash
python -m cfour_parser example/pyrazine.c4 -v
```
or if you have installed it with pip 
```bash
cfour_parser example/pyrazine.c4 -v
cfour_parser example/pyrazine.c4 -vv
```

Ultimately, this parser was build to produce a json file
```bash
cfour_parser example/pyrazine.c4 -j > pyrazine.json
```
If you have [`jq`](https://jqlang.github.io/jq/) installed you can filter the
output to preview it manually
```bash
cfour_parser example/pyrazine.c4 -j | jq > pyrazine.json
```
