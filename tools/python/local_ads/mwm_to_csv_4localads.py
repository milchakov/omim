#!/usr/bin/env python2.7
import os
import sys

# TODO: Make mwm an installable module.
sys.path.append(
    os.path.join(
        os.path.dirname(__file__), '..', 'mwm'
    )
)

import argparse
import csv
import mwm
import logging
import ctypes
from zlib import adler32
from multiprocessing import Pool, Queue, Process


HEADERS = {
    'mapping': 'osmid fid mwm_id mwm_version'.split(),
    'sponsored': 'stype sid fid mwm_id mwm_version'.split(),
    'mwm': 'mwm_id name mwm_version'.split(),
}
QUEUES = {name: Queue() for name in HEADERS}
GOOD_TYPES = ("amenity", "shop", "tourism", "leisure", "sport",
              "craft", "man_made", "office", "historic")


def generate_id_from_name_and_version(name, version):
    return ctypes.c_long((adler32(name) << 32) | version).value


def parse_mwm(mwm_name, osm2ft_name, override_version, types_name):
    with open(osm2ft_name, 'rb') as f:
        ft2osm = mwm.read_osm2ft(f, ft2osm=True, tuples=False)
    with open(mwm_name, 'rb') as f:
        mwm_file = mwm.MWM(f)
        version = override_version or mwm_file.read_version()['version']
        region_name = os.path.splitext(mwm_name)[0]
        mwm_id = generate_id_from_name_and_version(region_name, version)
        QUEUES['mwm'].put((mwm_id, region_name, version))
        mwm_file.read_header()
        mwm_file.read_types(types_name)
        for feature in mwm_file.iter_features(metadata=True):
            osm_id = ft2osm.get(feature['id'], None)
            if osm_id is None:
                if 'ref:sponsored' in feature['metadata']:
                    for t in feature['header']['types']:
                        if t.startswith('sponsored-'):
                            QUEUES['sponsored'].put((t[t.find('-')+1:],
                                                     feature['metadata']['ref:sponsored'],
                                                     feature['id'],
                                                     mwm_id,
                                                     version))
                            break
            else:
                for t in feature['header']['types']:
                    if t.startswith(GOOD_TYPES):
                        QUEUES['mapping'].put((ctypes.c_long(osm_id).value,
                                               feature['id'],
                                               mwm_id,
                                               version))
                        break


def write_csv(output_dir, qtype):
    with open(os.path.join(output_dir, qtype + '.csv'), 'w') as f:
        mapping = QUEUES[qtype].get()
        w = csv.writer(f)
        w.writerow(HEADERS[qtype])
        while mapping is not None:
            w.writerow(mapping)
            mapping = QUEUES[qtype].get()


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    parser = argparse.ArgumentParser(
        description='Prepares CSV files for uploading to localads database from mwm files.')
    parser.add_argument('mwm', help='path to mwm files')
    parser.add_argument('--osm2ft', help='path to osm2ft files (default is the same as mwm)')
    parser.add_argument('--output', default='.', help='path to generated files ("." by default)')
    types_default = os.path.join(os.path.dirname(sys.argv[0]),
                                 '..', '..', '..', 'data', 'types.txt')
    parser.add_argument('--types', default=types_default, help='path to omim/data/types.txt')
    parser.add_argument('--threads', type=int, help='number of threads to process files')
    parser.add_argument('--version', type=int, help='override mwm version')
    args = parser.parse_args()
    if not args.osm2ft:
        args.osm2ft = args.mwm

    # Create CSV writer processes for each queue and a pool of MWM readers.
    writers = [Process(target=write_csv, args=(args.output, qtype)) for qtype in QUEUES]
    for w in writers:
        w.start()
    pool = Pool(processes=args.threads)
    for mwm_name in os.listdir(args.mwm):
        if 'World' in mwm_name or 'minsk_pass' in mwm_name or not mwm_name.endswith('.mwm'):
            continue
        osm2ft_name = os.path.join(args.osm2ft, os.path.basename(mwm_name) + '.osm2ft')
        if not os.path.exists(osm2ft_name):
            logging.error('Cannot find %s', osm2ft_name)
            sys.exit(2)
        logging.info(mwm_name)
        pool.apply_async(parse_mwm, (mwm_name, osm2ft_name, args.version, args.types))
    pool.close()
    pool.join()
    for queue in QUEUES.values():
        queue.put(None)
    for w in writers:
        w.join()


if __name__ == '__main__':
    main()
