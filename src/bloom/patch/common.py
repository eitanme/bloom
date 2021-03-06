from __future__ import print_function

import os
import sys
import subprocess
import traceback

from .. util import check_output
from .. util import execute_command
from .. logging import error
from .. logging import debug
from .. git import get_current_branch
from .. git import has_changes
from .. git import inbranch

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    error("catkin_pkg was not detected, please install it.", file=sys.stderr)
    sys.exit(1)

_patch_config_keys = ['parent', 'base', 'trim', 'trimbase']
_patch_config_keys.sort()


def get_version(directory=None):
    packages = find_packages(basepath=directory if directory else os.getcwd())
    try:
        version = verify_equal_package_versions(packages.values())
    except RuntimeError as err:
        traceback.print_exec()
        error("Releasing multiple packages with different versions is "
                "not supported: " + str(err))
        sys.exit(1)
    return version


def update_tag(version=None, force=True, directory=None):
    if version is None:
        version = get_version(directory)
    current_branch = get_current_branch(directory)
    tag_name = current_branch + "/" + version
    debug("Updating tag " + tag_name + " to point to " + current_branch)
    cmd = 'git tag ' + tag_name
    if force:
        cmd += ' -f'
    execute_command(cmd, cwd=directory)


def list_patches(directory=None):
    directory = directory if directory else '.'
    files = os.listdir(directory)
    patches = []
    for f in files:
        if f.endswith('.patch'):
            patches.append(f)
    return patches


def get_patch_config(patches_branch, directory=None):
    @inbranch(patches_branch, directory=directory)
    def fn():
        global _patch_config_keys
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        if not os.path.exists(conf_path):
            return None
        cmd = 'git config -f {0} patches.'.format(conf_path)
        try:
            config = {}
            for key in _patch_config_keys:
                config[key] = check_output(cmd + key, shell=True,
                                           cwd=directory).strip()
            return config
        except subprocess.CalledProcessError as err:
            traceback.print_exc()
            error("Failed to get patches info: " + str(err))
            return None
    return fn()


def set_patch_config(patches_branch, config, directory=None):
    @inbranch(patches_branch, directory=directory)
    def fn(config):
        global _patch_config_keys
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        config_keys = config.keys()
        config_keys.sort()
        if _patch_config_keys != config_keys:
            raise RuntimeError("Invalid config passed to set_patch_config")
        cmd = 'git config -f {0} patches.'.format(conf_path)
        try:
            for key in config:
                _cmd = cmd + key + ' "' + config[key] + '"'
                execute_command(_cmd, cwd=directory)
            # Stage the patches.conf file
            cmd = 'git add ' + conf_path
            execute_command(cmd, cwd=directory)
            if has_changes(directory):
                # Commit the changed config file
                cmd = 'git commit -m "Updated patches.conf"'
                execute_command(cmd, cwd=directory)
        except subprocess.CalledProcessError as err:
            traceback.print_exc()
            error("Failed to set patches info: " + str(err))
            raise
    return fn(config)
