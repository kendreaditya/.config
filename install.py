import platform
import subprocess
from rich.console import Console

console = Console()

def run_command(command, name):
    console.print(f'Installing [bold]{name}[/bold]...', style="blue")
    subprocess.run(command, shell=True)
    console.print(f'Finished installing [bold]{name}[/bold].', style="green")

def install_packages(packages):
    current_os = platform.system().lower()
    console.print(f'Current OS: [italic]{current_os}[/italic]')

    if current_os in packages['os_specific']:
        for package, command in packages['os_specific'][current_os].items():
            run_command(command, package)

    for package in packages['base_packages']:
        if current_os in packages['base_packages'][package]:
            run_command(packages['base_packages'][package][current_os], package)


if __name__ == '__main__':
    import json

    with open('apps.json') as f:
        package_list = json.load(f)
        install_packages(package_list)
