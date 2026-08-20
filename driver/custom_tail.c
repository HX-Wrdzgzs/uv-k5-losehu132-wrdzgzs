/*
 * 自定义尾音 - 由 wav2tail_hq.py 自动生成
 * 源文件: 1.wav
 * 音调段数: 64
 * 总时长: 1.79s
 *
 * BK4819 只能合成单音，以下序列保留 1.wav 的主频率、音量包络和静音段，
 * 是可编译进固件的近似，不是 PCM 播放。
 * 开头低电平且不稳定的频率跟踪段已裁掉，避免开场颤音。
 * 公版保留尾音菜单入口，但不嵌入个人尾音；个人构建才启用本数组。
 */

#include "bk4819.h"

#if CUSTOM_TAIL_EMBEDDED

#include "system.h"

static inline uint16_t freq_to_reg(uint16_t freq_hz)
{
    return (uint16_t)(((uint32_t)freq_hz * 1353245u + (1u << 16)) >> 17);
}

#define TAIL_COUNT 64

static const uint16_t gCustomTailFreqs[TAIL_COUNT] = {
    1360u, 1430u, 1455u, 1495u, 1470u, 1473u, 1550u, 1580u, 1580u, 1440u, 1590u, 1690u,
    1677u, 1695u, 1736u, 1762u, 1773u, 1785u, 1763u, 1761u, 1760u, 1770u, 1780u, 1780u,
    1780u, 1780u, 1772u, 1755u, 0u, 1096u, 1125u, 1186u, 1220u, 1267u, 1300u, 1400u,
    1420u, 1420u, 1430u, 1455u, 1485u, 1515u, 1545u, 1583u, 1590u, 1566u, 1520u, 1460u,
    1420u, 1380u, 1340u, 1291u, 1260u, 1220u, 1180u, 1135u, 1105u, 1075u, 1040u, 995u,
    960u, 925u, 0u, 0u
};

static const uint8_t gCustomTailGains[TAIL_COUNT] = {
    27u, 32u, 38u, 39u, 35u, 28u, 33u, 46u, 58u, 68u, 71u, 74u, 86u, 96u, 103u, 105u, 95u, 92u,
    102u, 94u, 85u, 77u, 68u, 59u, 50u, 42u, 32u, 24u, 0u, 24u, 26u, 31u, 33u, 35u, 43u, 52u,
    61u, 67u, 73u, 82u, 90u, 94u, 95u, 90u, 82u, 72u, 70u, 68u, 67u, 66u, 64u, 60u, 57u, 56u,
    52u, 50u, 50u, 48u, 43u, 37u, 28u, 24u, 0u, 0u
};

static const uint8_t gCustomTailDurations[TAIL_COUNT] = {
    6u, 17u, 12u, 23u, 17u, 18u, 6u, 17u, 6u, 17u, 6u, 29u, 18u, 11u, 29u, 35u, 17u, 93u,
    82u, 58u, 23u, 11u, 12u, 17u, 24u, 17u, 23u, 24u, 116u, 34u, 12u, 17u, 12u, 18u, 5u, 6u,
    6u, 6u, 6u, 11u, 12u, 11u, 12u, 35u, 17u, 23u, 12u, 12u, 5u, 6u, 12u, 11u, 6u, 12u,
    12u, 11u, 12u, 11u, 18u, 23u, 12u, 11u, 250u, 145u
};


void BK4819_PlayCustomTail(void)
{
    bool active = false;

    BK4819_EnterTxMute();
    BK4819_SetAF(BK4819_AF_MUTE);
    BK4819_EnableTXLink();
    /* Stabilise the TX chain before the retained tail starts. */
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
