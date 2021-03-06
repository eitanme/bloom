from __future__ import print_function

import os
import sys
import traceback

from .. util import execute_command
from .. util import maybe_continue
from .. util import parse_stack_xml
from .. logging import ansi
from .. logging import error
from .. logging import log_prefix
from .. logging import info
from .. logging import warning
from .. git import create_branch
from .. git import branch_exists
from .. git import get_commit_hash
from .. git import get_current_branch
from .. git import track_branches

from .. patch.common import set_patch_config
from .. patch.common import get_patch_config
from .. patch.rebase_cmd import rebase_patches
from .. patch.trim_cmd import trim

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr)
    sys.exit(1)


def branch(src, prefix, patch, interactive, ignore_stack, directory=None):
    """
    Trys to find a old-style stack.xml, else passes to branch_packages.

    Most parameters passed through to execute_branch or branch_packages.
    :param ignore_stack: if True, does not look for stack.xml
    """
    cwd = directory if directory else os.getcwd()
    stack_path = os.path.join(cwd, 'stack.xml')
    info("Checking for stack.xml in ({0})".format(cwd))
    if not ignore_stack and os.path.exists(stack_path):
        stack_name = parse_stack_xml(stack_path).name
        return execute_command(src, stack_name, patch, interactive, directory)
    else:
        info("stack.xml not found, searching for package.xml(s)")
        branch_packages(src, prefix, patch, interactive, directory)


@log_prefix('[git-bloom-branch]: ')
def branch_packages(src, prefix, patch, interactive, directory=None):
    """
    Handles source directories with one or more new style catkin packages.

    All parameters are passes through to execute_branch.
    """
    current_branch = get_current_branch()
    try:
        _branch_packages(src, prefix, patch, interactive, directory)
    finally:
        if current_branch:
            execute_command('git checkout ' + current_branch, cwd=directory)


def _branch_packages(src, prefix, patch, interactive, directory=None):
    # Ensure we are on the correct src branch
    current_branch = get_current_branch()
    if current_branch != src:
        info("Changing to specified source branch " + src)
        execute_command('git checkout ' + src, cwd=directory)
    # Get packages
    repo_dir = directory if directory else os.getcwd()
    packages = find_packages(repo_dir)
    if packages == []:
        error("No package.xml(s) found in " + repo_dir)
        return 1
    # Verify that the packages all have the same version
    version = verify_equal_package_versions(packages.values())
    # Call git-bloom-branch on each package
    info(
      "Branching these packages: " + str([p.name for p in packages.values()])
    )
    if interactive:
        if not maybe_continue():
            error("Answered no to continue, exiting.")
            return 1
    retcode = 0
    for path in packages:
        package = packages[path]
        branch = prefix + ('' if prefix and prefix.endswith('/') else '/') \
               + package.name
        print('')  # white space
        info("Branching " + package.name + "_" + version + " to " + branch)
        ret = -1
        try:
            ret = execute_branch(src, branch, patch, False, path,
                directory=directory)
            msg = "Branching " + package.name + "_" + version + " to " + \
                branch + " returned " + str(ret)
            if ret != 0:
                warning(msg)
                retcode = ret
            else:
                info(msg)
        except Exception as err:
            traceback.print_exc()
            error("Error branching " + package.name + ": " + str(err))
            retcode = ret
        finally:
            execute_command('git checkout ' + src, cwd=directory)
    return retcode


