# PANACEA

The project is a simple script that reads an XML file from ADTool and generates a PRISM model for PRISM-games.

The project was tested on Windows 10 and Ubuntu WSL2 with the following software versions:
- Python 3.12
- ADTool 2.2.2
- PRISM-games 3.2.1

## Building (Executable file Linux - Windows compatible)

Automated builds for Windows and Linux are available through GitHub Actions. Pre-built executables are generated for each release, eliminating the need to install Python and dependencies manually. Check the releases page on github for the latest pre-built binaries for your platform.

## Graphical User Interface (Terminal start version)

A desktop graphical user interface (GUI) has been developed to simplify the process of converting XML files to PRISM models. The GUI allows users to load XML files, select options like time analysis, and generate PRISM models with a user-friendly interface.

The GUI was created by [Mark8948](https://github.com/Mark8948) and is available in the `panacea-gui.py` file. To run it for the first time, ensure all dependencies are installed by executing:

if you are on windows:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

if you are on linux:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

and finally you can run the program by only running the following command:

```bash 
python panacea-gui.py
```

**Note:** In the GUI version of PANACEA, the `--props` flag (for generating properties) is applied automatically when generating the PRISM model.

## Installation

To install the project, you need to clone the repository and install the dependencies.

```bash
git clone https://github.com/Marini97/PANACEA.git
cd PANACEA
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### ADTool

To generate the XML file, you need to use ADTool. You can download the software from the following link: [Download ADTool](https://satoss.uni.lu/members/piotr/adtool/) or with the following command:

```bash
wget https://satoss.uni.lu/members/piotr/adtool/ADTool-2.2.2-full.jar
```

To run the software, you need to use the following command:
```bash
java -jar ADTool-2.2.2-full.jar 
```
When creating the tree, every node needs to have a unique name and a description with the following fields:
```
Type: Action/Attribute/Goal
Action: if Type is Action then the action name
Cost: if Type is Action then the cost of the action
Time: if Type is Action then the time of the action
Role: Attacker/Defender
```
Example:
```
Type: Action
Action: exfiltrateData
Cost: 50
Time: 2
Role: Attacker
```
Some xml files are provided in the `trees` folder.

Once you have created the Tree, you can export it to an XML file to use it with the script.

### PRISM-games

To run the PRISM model, you need to use PRISM-games. You can download the software from the following link: [Download PRISM-games](https://www.prismmodelchecker.org/games/download.php)
or with the following command:

```bash
wget https://www.prismmodelchecker.org/dl/prism-games-3.2.1-linux64-x86.tar.gz
```
Unzip the file inside this project, specifying the correct path, with the following command:
```bash
tar -xvf prism-games-3.2.1-linux64-x86.tar.gz
```

Install the software with the following command:
```bash
cd prism-games-3.2.1-linux64-x86
./install.sh
```
To run PRISM-games: for Windows, double-click the short-cut; on other OSs, run `bin/xprism` for the GUI or `bin/prism` for the command-line version.


## Usage

To use the project, you need to run the script `main.py` with the following arguments:
- `--input` or `-i`: the path to the XML file from ADTool
- `--output` or `-o`: the path to the output file for the PRISM model
- `--props`: generate the properties for the PRISM model
- `--prune` or `-p`: name of the subtree root to keep
- `--time` or `-t`: generate a time-based PRISM model

```bash
python main.py --input input.xml --output output.prism --time
```

Then you can run the PRISM model with the following command:
```bash
prism-games-3.2.1-linux64-x86/bin/prism \
    -javamaxmem 1g \
    -cuddmaxmem 1g \
    output.prism \
    properties.props -prop 1 \
    -exportresults output/results.csv:csv \
    -exportstrat output/strat.dot
```
Change `-javamaxmem` and `-cuddmaxmem` values according to your system specifications and the size of the model.

Or you can run PRISM-games with the GUI with the following command:
```bash
prism-games-3.2.1-linux64-x86/bin/xprism
```
And then load the PRISM model and the properties file.
