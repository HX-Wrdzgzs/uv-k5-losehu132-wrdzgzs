#!/usr/bin/env python3
"""
WAV → UV-K5 自定义尾音转换工具
===============================
用法: python wav2tail.py <input.wav> [options]

将WAV音频文件分析并转换为UV-K5 BK4819可播放的音调序列C代码。

选项:
  --output FILE    输出文件名 (默认: custom_tail.c)
  --tones N        最大音调数 (默认: 8)
  --min-freq HZ    最小频率Hz (默认: 300)
  --max-freq HZ    最大频率Hz (默认: 3000)
  --duration MS    每个音调最小时长ms (默认: 50)

输出:
  - custom_tail.c  可直接编译到固件中的C代码
  - 分析报告 (stdout)
"""

import wave
import numpy as np
import sys
import os
import argparse
from struct import unpack

def analyze_wav(filepath):
    """打开WAV文件并返回音频数据"""
    with wave.open(filepath, 'rb') as wf:
        params = wf.getparams()
        frames = wf.readframes(params.nframes)
        
        if params.sampwidth == 1:
            audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0
        elif params.sampwidth == 2:
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            raise ValueError(f"不支持的位宽: {params.sampwidth}")
        
        if params.nchannels == 2:
            audio = audio.reshape(-1, 2).mean(axis=1)
        
        sr = params.framerate
        return audio, sr

def extract_tone_sequence(audio, sr, max_tones=8, min_freq=300, max_freq=3000, min_tone_ms=50):
    """将音频分析为频率序列"""
    
    # 使用滑动窗口FFT分析时频内容
    window_size = int(sr * min_tone_ms / 1000)  # 窗口大小(样本数)
    hop_size = window_size // 2
    
    # 如果音频太短，调整窗口
    if len(audio) < window_size:
        window_size = len(audio)
        hop_size = window_size
    
    # 预加重 - 增强高频
    audio = np.append(audio[0], audio[1:] - 0.95 * audio[:-1])
    
    # 滑动窗口分析
    frequencies = []
    times = []
    
    for start in range(0, len(audio) - window_size + 1, hop_size):
        segment = audio[start:start + window_size]
        
        # 应用汉宁窗
        windowed = segment * np.hanning(len(segment))
        
        # FFT
        fft = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), 1.0 / sr)
        
        # 限制频率范围
        mask = (freqs >= min_freq) & (freqs <= max_freq)
        f_limited = freqs[mask]
        m_limited = fft[mask]
        
        if len(m_limited) == 0 or np.max(m_limited) < 0.01:
            continue
        
        # 找峰值
        peak_freq = f_limited[np.argmax(m_limited)]
        
        # 量化到最近的整数Hz
        peak_freq = round(peak_freq)
        
        t = start / sr
        if frequencies and abs(peak_freq - frequencies[-1]) < 20:
            # 频率变化太小，合并
            continue
        
        frequencies.append(peak_freq)
        times.append(t)
    
    if not frequencies:
        return [], []
    
    # 合并相近的片段
    merged_freqs = [frequencies[0]]
    merged_times = [times[0]]
    
    for i in range(1, len(frequencies)):
        if abs(frequencies[i] - merged_freqs[-1]) < 30:
            continue  # 跳过相近的频率
        merged_freqs.append(frequencies[i])
        merged_times.append(times[i])
    
    # 限制最大音调数
    if len(merged_freqs) > max_tones:
        # 均匀采样
        indices = np.linspace(0, len(merged_freqs) - 1, max_tones, dtype=int)
        merged_freqs = [merged_freqs[i] for i in indices]
        merged_times = [merged_times[i] for i in indices]
    
    return merged_freqs, merged_times

