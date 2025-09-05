# Alive Renewal Decompilation Project

Disclaimer: This project is not affiliated with the game or its developers.

## Overview

This project is a decompilation of the Alive Renewal game. It aims to extract the texts and plot branches from the game and save them to allow further modifications/translations.

## Features

- Decompilation of the game (very partial)
- Extraction of `.arc` resources
- Extraction of the game's texts
- ~~Extraction of the game's full plot data~~ (TODO)

## Usage

### Extract text / plot branches data

1. Clone the repository
- optional: open the game `alive.exe` with IDA Pro to discover the program and generate your own `alive.exe.i64` file
2. Run the `extract_texts.py` script to extract the dialog texts from the game
~~3. Run the `extract_texts_pro.py` script to extract the game's all texts and plot branches from the game~~ not implemented yet

### Extract .arc resources

1. Clone the repository
2. Run the `DLARC/main.py` script and follow the popup window.

## Contributing

PR

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- [IDA Pro](https://www.hex-rays.com/products/ida/)
- [tqdm](https://github.com/tqdm/tqdm)
- [openpyxl](https://openpyxl.readthedocs.io/en/stable/)

