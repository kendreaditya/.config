# 🗂 .config dotfiles

- GitHub: auth for Github.com
- Neovim: fresh-vim editor
- skhd (macos): a hotkey daemon
- terminal (windows): windows terminal settings
- vscode: VSCode setting
- yabai (macos): Tilling window managers

# 🚀 Package Installer

This script is a package installer that automatically installs common development packages based on the operating system you are using. It simplifies the installation process by providing a centralized script that handles the installation of various packages.

## Prerequisites

- Python 3.x
- `pip` package manager

## Installation

1. Clone the repository or download the script `package_installer.py` to your local machine.

2. Open a terminal or command prompt and navigate to the directory where the script is located.

3. Install the required Python dependencies by running the following command:

   ```shell
   pip install -r requirements.txt
   ```

## Usage

1. Open the apps.json file and update it with the desired packages and their installation commands for each operating system.
2. Execute the script by running the following command:
   ```shell
   python package_installer.py
   ```
3. The script will automatically detect the current operating system and proceed to install the specified packages accordingly. Note: Depending on your system's configuration, you may need to run the script with administrative privileges (sudo or "Run as administrator") to ensure successful installation.

4. The script will display the progress of each package installation in the console. Once the installation process is complete, you will see a summary of the installed packages.

## Customization

- kbase_packages: This section of the apps.json file contains the base packages to be installed on all operating systems. You can modify the commands for each package according to your needs.

- os_specific: This section of the apps.json file contains operating system-specific commands. You can add or remove operating systems and specify their respective installation commands for specific packages.

## Contributing

Contributions are welcome! If you have any suggestions, bug reports, or feature requests, please open an issue or submit a pull request on the GitHub repository.
