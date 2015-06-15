#!/usr/bin/env python

import argparse
import sys
import logging
import os.path as pt
import pandas as pd
import warnings

__dir = pt.dirname(pt.realpath(__file__))
# sys.path.insert(0, pt.join(__dir, '../module'))

import hdf
import feature_extractor as fext
import data
import annos as A


class Processor(object):

    def __init__(self, path, dataset, distance=False):
        self.path = path
        self.dataset = dataset
        self.distance = distance

    def annotate(self, chromo, annos):
        pos = data.get_pos(self.path, self.dataset, chromo)
        chromo = int(chromo)
        annos = annos.loc[annos.chromo == chromo]
        start, end = A.join_overlapping(annos['start'].values,
                                            annos['end'].values)
        if self.distance:
            f = A.distance(pos, start, end)
        else:
            f = A.is_in(pos, start, end)
        f = pd.DataFrame(dict(pos=pos, value=f))
        return f

    def process_chromo(self, chromo, annos, anno_name):
        f = self.annotate(chromo, annos)
        group = 'annos'
        if self.distance:
            group += '_dist'
        out_group = pt.join(self.dataset, group, anno_name, chromo)
        f.to_hdf(self.path, out_group, format='t', data_columns=True)

    def process(self, annos, anno_name):
        chromos = data.list_chromos(self.path, self.dataset)
        for chromo in chromos:
            self.process_chromo(chromo, annos, anno_name)


class App(object):

    def run(self, args):
        name = pt.basename(args[0])
        parser = self.create_parser(name)
        opts = parser.parse_args(args[1:])
        return self.main(name, opts)

    def create_parser(self, name):
        p = argparse.ArgumentParser(
            prog=name,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Adds annotation')
        p.add_argument(
            'in_file',
            help='Input HDF path to dataset (test, train, val)')
        p.add_argument(
            '-a', '--anno_files',
            help='Annotation files in BED format',
            nargs='+')
        p.add_argument(
            '--prefix',
            help='Prefix annotation names',
            default='')
        p.add_argument(
            '--distance',
            help='Compute distance to annotations',
            action='store_true'
        )
        p.add_argument(
            '--verbose', help='More detailed log messages', action='store_true')
        p.add_argument(
            '--log_file', help='Write log messages to file')
        return p

    def main(self, name, opts):
        logging.basicConfig(filename=opts.log_file,
                            format='%(levelname)s (%(asctime)s): %(message)s')
        log = logging.getLogger(name)
        if opts.verbose:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
        log.debug(opts)

        log.info('Add annotations ...')
        in_path, in_group = hdf.split_path(opts.in_file)
        p = Processor(in_path, in_group, opts.distance)
        for anno_file in opts.anno_files:
            anno_name = opts.prefix + pt.splitext(pt.basename(anno_file))[0]
            log.info('\t%s...', anno_name)
            annos = data.read_annos(anno_file)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                p.process(annos, anno_name)
        log.info('Done!')
        return 0


if __name__ == '__main__':
    app = App()
    app.run(sys.argv)
