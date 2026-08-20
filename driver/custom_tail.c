/*
 * 自定义尾音 - 由 wav2tail_hq.py 自动生成
 * 源文件: 1.wav
 * 音调段数: 54
 * 总时长: 1.79s
 *
 * BK4819 只能合成单音，以下序列保留 1.wav 的主频率、音量包络和静音段，
 * 是可编译进固件的近似，不是 PCM 播放。
 * 公版保留尾音菜单入口，但不嵌入个人尾音；个人构建才启用本数组。
 */

#include "bk4819.h"

#if CUSTOM_TAIL_EMBEDDED

#include "system.h"

static inline uint16_t freq_to_reg(uint16_t freq_hz)
{
    return (uint16_t)(((uint32_t)freq_hz * 1353245u + (1u << 16)) >> 17);
}

#define TAIL_COUNT 54

static const uint16_t gCustomTailFreqs[TAIL_COUNT] = {
    0u, 1564u, 1400u, 1496u, 1425u, 1360u, 1272u, 1407u, 1360u, 1440u, 1485u, 1473u,
    1550u, 1580u, 1580u, 1440u, 1590u, 1690u, 1680u, 1748u, 1784u, 1763u, 1762u, 1766u,
    1780u, 1780u, 1778u, 1759u, 0u, 1104u, 1192u, 1258u, 1300u, 1400u, 1420u, 1439u,
    1477u, 1531u, 1584u, 1573u, 1520u, 1460u, 1420u, 1365u, 1315u, 1269u, 1210u, 1147u,
    1091u, 1032u, 985u, 934u, 0u, 0u
};

static const uint8_t gCustomTailGains[TAIL_COUNT] = {
    0u, 24u, 24u, 24u, 24u, 24u, 24u, 24u, 26u, 35u, 37u, 28u, 33u, 46u, 58u, 68u, 71u, 74u,
    88u, 104u, 91u, 102u, 89u, 79u, 64u, 50u, 38u, 26u, 0u, 24u, 32u, 35u, 43u, 52u, 64u, 76u,
    88u, 94u, 89u, 75u, 70u, 68u, 67u, 66u, 62u, 58u, 55u, 51u, 49u, 42u, 34u, 25u, 0u, 0u
};

static const uint8_t gCustomTailDurations[TAIL_COUNT] = {
    12u, 11u, 12u, 17u, 23u, 6u, 35u, 58u, 12u, 29u, 40u, 18u, 6u, 17u, 6u, 17u, 6u, 29u,
    23u, 76u, 104u, 111u, 46u, 17u, 24u, 34u, 24u, 35u, 116u, 46u, 23u, 24u, 5u, 6u, 12u, 11u,
    18u, 23u, 41u, 34u, 12u, 12u, 5u, 12u, 12u, 11u, 18u, 17u, 23u, 24u, 23u, 17u, 250u, 145u
};


void BK4819_PlayCustomTail(void)
{
    bool active = false;

    BK4819_EnterTxMute();
    BK4819_SetAF(BK4819_AF_MUTE);
    BK4819_EnableTXLink();
    /* Keep the source WAV timing intact; this delay is only TX-chain setup. */
    SYSTEM_DelayMs(20);

    for (uint8_t i = 0; i < TAIL_COUNT; i++)
    {
        if (gCustomTailFreqs[i] == 0u || gCustomTailGains[i] == 0u)
        {
            BK4819_WriteRegister(BK4819_REG_70, 0u);
            if (active)
            {
                BK4819_EnterTxMute();
                active = false;
            }
        }
        else
        {
            BK4819_WriteRegister(BK4819_REG_71, freq_to_reg(gCustomTailFreqs[i]));
            BK4819_WriteRegister(
                BK4819_REG_70,
                BK4819_REG_70_ENABLE_TONE1
                | ((uint16_t)gCustomTailGains[i] << BK4819_REG_70_SHIFT_TONE1_TUNING_GAIN));
            if (!active)
            {
                BK4819_ExitTxMute();
                active = true;
            }
        }
        SYSTEM_DelayMs(gCustomTailDurations[i]);
    }

    BK4819_EnterTxMute();
    BK4819_TurnsOffTones_TurnsOnRX();
}

#else

/* 公版保留入口，但不带维护者个人 1.wav 资源。 */
void BK4819_PlayCustomTail(void)
{
    BK4819_PlayRogerNormal();
}

#endif
