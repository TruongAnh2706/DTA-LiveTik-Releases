/**
 * DTA Studio - Softcam Native Shared Memory Contract
 * Matching tshino/softcam zero-latency IPC architecture.
 */

#ifndef DTA_SOFTCAM_SHM_H
#define DTA_SOFTCAM_SHM_H

#include <stdint.h>

#define DTA_SOFTCAM_MAGIC 0x534F4654  // "SOFT"
#define DTA_SOFTCAM_SHM_NAME "Global\\DTACameraSharedMemory"
#define DTA_SOFTCAM_MUTEX_NAME "Global\\DTACameraMutex"

#define DTA_DEFAULT_WIDTH 1920
#define DTA_DEFAULT_HEIGHT 1080
#define DTA_DEFAULT_FPS 30
#define DTA_FRAME_PAYLOAD_SIZE (1920 * 1080 * 3)  // 6,220,800 bytes BGR24

#pragma pack(push, 1)

typedef struct _DTA_SOFTCAM_HEADER {
    uint32_t magic;          // DTA_SOFTCAM_MAGIC
    uint32_t width;          // 1920
    uint32_t height;         // 1080
    uint32_t fps;            // 30
    uint32_t format;         // 0: BGR24 (OpenCV), 1: RGB24, 2: UYVY
    uint64_t frame_index;    // Monotonic counter
    uint64_t timestamp_ms;   // Timestamp ms
    uint32_t payload_size;   // Size of pixel buffer
} DTA_SOFTCAM_HEADER;

typedef struct _DTA_SOFTCAM_BUFFER {
    DTA_SOFTCAM_HEADER header;
    uint8_t pixels[DTA_FRAME_PAYLOAD_SIZE];
} DTA_SOFTCAM_BUFFER;

#pragma pack(pop)

#endif // DTA_SOFTCAM_SHM_H
