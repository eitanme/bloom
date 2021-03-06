import os
import sys
import shutil

from export_bloom_from_src import get_path_and_pythonpath
# Setup environment for running commands
path, ppath = get_path_and_pythonpath()
os.putenv('PATH', path)
os.putenv('PYTHONPATH', ppath)


def test_create_temporary_directory():
    from bloom.util import create_temporary_directory

    tmp_dir = create_temporary_directory()
    assert os.path.exists(tmp_dir)
    shutil.rmtree(tmp_dir)

    if os.path.exists('/tmp'):
        os.mkdir('/tmp/test-bloom-util')
        tmp_dir = create_temporary_directory('/tmp/test-bloom-util')
        assert os.path.exists(tmp_dir)
        shutil.rmtree('/tmp/test-bloom-util')


def test_ANSI_colors():
    from bloom.util import ansi, enable_ANSI_colors, disable_ANSI_colors

    control_str = '\033[1m\033[3m\033[31mBold and Italic and Red \033[0mPlain'
    control_str_disable = 'Bold and Italic and Red Plain'

    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str == test_str, \
           '{0} == {1}'.format(control_str, test_str)

    disable_ANSI_colors()
    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str_disable == test_str, \
           '{0} == {1}'.format(control_str_disable, test_str)

    enable_ANSI_colors()
    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str == test_str, \
           '{0} == {1}'.format(control_str, test_str)


def test_maybe_continue():
    from subprocess import Popen, PIPE
    this_dir = os.path.abspath(os.path.dirname(__file__))
    cmd = '/usr/bin/env python maybe_continue_helper.py'

    p = Popen(cmd, shell=True, cwd=this_dir, stdin=PIPE, stdout=PIPE)
    p.communicate('y')
    assert p.returncode == 0

    p = Popen(cmd, shell=True, cwd=this_dir, stdin=PIPE, stdout=PIPE)
    p.communicate('n')
    assert p.returncode == 1


def test_extract_text():
    example_xml = """\
<stack>
  <name>langs</name>
  <version>0.3.5</version>
</stack>
"""
    from xml.dom.minidom import parseString
    dom = parseString(example_xml)
    from bloom.util import extract_text
    assert extract_text(dom.getElementsByTagName('name')[0]) == 'langs'
    assert extract_text(dom.getElementsByTagName('version')[0]) == '0.3.5'


def test_segment_version():
    test_str = '0.3.5'
    from bloom.util import segment_version
    assert segment_version(test_str) == ['0', '3', '5']


def test_parse_stack_xml():
    example_stack = """\
<stack>
  <name>langs</name>
  <version>0.3.5</version>
  <description>
    Meta package modeling the run-time dependencies for language bindings \
of messages.
  </description>
  <author>The ROS Ecosystem</author>
  <maintainer email="dthomas@willowgarage.com">Dirk Thomas</maintainer>
  <license>BSD</license>
  <copyright>Willow Garage</copyright>
  <url>http://www.ros.org</url>

  <build_depends>catkin</build_depends>

  <depends>catkin</depends>
  <!-- required for messages generated by gencpp -->
  <depends>roscpp_core</depends>

  <!-- workaround to provide the generators to dry downstream packages -->
  <depends>langs-dev</depends>
</stack>
"""
    from tempfile import mkdtemp
    tmp_dir = mkdtemp()
    stack_file = os.path.join(tmp_dir, 'stack.xml')
    open(stack_file, 'w+').write(example_stack)
    from bloom.util import parse_stack_xml
    stack = parse_stack_xml(stack_file)
    assert stack.name == 'langs'
    assert stack.version == '0.3.5'
    from shutil import rmtree
    rmtree(tmp_dir)


def test_assert_is_remote_git_repo():
    from tempfile import mkdtemp
    tmp_dir = mkdtemp()
    repo_dir = os.path.join(tmp_dir, 'repo')
    os.makedirs(repo_dir)
    from subprocess import check_call, Popen, PIPE
    check_call('git init .', shell=True, cwd=repo_dir, stdout=PIPE)
    check_call('touch example.txt', shell=True, cwd=repo_dir, stdout=PIPE)
    check_call('git add *', shell=True, cwd=repo_dir, stdout=PIPE)
    check_call('git commit -m "Init"', shell=True, cwd=repo_dir, stdout=PIPE)
    # Ensure PYTHONPATH
    this_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(os.path.abspath(os.path.join(this_dir, '..', 'src')))
    cmd = 'python -c "from bloom.util import assert_is_remote_git_repo; '
    cmd += 'assert_is_remote_git_repo(\'{0}\')"'.format('file://' + repo_dir)
    p = Popen(cmd, shell=True, cwd=repo_dir, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    assert p.returncode == 0
    cmd = 'python -c "from bloom.util import assert_is_remote_git_repo; '
    cmd += 'assert_is_remote_git_repo(\'{0}\')"'.format('file://' + tmp_dir)
    p = Popen(cmd, shell=True, cwd=repo_dir, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    assert p.returncode == 1
    from shutil import rmtree
    rmtree(tmp_dir)


def test_assert_is_not_gbp_repo():
    from tempfile import mkdtemp
    tmp_dir = mkdtemp()
    repo_dir = os.path.join(tmp_dir, 'repo')
    os.makedirs(repo_dir)
    from subprocess import check_call, Popen, PIPE
    check_call('git init .', shell=True, cwd=repo_dir, stdout=PIPE)
    check_call('touch example.txt', shell=True, cwd=repo_dir, stdout=PIPE)
    check_call('git add *', shell=True, cwd=repo_dir, stdout=PIPE)
    check_call('git commit -m "Init"', shell=True, cwd=repo_dir, stdout=PIPE)
    # Ensure PYTHONPATH
    this_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(os.path.abspath(os.path.join(this_dir, '..', 'src')))
    cmd = 'python -c "from bloom.util import assert_is_not_gbp_repo; '
    cmd += 'assert_is_not_gbp_repo(\'{0}\')"'.format('file://' + repo_dir)
    p = Popen(cmd, shell=True, cwd=repo_dir, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    assert p.returncode == 0
    cmd = 'python -c "from bloom.util import assert_is_remote_git_repo; '
    cmd += 'assert_is_remote_git_repo(\'{0}\')"'.format('file://' + tmp_dir)
    p = Popen(cmd, shell=True, cwd=repo_dir, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    assert p.returncode == 1
    check_call('git branch upstream', shell=True, cwd=repo_dir, stdout=PIPE)
    cmd = 'python -c "from bloom.util import assert_is_not_gbp_repo; '
    cmd += 'assert_is_not_gbp_repo(\'{0}\')"'.format('file://' + repo_dir)
    p = Popen(cmd, shell=True, cwd=repo_dir, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    print(out)
    assert p.returncode == 1
    from shutil import rmtree
    rmtree(tmp_dir)


def test_get_versions_from_upstream_tag():
    tag = 'upstream/0.4.0'
    from bloom.util import get_versions_from_upstream_tag
    result = get_versions_from_upstream_tag(tag)
    assert ['0', '4', '0'] == result, result
