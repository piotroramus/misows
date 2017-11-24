import argparse
import math
import os
import time

import boto
from boto.s3.key import Key
from filechunkio import FileChunkIO


def read_config(config_file='.config'):
    cfg = dict()
    with open(config_file, 'r') as f:
        for line in f:
            key, value = line.strip().split('=')
            cfg[key] = value
    return cfg


def benchmark(config_file, file_to_process='ala.txt'):
    cfg = read_config(config_file)
    aws_access_key_id = cfg['aws_access_key_id']
    aws_secret_access_key = cfg['aws_secret_access_key']
    bucket = cfg['bucket']

    # Connect to S3
    c = boto.connect_s3(aws_access_key_id, aws_secret_access_key)
    b = c.get_bucket(bucket)

    # Get file info
    source_path = file_to_process
    source_size = os.stat(source_path).st_size

    print "Starting the upload..."
    start_time = time.time()
    # Create a multipart upload request
    mp = b.initiate_multipart_upload(os.path.basename(source_path))

    # Use a chunk size of 50 MiB (feel free to change this)
    chunk_size = 52428800
    chunk_count = int(math.ceil(source_size / float(chunk_size)))

    # Send the file parts, using FileChunkIO to create a file-like object
    # that points to a certain byte range within the original file. We
    # set bytes to never exceed the original file size.
    for i in range(chunk_count):
        offset = chunk_size * i
        bytes = min(chunk_size, source_size - offset)
        with FileChunkIO(source_path, 'r', offset=offset,
                         bytes=bytes) as fp:
            mp.upload_part_from_file(fp, part_num=i + 1)

    # Finish the upload
    mp.complete_upload()

    total_time = time.time() - start_time
    print "Upload finished, time elapsed: {}s".format(total_time)

    print "Starting lookup"

    start_time = time.time()
    k = Key(b)
    k.key = file_to_process
    k.get_contents_to_filename("{}.download".format(file_to_process))

    total_time = time.time() - start_time
    print "Lookup finished, time elapsed: {}s".format(total_time)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Measures upload and download to S3 for the given file')
    parser.add_argument('--config', default='.config')
    parser.add_argument('--file')

    args = parser.parse_args()

    benchmark(args.config, args.file)
