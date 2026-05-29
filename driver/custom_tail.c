/*
 * 自定义尾音 - 由 wav2tail.py 自动生成
 * 源文件: 1.wav
 * 音调数: 24
 * 总时长: 1.79s
 *
 * 使用方法:
 * 1. 将此文件保存为 driver/custom_tail.c
 * 2. 在 driver/bk4819.h 中添加: void BK4819_PlayCustomTail(void);
 * 3. 在 driver/bk4819.c 的 BK4819_PlayRoger() 中调用 BK4819_PlayCustomTail()
 *    替换或补充 BK4819_PlayRogerNormal() 调用
 * 4. 在 Makefile 的 OBJS 中添加: OBJS += driver/custom_tail.o
 */

#include "bk4819.h"
#include "system.h"

// 频率缩放: 将Hz转换为BK4819寄存器值
static inline uint16_t freq_to_reg(uint16_t freq_hz)
{
    return (uint16_t)(((uint32_t)freq_hz * 1353245u + (1u << 16)) >> 17);
}

// 音调序列: 1580Hz, 1400Hz, 1260Hz, 1420Hz, 1440Hz, 1500Hz, 440Hz, 1700Hz, 1780Hz, 1740Hz, 1080Hz, 1120Hz, 1280Hz, 1420Hz, 1560Hz, 1600Hz, 1460Hz, 1320Hz, 1120Hz, 1060Hz, 960Hz, 1000Hz, 480Hz, 1340Hz
// 时长序列: 30ms, 74ms, 30ms, 74ms, 30ms, 74ms, 30ms, 124ms, 399ms, 99ms, 49ms, 49ms, 30ms, 49ms, 30ms, 74ms, 30ms, 49ms, 30ms, 49ms, 30ms, 49ms, 274ms, 63ms

#define TONE_COUNT 24
#define TONE_GAIN 66     // 音量增益 (0-127)
#define TONE_LEVEL 10    // 侧音音量

static const uint16_t gCustomTailFreqs[TONE_COUNT] = {
    1580u, 1400u, 1260u, 1420u, 1440u, 1500u, 440u, 1700u, 1780u, 1740u, 1080u, 1120u, 1280u, 1420u, 1560u, 1600u, 1460u, 1320u, 1120u, 1060u, 960u, 1000u, 480u, 1340u
};

static const uint16_t gCustomTailDurations[TONE_COUNT] = {
    30u, 74u, 30u, 74u, 30u, 74u, 30u, 124u, 399u, 99u, 49u, 49u, 30u, 49u, 30u, 74u, 30u, 49u, 30u, 49u, 30u, 49u, 274u, 63u
};

void BK4819_PlayCustomTail(void)
{
    BK4819_EnterTxMute();
    BK4819_SetAF(BK4819_AF_MUTE);
    
    // 配置TONE1
    BK4819_WriteRegister(BK4819_REG_70, 
        BK4819_REG_70_ENABLE_TONE1 | 
        (TONE_GAIN << BK4819_REG_70_SHIFT_TONE1_TUNING_GAIN));
    
    BK4819_EnableTXLink();
    SYSTEM_DelayMs(30);
    
    for (int i = 0; i < TONE_COUNT; i++)
    {
        // 设置音调频率
        BK4819_WriteRegister(BK4819_REG_71, freq_to_reg(gCustomTailFreqs[i]));
        
        if (i == 0) {
            BK4819_ExitTxMute();
        }
        
        SYSTEM_DelayMs(gCustomTailDurations[i]);
    }
    
    BK4819_EnterTxMute();
    BK4819_TurnsOffTones_TurnsOnRX();
}