def generate_c_code(frequencies, times, filename, total_duration):
    """生成自定义尾音的C代码"""
    
    # 计算每个音调的持续时间(ms)
    durations = []
    for i in range(len(times)):
        if i < len(times) - 1:
            dur = int((times[i + 1] - times[i]) * 1000)
        else:
            dur = int((total_duration - times[i]) * 1000)
        durations.append(max(dur, 30))  # 至少30ms
    
    entries = len(frequencies)
    
    code = f"""/*
 * 自定义尾音 - 由 wav2tail.py 自动生成
 * 源文件: {os.path.basename(filename)}
 * 音调数: {entries}
 * 总时长: {total_duration:.2f}s
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

// BK4819频率缩放函数 (来自 bk4819.c)
extern uint16_t scale_freq(uint16_t freq);

// 音调序列: {', '.join(f'{f}Hz' for f in frequencies)}
// 时长序列: {', '.join(f'{d}ms' for d in durations)}

#define TONE_COUNT {entries}
#define TONE_GAIN 66     // 音量增益 (0-127)
#define TONE_LEVEL 10    // 侧音音量

static const uint16_t gCustomTailFreqs[TONE_COUNT] = {{
    {', '.join(f'{f}u' for f in frequencies)}
}};

static const uint16_t gCustomTailDurations[TONE_COUNT] = {{
    {', '.join(f'{d}u' for d in durations)}
}};

void BK4819_PlayCustomTail(void)
{{
    BK4819_EnterTxMute();
    BK4819_SetAF(BK4819_AF_MUTE);
    
    // 配置TONE1
    BK4819_WriteRegister(BK4819_REG_70, 
        BK4819_REG_70_ENABLE_TONE1 | 
        (TONE_GAIN << BK4819_REG_70_SHIFT_TONE1_TUNING_GAIN));
    
    BK4819_EnableTXLink();
    SYSTEM_DelayMs(30);
    
    for (int i = 0; i < TONE_COUNT; i++)
    {{
        // 设置音调频率
        BK4819_WriteRegister(BK4819_REG_71, scale_freq(gCustomTailFreqs[i]));
        
        if (i == 0) {{
            BK4819_ExitTxMute();
        }}
        
        SYSTEM_DelayMs(gCustomTailDurations[i]);
    }}
    
    BK4819_EnterTxMute();
    BK4819_TurnsOffTones_TurnsOnRX();
}}
"""
    return code

def print_analysis(audio, sr, frequencies, times):
    """打印分析报告"""
    print(f"{'='*60}")
    print(f"  WAV音频分析报告")
    print(f"{'='*60}")
    print(f"  采样率: {sr} Hz")
    print(f"  时长:   {len(audio)/sr:.2f} 秒")
    print(f"  样本数: {len(audio)}")
    print(f"  峰值:   {np.max(np.abs(audio)):.4f}")
    print(f"  RMS:    {np.sqrt(np.mean(audio**2)):.4f}")
    print(f"{'='*60}")
    print(f"  提取的音调序列:")
    print(f"  {'#':>3} | {'时间(s)':>8} | {'频率(Hz)':>8} | {'时长(ms)':>8}")
    print(f"  {'-'*33}")
    
    for i in range(len(frequencies)):
        t = times[i]
        if i < len(times) - 1:
            d = (times[i + 1] - times[i]) * 1000
        else:
            d = (len(audio)/sr - times[i]) * 1000
        print(f"  {i+1:>3} | {t:>8.2f} | {frequencies[i]:>8} | {d:>7.0f}")
    
    print(f"{'='*60}")
    print(f"  建议的BK4819音调序列:")
    for i, f in enumerate(frequencies):
        d = (times[i + 1] - times[i]) * 1000 if i < len(times) - 1 else 200
        print(f"    {f}Hz 持续 {d:.0f}ms")
    print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(description='WAV → UV-K5尾音转换工具')
    parser.add_argument('input', help='输入的WAV文件')
    parser.add_argument('--output', '-o', default='driver/custom_tail.c', help='输出C文件')
    parser.add_argument('--tones', '-t', type=int, default=8, help='最大音调数')
    parser.add_argument('--min-freq', type=int, default=300, help='最小频率Hz')
    parser.add_argument('--max-freq', type=int, default=3000, help='最大频率Hz')
    parser.add_argument('--min-tone', type=int, default=50, help='每个音调最小时长ms')
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 找不到文件 {args.input}")
        sys.exit(1)
    
    print(f"正在分析 {args.input}...")
    audio, sr = analyze_wav(args.input)
    total_duration = len(audio) / sr
    
    print(f"正在提取音调序列...")
    frequencies, times = extract_tone_sequence(
        audio, sr, 
        max_tones=args.tones,
        min_freq=args.min_freq,
        max_freq=args.max_freq,
        min_tone_ms=args.min_tone
    )
    
    if not frequencies:
        print("错误: 无法提取音调序列 (音频可能太安静或噪声太大)")
        sys.exit(1)
    
    # 打印分析
    print_analysis(audio, sr, frequencies, times)
    
    # 生成C代码
    c_code = generate_c_code(frequencies, times, args.input, total_duration)
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(c_code)
    
    print(f"C代码已生成: {args.output}")
    print()
    print("集成步骤:")
    print(f"  1. 将 {args.output} 放入固件目录")
    print(f"  2. 在 driver/bk4819.h 中添加 void BK4819_PlayCustomTail(void);")
    print(f"  3. 在 driver/bk4819.c 的 BK4819_PlayRoger() 中调用 BK4819_PlayCustomTail()")
    print(f"  4. 在 Makefile 的 OBJS 中添加 driver/custom_tail.o")

if __name__ == '__main__':
    main()
