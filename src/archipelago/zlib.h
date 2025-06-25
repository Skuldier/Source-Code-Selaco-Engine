/* Minimal dummy zlib.h */
#ifndef ZLIB_H
#define ZLIB_H

#define Z_OK 0
#define Z_STREAM_END 1
#define Z_ERRNO (-1)

typedef struct z_stream_s {
    void *opaque;
    int data_type;
    unsigned long adler;
    unsigned long reserved;
} z_stream;

#endif
