#!/usr/bin/env python3
"""
Copyright 2019 Ryan Wick (rrwick@gmail.com)
https://github.com/rrwick/Minipolish

This file is part of Minipolish. Minipolish is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version. Minipolish is distributed
in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
details. You should have received a copy of the GNU General Public License along with Minipolish.
If not, see <http://www.gnu.org/licenses/>.
"""

import gzip
import multiprocessing
import os
import sys


def get_compression_type(filename):
    """
    Attempts to guess the compression (if any) on a file using the first few bytes.
    http://stackoverflow.com/questions/13044562
    """
    magic_dict = {'gz': (b'\x1f', b'\x8b', b'\x08'),
                  'bz2': (b'\x42', b'\x5a', b'\x68'),
                  'zip': (b'\x50', b'\x4b', b'\x03', b'\x04')}
    max_len = max(len(x) for x in magic_dict)

    unknown_file = open(str(filename), 'rb')
    file_start = unknown_file.read(max_len)
    unknown_file.close()
    compression_type = 'plain'
    for file_type, magic_bytes in magic_dict.items():
        if file_start.startswith(magic_bytes):
            compression_type = file_type
    if compression_type == 'bz2':
        sys.exit('Error: cannot use bzip2 format - use gzip instead')
    if compression_type == 'zip':
        sys.exit('Error: cannot use zip format - use gzip instead')
    return compression_type


def get_open_func(filename):
    if get_compression_type(filename) == 'gz':
        return gzip.open
    else:  # plain text
        return open


def get_sequence_file_type(filename):
    """
    Determines whether a file is FASTA or FASTQ.
    """
    if not os.path.isfile(filename):
        sys.exit('Error: could not find {}'.format(filename))
    if get_compression_type(filename) == 'gz':
        open_func = gzip.open
    else:  # plain text
        open_func = open
    with open_func(filename, 'rt') as seq_file:
        try:
            first_char = seq_file.read(1)
        except UnicodeDecodeError:
            first_char = ''
    if first_char == '>':
        return 'FASTA'
    elif first_char == '@':
        return 'FASTQ'
    else:
        raise ValueError('File is neither FASTA or FASTQ')


def iterate_fastq(filename):
    if get_sequence_file_type(filename) != 'FASTQ':
        sys.exit('Error: {} is not FASTQ format'.format(filename))
    with get_open_func(filename)(filename, 'rt') as fastq:
        for line in fastq:
            line = line.strip()
            if len(line) == 0:
                continue
            if not line.startswith('@'):
                continue
            name = line[1:].split()[0]
            sequence = next(fastq).strip()
            _ = next(fastq)
            qualities = next(fastq).strip()
            yield name, sequence, qualities


def count_reads(filename):
    count = 0
    for _ in iterate_fastq(filename):
        count += 1
    return count


def load_fasta(fasta_filename):
    if get_compression_type(fasta_filename) == 'gz':
        open_func = gzip.open
    else:  # plain text
        open_func = open
    fasta_seqs = []
    with open_func(fasta_filename, 'rt') as fasta_file:
        name = ''
        sequence = []
        for line in fasta_file:
            line = line.strip()
            if not line:
                continue
            if line[0] == '>':  # Header line = start of new contig
                if name:
                    fasta_seqs.append((name.split()[0], ''.join(sequence), name))
                    sequence = []
                name = line[1:]
            else:
                sequence.append(line)
        if name:
            fasta_seqs.append((name.split()[0], ''.join(sequence), name))
    return fasta_seqs


def get_default_thread_count():
    return min(multiprocessing.cpu_count(), 16)


def print_stderr(message, end='\n'):
    print(message, file=sys.stderr, flush=True, end=end)
