import os
import json
import subprocess

from setuptools import setup, find_packages
from setuptools.command.install import install

__requires__ = ['pipenv']

pipenv_command = ['pipenv', 'install']

def get_requirements_from_pipfile_lock(pipfile_lock=None):
    if pipfile_lock is None:
        pipfile_lock = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Pipfile.lock')
    lock_data = json.load(open(pipfile_lock))
    return [package_name for package_name in lock_data.get('default', {}).keys()]

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        subprocess.check_call(pipenv_command)
        install.run(self)

packages = find_packages()
requirements = get_requirements_from_pipfile_lock()

setup(
    name='git-migration',
    version='0.0.1',
    packages=find_packages(),
    scripts=[ 'migrate.py', 'interactive_migrate.py'],
    long_description=open('README.md', encoding='utf-8').read(),
    install_requires=requirements,
    python_requires=">=3.5",
)