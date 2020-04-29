#!/usr/bin/env python

import logging
import os
import subprocess
import sys


def IsRealDepotTools(path):
    expanded_path = os.path.expanduser(path)
    return os.path.isfile(os.path.join(expanded_path, 'gclient.py'))


def add_depot_tools_to_path(source_dir=''):
    """Search for depot_tools and add it to sys.path."""
    # First, check if we have a DEPS'd in "depot_tools".
    deps_depot_tools = os.path.join(source_dir, 'third_party', 'depot_tools')
    if IsRealDepotTools(deps_depot_tools):
        # Put the pinned version at the start of the sys.path, in case there
        # are other non-pinned versions already on the sys.path.
        sys.path.insert(0, deps_depot_tools)
        return deps_depot_tools

    # Then look if depot_tools is already in PYTHONPATH.
    for i in sys.path:
        if i.rstrip(os.sep).endswith('depot_tools') and IsRealDepotTools(i):
            return i
    # Then look if depot_tools is in PATH, common case.
    for i in os.environ['PATH'].split(os.pathsep):
        if IsRealDepotTools(i):
            sys.path.append(i.rstrip(os.sep))
            return i
    # Rare case, it's not even in PATH, look upward up to root.
    root_dir = os.path.dirname(os.path.abspath(__file__))
    previous_dir = os.path.abspath(__file__)
    while root_dir and root_dir != previous_dir:
        i = os.path.join(root_dir, 'depot_tools')
        if IsRealDepotTools(i):
            sys.path.append(i)
            return i
        previous_dir = root_dir
        root_dir = os.path.dirname(root_dir)
    logging.error('Failed to find depot_tools')
    return None


def _RunCommand(cmd):
    logging.debug('Running: %r', cmd)
    subprocess.check_call(cmd)


def _RunGN(args):
    logging.info('Gn args : %s', args)

    cmd = [sys.executable, os.path.join(add_depot_tools_to_path(), 'gn.py')]
    cmd.extend(args)
    _RunCommand(cmd)


def _RunNinja(output_directory, args):
    logging.info('Ninja args : %s', args)

    cmd = [os.path.join(add_depot_tools_to_path(), 'ninja'),
           '-C', output_directory]
    cmd.extend(args)
    _RunCommand(cmd)


def _EncodeForGN(value):
    """Encodes value as a GN literal."""
    if isinstance(value, str):
        return '"' + value + '"'
    elif isinstance(value, bool):
        return repr(value).lower()
    else:
        return repr(value)


def Build(output_directory, gn_args, ninja_target_args):
    """Generates target architecture using GN and builds it using ninja."""

    gn_args_str = '--args=' + ' '.join([k + '=' + _EncodeForGN(v) for k, v in gn_args.items()])

    gn_args_list = ['gen', output_directory, gn_args_str]

    _RunGN(gn_args_list)

    _RunNinja(output_directory, ninja_target_args)
