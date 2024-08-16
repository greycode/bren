# bren - Batch Rename Tool 🏷️✨

bren is a powerful and flexible command-line batch renaming tool for files and directories. Rename with ease! 🚀

## 📚 Table of Contents

- [✨ Features](#-features)
- [🛠️ Installation](#️-installation)
- [🚀 Basic Usage](#-basic-usage)
- [🔧 Advanced Usage](#-advanced-usage)
- [🔠 Placeholders](#-placeholders)
- [💡 Best Practices](#-best-practices)
- [❓ FAQ](#-faq)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## ✨ Features

- 🔍 Rename files and directories using various matching patterns
- 🧙‍♂️ Support for regular expressions
- 📅 Date and 🎲 random string insertion
- 🌳 Recursive renaming
- 👀 Preview and 🏃‍♂️ dry-run modes
- ↩️ Rollback capability
- 🗃️ Archive file support (zip, gz, tar)
- 🖥️ Cross-platform (Windows, Linux, macOS)

## 🛠️ Installation

### Prerequisites

- Python 3.6 or higher 🐍

### Steps

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/bren.git
   ```
2. Navigate to the bren directory:
   ```
   cd bren
   ```
3. Make the script executable (Linux/macOS):
   ```
   chmod +x bren
   ```
4. Add the bren directory to your PATH or create a symlink to the `bren` script in a directory that's already in your PATH.

## 🚀 Basic Usage

The basic syntax of bren is:

```
bren -m match_pattern [rename_operations]
```

### 🔍 Matching Patterns

- `-m suffix:.txt`: Match all files with .txt extension
- `-m prefix:img_`: Match all files starting with img_
- `-m contain:project`: Match all files containing "project" in the filename
- `-m "regex:^[a-z]+_\d{3}\.jpg$"`: Use regex to match files

### 🔄 Rename Operations

- `--append "_old"`: Add "_old" to the end of filenames
- `--prepend "new_"`: Add "new_" to the beginning of filenames
- `--delete "_temp"`: Remove "_temp" from filenames
- `--replace "old" "new"`: Replace "old" with "new" in filenames

### 📝 Examples

1. Rename all .txt files, appending "_old" to the filename:
   ```
   bren -m suffix:.txt --append "_old"
   ```

2. Rename all files starting with "IMG_", replacing "IMG_" with "Photo_":
   ```
   bren -m prefix:IMG_ --replace "IMG_" "Photo_"
   ```

3. Add current date to all files containing "report":
   ```
   bren -m contain:report --append "_${date:%Y%m%d}"
   ```

## 🔧 Advanced Usage

### 🧙‍♂️ Using Regular Expressions

```
bren -m "regex:^IMG_(\d{4})\.jpg$" --replace "IMG_" "Photo_" --append "_${1}"
```

### 🔗 Combining Multiple Operations

```
bren -m suffix:.txt --delete "_old" --append "_new" --prepend "${date}_"
```

### 👀 Preview Mode

```
bren -m suffix:.jpg --append "_edited" -v
```

### 🗃️ Processing Archives

```
bren -g archive.zip -m suffix:.txt --append "_processed"
```

For more advanced usage examples, please refer to the [documentation](docs/index.html).

## 🔠 Placeholders

- `${date}`: Insert current date/time 📅
- `${random}`: Insert random string 🎲
- `$W`: Working directory name 📂
- `$U`: Current username 👤
- `#`: File numbering 🔢

## 💡 Best Practices

- Always use preview (-v) or dry-run mode before actual renaming 👀
- Backup important files before batch renaming 💾
- Use specific matching patterns to avoid unintended renaming 🎯
- Utilize the logging feature for easy rollback 📜
- Thoroughly test your regex patterns 🧪

## ❓ FAQ

For frequently asked questions, please refer to the [FAQ section](docs/index.html#faq) in the documentation.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 🎉

1. Fork the repository 🍴
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 📬

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👏 Acknowledgments

- Thanks to all contributors who have helped to improve this project 🙌
- Inspired by various renaming tools and the need for a flexible, cross-platform solution 💡
