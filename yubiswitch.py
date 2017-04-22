#!/usr/bin/env python3
# Python version of https://github.com/gsstark/yubiswitch-for-linux

import os
import sys
import subprocess
import argparse


class YubiKey:

    def __init__(self, dev_id, product):
        self.dev_id = dev_id
        self.product = product

    def is_active(self):
        try:
            return bool(os.lstat(
                os.path.join('/sys/bus/usb/drivers/usbhid', self.dev_id)))
        except FileNotFoundError:
            return False

    def activate(self):
        '''
        Activate the Yubikey. Return True if succeeded, False if the key is
        already active. Raise an exception if it fails otherwise.
        '''
        if self.is_active():
            return False
        with open('/sys/bus/usb/drivers/usbhid/bind', 'w') as fd:
            fd.write(self.dev_id)
        return True

    def deactivate(self):
        '''
        Deactivate the Yubikey. Return True if succeeded, False if the key is
        already active. Raise an exception if it fails otherwise.
        '''
        if not self.is_active():
            return False
        with open('/sys/bus/usb/drivers/usbhid/unbind', 'w') as fd:
            fd.write(self.dev_id)
        return True

    def __repr__(self):
        return '<{c} (dev_id={d!r}, product={p!r})>'.format(
            c=self.__class__.__name__,
            d=self.dev_id,
            p=self.product,
        )


def get_yubikeys(debug=False):
    yubikeys = []
    basepath = '/sys/bus/usb/devices/'
    if debug:
        print('Scanning {p}'.format(p=basepath))
    for dev_id in os.listdir(basepath):
        manufacturer_path = os.path.join(basepath, dev_id, 'manufacturer')
        if debug:
            print('Opening manufacturer file {f}'.format(f=manufacturer_path))
        try:
            with open(manufacturer_path) as fd:
                manufacturer = fd.read()
        except (OSError, IOError) as exc:
            continue
        if manufacturer == 'Yubico\n':
            if debug:
                print('Found Yubico device at {p}, scanning sub-devices'
                      .format(p=manufacturer_path))
            product_path = os.path.join(basepath, dev_id, 'product')
            if debug:
                print('Opening product file {p}'.format(p=product_path))
            with open(product_path) as fd:
                product = fd.read().strip()
            for subdev in os.listdir(os.path.join(basepath, dev_id)):
                if not os.path.isdir(os.path.join(basepath, dev_id, subdev)):
                    continue
                if not set(subdev).issubset(set('0123456789-:.')):
                    continue
                yubikeys.append(YubiKey(subdev, product))
    return yubikeys


def rerun_as_root(argv=None):
    print('Root access required, re-running with sudo')
    if argv is None:
        argv = sys.argv
    cmd = ['sudo'] + argv
    try:
        sys.exit(subprocess.check_call(cmd))
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['on', 'off', 'list'])
    parser.add_argument('-d', '--debug', action='store_true',
        help='Print debug output')
    args = parser.parse_args()

    if args.command in ('on', 'off') and os.geteuid() != 0:
        rerun_as_root()

    yubikeys = get_yubikeys(debug=args.debug)
    if args.command == 'on':
        for yubikey in yubikeys:
            if yubikey.activate():
                print('Yubikey activated successfully: {}'.format(yubikey))
            else:
                print('Yubikey already active: {}'.format(yubikey))
    elif args.command == 'off':
        for yubikey in yubikeys:
            if yubikey.deactivate():
                print('Yubikey deactivated successfully: {}'.format(yubikey))
            else:
                print('Yubikey already inactive: {}'.format(yubikey))
    elif args.command == 'list':
        for idx, yubikey in enumerate(yubikeys, 1):
            print('{i}) {d:<10} {p} (active={s})'.format(
                i=idx,
                d=yubikey.dev_id,
                p=yubikey.product,
                s=yubikey.is_active(),
            ))


if __name__ == '__main__':
    main()