def execute_branch(src, dst, patch, interactive, trim_dir, directory=None):
    """
    executes bloom branch from src to dst and optionally will patch

    If the dst branch does not exist yet, then it is created by branching the
    current working branch or the specified SRC_BRANCH.

    If the patches/dst branch branch does not exist yet then it is created.

    If the branches are created successful, then the working branch will be
    set to the dst branch, otherwise the working branch will remain unchanged.

    If the dst branch and patches/dst branch already existed, then a call to
    `git-bloom-patch rebase` is attempted unless patch is False.

    :param src: source branch from which to copy
    :param dst: destination branch
    :param patch: whether or not to apply previous patches to destination
    :param interactive: if True actions are summarized before committing
    :param trim_dir: sub directory to move to the root of git dst branch
    :param directory: directory in which to preform this action
    :returns: return code to be passed to sys.exit

    :raises: subprocess.CalledProcessError if any git calls fail
    """
    if branch_exists(src, local_only=False, directory=directory):
        if not branch_exists(src, local_only=True, directory=directory):
            info("Tracking source branch: {0}".format(src))
            track_branches(src, directory)
    else:
        error("Specified source branch does not exist: {0}".format(src))

    create_dst_branch = False
    if branch_exists(dst, local_only=False, directory=directory):
        if not branch_exists(dst, local_only=True, directory=directory):
            info("Tracking destination branch: {0}".format(dst))
            track_branches(dst, directory)
    else:
        create_dst_branch = True

    create_dst_patches_branch = False
    dst_patches = 'patches/' + dst
    if branch_exists(dst_patches, False, directory=directory):
        if not branch_exists(dst_patches, True, directory=directory):
            track_branches(dst_patches, directory)
    else:
        create_dst_patches_branch = True

    if interactive:
        info("Summary of changes:")
        if create_dst_branch:
            info("- The specified destination branch, " + ansi('boldon') + \
                 dst + ansi('reset') + ", does not exist, it will be " + \
                 "created from the source branch " + ansi('boldon') + src + \
                 ansi('reset'))
        if create_dst_patches_branch:
            info("- The destination patches branch, " + ansi('boldon') + \
                 dst_patches + ansi('reset') + " does not exist, it will be "
                 "created")
        info("- The working branch will be set to " + ansi('boldon') + dst + \
             ansi('reset'))
        if not maybe_continue():
            error("Answered no to continue, aborting.")
            return 1

    current_branch = get_current_branch(directory)
    try:
        # Change to the src branch
        execute_command('git checkout {0}'.format(src), cwd=directory)
        # Create the dst branch if needed
        if create_dst_branch:
            create_branch(dst, changeto=True, directory=directory)
        else:
            execute_command('git checkout {0}'.format(dst), cwd=directory)
        config = None
        # Create the dst patches branch if needed
        if create_dst_patches_branch:
            create_branch(dst_patches, orphaned=True, directory=directory)
        else:
            # Get the patches info and compare it, warn of changing parent
            config = get_patch_config(dst_patches, directory)
            if config is None:
                error("Failed to retreive patch config from " + dst_patches)
                return 1
            if config['parent'] != src:
                warning("You are changing the parent branch to " + src + \
                        " from " + config['parent'] + ", are you sure you "
                        "want to do this?")
                if not maybe_continue():
                    error("Answered no to continue, aborting.")
                    return 1
            if trim_dir != '' and config['trim'] != trim_dir:
                warning("You are changing the sub directory for the "
                        "destination branch to " + trim_dir + " from " + \
                        config['trim'] + ", are you sure you want to do this?")
                if not maybe_continue():
                    error("Answered no to continue, aborting.")
                    return 1
        # Get the current commit hash as a baseline
        commit_hash = get_commit_hash(dst, directory=directory)
        # Set the patch config
        config = {
            'parent': src,
            'base': commit_hash,
            'trim': config['trim'] if config is not None else '',
            'trimbase': config['trimbase'] if config is not None else ''
        }
        set_patch_config(dst_patches, config, directory=directory)
        # Command is successful, even if applying patches fails
        current_branch = None
        execute_command('git checkout ' + dst, cwd=directory)
        # If trim_dir is set, trim the resulting directory
        if trim_dir not in ['', '.'] and create_dst_branch:
            trim(trim_dir, False, False, directory)
        # Try to update if appropriate
        if not create_dst_branch and not create_dst_patches_branch:
            if patch:
                # Execute git-bloom-patch rebase
                rebase_patches(directory=directory)
            else:
                info("Skipping call to 'git-bloom-patch rebase' because "
                     "'--no-patch' was passed.")
    finally:
        if current_branch is not None:
            execute_command('git checkout {0}'.format(current_branch),
                            cwd=directory)
    return 0
