# CFOUR parser 

Parser of the output of the [CFOUR](https://cfour.uni-mainz.de/) program. 

## Install

### pip

```bash
python -m pip install cfour_parser
```

### localy

Go to your local code directory and download it there, e.g.,
```bash
cd ~/chemistry/tools/
git clone git@github.com:the-pawel-wojcik/cfour_parser.git 
```
After that make sure your directory is visible to python. Add at the end of
your `.bashrc`
```bash
export PYTHONPATH=~/chemistry/tools/cfour_parser/src:$PYTHONPATH
```

## Use 

Use the example file 
```bash
python -m cfour_parser example/pyrazine.c4 -j > pyrazine.json
```
or if you have installed with pip 
```bash
cfour_parser example/pyrazine.c4 -j > pyrazine.json
```
If you have `jq` installed you can filter the output
```bash
cfour_parser example/pyrazine.c4 -j | jq > pyrazine.json
```
For a quick overview of the output use the `-v` flags
```bash
cfour_parser example/pyrazine.c4 -v
cfour_parser example/pyrazine.c4 -vv
```
