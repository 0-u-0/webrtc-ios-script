#!/usr/bin/env python
import os
import argparse
import logging
import sys

from distutils import dir_util

from build_tools import Build, _RunCommand

# disable x86-64 when you intend to distribute app through the app store
# https://webrtc.github.io/webrtc-org/native-code/ios/
# DEFAULT_ARCHS = ['arm64', 'arm', 'x64', 'x86']
DEFAULT_ARCHS = ['arm64', 'arm', 'x64']
TARGETS = ['sdk:framework_objc']
OUT_DIR = 'out'
SDK_FRAMEWORK_NAME = 'WebRTC.framework'


def parse_args():
    parser = argparse.ArgumentParser(description='Collect and build WebRTC iOS framework.')
    parser.add_argument('-s', '--source-dir', help='WebRTC source dir. Example: /realpath/to/src')
    parser.add_argument('-v', '--verbose', action='store_true', help='Debug logging.')
    parser.add_argument('-r', '--is-release', action='store_true', help='Release or not.')
    parser.add_argument('--use-bitcode', action='store_true', help='Use bitcode or not.')
    parser.add_argument('--enable-vp9', action='store_true', help='Enable VP9 SoftCodec or not.')

    return parser.parse_args()


def get_debug_dir(is_debug):
    if is_debug:
        return 'Debug'
    else:
        return 'Release'


def build_ios_framework(src_dir, is_debug, bitcode):
    gn_args = {
        'target_os': 'ios',
        'ios_enable_code_signing': False,
        'use_xcode_clang': True,
        'is_debug': is_debug,
        'ios_deployment_target': '10.0',
        'enable_stripping': True,
        'enable_dsyms': not bitcode,
        'enable_ios_bitcode': bitcode
    }

    ninja_target_args = TARGETS

    for arch in DEFAULT_ARCHS:
        gn_args['target_cpu'] = arch

        build_dir = os.path.join(src_dir, OUT_DIR, get_debug_dir(is_debug), arch)

        logging.info('Build dir : %s', build_dir)
        Build(build_dir, gn_args, ninja_target_args)


def create_fat_library(src_dir, is_debug):
    output_dir = os.path.join(src_dir, OUT_DIR, get_debug_dir(is_debug))

    lib_paths = [os.path.join(output_dir, arch)
                 for arch in DEFAULT_ARCHS]

    # Combine the slices.
    dylib_path = os.path.join(SDK_FRAMEWORK_NAME, 'WebRTC')
    # Dylibs will be combined, all other files are the same across archs.
    # Use distutils instead of shutil to support merging folders.
    dir_util.copy_tree(
        os.path.join(lib_paths[0], SDK_FRAMEWORK_NAME),
        os.path.join(output_dir, SDK_FRAMEWORK_NAME))
    logging.info('Merging framework slices.')
    dylib_paths = [os.path.join(path, dylib_path) for path in lib_paths]
    out_dylib_path = os.path.join(output_dir, dylib_path)
    try:
        os.remove(out_dylib_path)
    except OSError:
        pass
    cmd = ['lipo'] + dylib_paths + ['-create', '-output', out_dylib_path]
    _RunCommand(cmd)

    # Merge the dSYM slices.
    lib_dsym_dir_path = os.path.join(lib_paths[0], 'WebRTC.dSYM')
    if os.path.isdir(lib_dsym_dir_path):
        dir_util.copy_tree(lib_dsym_dir_path, os.path.join(output_dir, 'WebRTC.dSYM'))
        logging.info('Merging dSYM slices.')
        dsym_path = os.path.join('WebRTC.dSYM', 'Contents', 'Resources', 'DWARF', 'WebRTC')
        lib_dsym_paths = [os.path.join(path, dsym_path) for path in lib_paths]
        out_dsym_path = os.path.join(output_dir, dsym_path)
        try:
            os.remove(out_dsym_path)
        except OSError:
            pass
        cmd = ['lipo'] + lib_dsym_paths + ['-create', '-output', out_dsym_path]
        _RunCommand(cmd)

    logging.info('Done.')


def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    if not args.source_dir:
        src_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    else:
        src_dir = args.source_dir

    if os.path.isdir(src_dir):
        is_debug = not args.is_release

        build_ios_framework(src_dir, is_debug, args.use_bitcode)

        create_fat_library(src_dir, is_debug)
    else:
        logging.error('Src path not exists : %s', src_dir)


if __name__ == '__main__':
    sys.exit(main())
