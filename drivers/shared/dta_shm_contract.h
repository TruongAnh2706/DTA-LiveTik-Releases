/**
 * DTA Studio - Shared Memory Inter-Process Communication Contract
 * Contract specification between Python Producer & WDM Kernel Camera/Audio Drivers
 */

#ifndef DTA_SHM_CONTRACT_H
#define DTA_SHM_CONTRACT_H

#include <stdint.h>

#define DTA_SHM_MAGIC 0x44544143  // "DTAC"
#define DTA_CAMERA_SHM_NAME "Global\\DTACameraSharedMemory"
#define DTA_CAMERA_MUTEX_NAME "Global\\DTACameraMutex"
#define DTA_AUDIO_SHM_NAME "Global\\DTAAudioSharedBuffer"
#define DTA_AUDIO_MUTEX_NAME "Global\\DTAAudioMutex"

#define DTA_DEFAULT_WIDTH 1920
#define DTA_DEFAULT_HEIGHT 1080
#define DTA_DEFAULT_FPS 30
#define DTA_FOURCC_MJPG 0x47504A4D  // "MJPG" Motion JPEG (Same as physical FHD Camera)
#define DTA_FOURCC_YUY2 0x32595559  // "YUY2" Uncompressed YUV 4:2:2
#define DTA_FRAME_PAYLOAD_SIZE (1920 * 1080 * 3)  // 6,220,800 bytes max buffer

#pragma pack(push, 1)

typedef struct _DTA_FRAME_HEADER {
    uint32_t magic;          // DTA_SHM_MAGIC
    uint32_t width;          // 1920
    uint32_t height;         // 1080
    uint32_t fps;            // 30
    uint32_t format;         // 0: RGB24, 1: NV12, 2: YUY2, 3: MJPEG (Motion JPEG)
    uint32_t fourcc;         // DTA_FOURCC_MJPG or DTA_FOURCC_YUY2
    uint64_t frame_index;    // Monotonic sequence number
    uint64_t timestamp_ms;   // Epoch timestamp in milliseconds
    uint32_t payload_size;   // Size of compressed frame buffer
} DTA_FRAME_HEADER;

typedef struct _DTA_CAMERA_SHM_BUFFER {
    DTA_FRAME_HEADER header;
    uint8_t pixel_buffer[DTA_FRAME_PAYLOAD_SIZE];
} DTA_CAMERA_SHM_BUFFER;

typedef struct _DTA_AUDIO_HEADER {
    uint32_t magic;          // 0x44544141 ("DTAA")
    uint32_t sample_rate;    // 48000
    uint32_t channels;       // 2
    uint32_t bits_per_sample;// 16
    uint64_t pcm_bytes_written;
} DTA_AUDIO_HEADER;

#pragma pack(pop)

#endif // DTA_SHM_CONTRACT_H
