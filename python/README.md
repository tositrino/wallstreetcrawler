# wallstreetcrawler

crawl reddit channel workstreetbit and counts occurrence of stock symbols in posts. 

## Prerequisites

The following software is necessary steps to be able to work on the project.
  - git version constrol [1]
  - python interpreter >= 3.10 [2]
  - some editor , i.e. zed [3], visual studio code [4] or vim [5]

On macos you might install all necessary packages using 
  - homebrew [6]
  - macports [7]

On windows you might want to use 
  - scoop [8]
  - chocolatey [9]

 the project
on a macos system. The following instruction should work on all macos versions > 10.11 (catalina)
We assume you are familiar with your macos installation and you already have homebrew or macports
installed to install non apple software. If not please see the following links:


### System Requirements

  - git
  - python >=3.10
  
  Note: see requirements.txt for further details

## For Developers: Standard Software 
  The following software can be downloaded and installed using the description provided by its manufacturer:

  - zed editor 
    

  - Microsoft visual studio code 
    
  
#### Python Adjustments

wallstreetcrawler uses black as code formatter - to be able use it, it must be installed into the
main python installation. To do so, run the following commands in powershell after having installed python:
```
  > pip install --upgrade pip black
```

## Project Setup

to setup the project just clone it from the git repository 
  
### Installation Steps
     
#### make sure you have installed the system requirements
```
  $ python --version
    Python 3.13.5
```
      
#### Setup the Python Virtual Environment

  After cloning the project enter its python subfolder and execute the following actions:

  ```
    $ cd ./python
    $ python -m venv ./venv
    $ . ./venv/bin/activate
    (venv) python -m pip install --upgrade pip
    (venv) python -m pip install -r requirements.txt
  ```

## Run the project

### show version and help
```
  # show help
  (venv) python __main__.py --help
```

### Usage Examples
```
  # download and convert NASDAQ data
  python __main__.py --nasdaq_download
  # crawl thoru reddit posts
  python __main__.py --crawl
```

## references
[1] https://git-scm.com/
[2] https://www.python.org/
[3] https://zed.dev/
[4] https://code.visualstudio.com/Download
[5] https://neovim.io/
[6] https://brew.sh/
[7] https://www.macports.org/
[8] https://scoop.sh/
[9] https://chocolatey.org/

## Troubleshooting

ideally, create an issue on the repository or mail to development@ths-one.

