//
// Created by RUPC on 2024/1/30.
//
#include "bsp/dp32g030/rtc.h"
#include "ARMCM0.h"
#include "driver/eeprom.h"
#include "driver/system.h"
#include "ui/helper.h"
#include <stdbool.h>

uint8_t time[6];
volatile bool gRTC_SecondTick = false;
static uint16_t rtc_save_counter = 0;

#ifndef ENABLE_DOPPLER
void RTCHandler(void) {
    // Called every second by RTC interrupt
    RTC_Get();
    gRTC_SecondTick = true;

    // Save time to EEPROM every ~10 minutes (600 seconds)
    rtc_save_counter++;
    if (rtc_save_counter >= 600) {
        rtc_save_counter = 0;
        EEPROM_WriteBuffer(0x2BC0, time, 6);
    }

    // Clear RTC interrupt flag
    RTC_IF |= (1 << 0);
}
#endif

void RTC_INIT(void) {
    uint32_t correct_freq = 32768 - 1 + ((((RC_FREQ_DELTA & 0x400) >> 10) ? 1 : -1) * (RC_FREQ_DELTA & 0x3ff));

    // 清空PRE_PERIOD, PRE_DECIMAL 和 PRE_ROUND相关位
    RTC_PRE &= ~((0x7fff << 0) | (0xf << 20) | (0x1 << 24));
    RTC_PRE |= correct_freq           // PRE_ROUND=32768HZ-1
               | (0 << 20)            // DECIMAL=0
               | (0 << 24);           // PRE_PERIOD=8s

    // 从EEPROM读取上次保存的时间
    EEPROM_ReadBuffer(0x2BC0, time, 6);

    // 校验时间数据是否合理，不合理则设为默认值
    if (time[0] < 20 || time[0] > 99 || time[1] < 1 || time[1] > 12 ||
        time[2] < 1 || time[2] > 31 || time[3] > 23 ||
        time[4] > 59 || time[5] > 59) {
        // 默认时间: 2026-01-01 00:00:00
        time[0] = 26; time[1] = 1; time[2] = 1;
        time[3] = 0;  time[4] = 0; time[5] = 0;
    }

    RTC_Set();

    NVIC_SetPriority(Interrupt2_IRQn, 0);

    // 清除中断标志并使能秒中断
    RTC_IF |= (1 << 0);
    RTC_IE |= (1 << 0);

    // 使能RTC
    RTC_CFG |= (1 << 0);

    NVIC_EnableIRQ(Interrupt2_IRQn);
}

void RTC_Set(void) {
    RTC_DR = (2 << 24)                    // day 2
             | (time[0] / 10 << 20)       // YEAR TEN
             | (time[0] % 10 << 16)       // YEAR ONE
             | (time[1] / 10 << 12)       // MONTH TEN
             | (time[1] % 10 << 8)        // MONTH ONE
             | (time[2] / 10 << 4)        // DAY TEN
             | (time[2] % 10 << 0);       // DAY ONE
    RTC_TR = (time[3] / 10 << 20)         // h十位
             | (time[3] % 10 << 16)       // h个位
             | (time[4] / 10 << 12)       // min十位
             | (time[4] % 10 << 8)        // min个位
             | (time[5] / 10 << 4)        // sec十位
             | (time[5] % 10 << 0);       // sec个位
    RTC_CFG |= (1 << 2);                  // 打开设置时间功能
}

void RTC_Get(void) {
    time[0] = (RTC_TSDR >> 20 & 0b1111) * 10 + (RTC_TSDR >> 16 & 0b1111);
    time[1] = (RTC_TSDR >> 12 & 0b1) * 10 + (RTC_TSDR >> 8 & 0b1111);
    time[2] = (RTC_TSDR >> 4 & 0b1111) * 10 + (RTC_TSDR >> 0 & 0b1111);

    time[3] = (RTC_TSTR >> 20 & 0b111) * 10 + (RTC_TSTR >> 16 & 0b1111);
    time[4] = (RTC_TSTR >> 12 & 0b111) * 10 + (RTC_TSTR >> 8 & 0b1111);
    time[5] = (RTC_TSTR >> 4 & 0b111) * 10 + (RTC_TSTR >> 0 & 0b1111);
}

void RTC_SaveToEEPROM(void) {
    EEPROM_WriteBuffer(0x2BC0, time, 6);
}
