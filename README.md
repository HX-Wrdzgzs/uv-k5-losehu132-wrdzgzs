# LOSEHU132 UV-K5 / UV-K6 固件

这是一个面向 Quansheng UV-K5/UV-K6 的自定义固件维护仓库。当前版本以 **LOSEHU132** 为主，重点维护中文功能、扩展功能、可复核的构建产物，以及一份持续更新的全国中继频率数据快照。

> 中文 README 是本仓库的项目说明和使用入口。`README_en.md` 保留为英文参考文档，版本和中继数据说明可能滞后于本页。

## 先看这里

| 你的目的 | 从这里开始 |
| --- | --- |
| 下载并刷写固件 | [2026-08-20 尾音开头修正版双版本发布](./release/LOSEHU132-bin-20260820-final3-public/) |
| 自己构建固件 | [本地构建](#本地构建) |
| 查阅中继数据 | [当前数据快照](#当前数据快照) |
| 参与更新中继 | [全国中继数据协作](#全国中继数据协作) |
| 了解源码结构 | [目录说明](#目录说明) |

## 当前版本

- 固件版本：`LOSEHU132`
- 构建时间：`2026-08-20`
- GitHub Release：`LOSEHU132-bin-20260820-final3`
- 发布变体：公共无私人尾音版 + 个人带尾音版；两者都保留尾音菜单入口
- 目标设备：Quansheng UV-K5 / UV-K6 系列；不同硬件批次和 EEPROM 容量的兼容性需要自行确认
- 构建环境：Windows + Python 3.13
- 中继数据：K5DB v3 快照，数据时间 `2026-07-28`
- 带尾音修正：裁掉原始音频开头约 180 ms 的低电平、不稳定频率跟踪段，避免开场颤抖音

固件后缀代表不同的功能和容量组合。实际可用功能以源码中的编译选项、设备硬件和最终固件版本为准：

| 后缀 | 典型定位 |
| --- | --- |
| `LOSEHU132` | 中文基础版本 |
| `LOSEHU132K` | 中文扩容版本，适用于更大 EEPROM |
| `LOSEHU132H` | 中文输入法/大容量版本 |
| `LOSEHU132E` | 英文版本 |
| `LOSEHU132EK` | 英文扩容版本 |
| `LOSEHU132HS` | 中文与 SI4732 相关功能版本 |

## 主要功能

功能会随版本后缀和编译选项变化，当前工程包含以下功能方向：

- 中文界面、GB2312 字库和中文输入相关功能；
- 可配置的 MDC1200、DTMF、联系人和串口功能；
- 宽范围接收、扫描范围、自定义侧键、VOX、手电筒和 RSSI 信号显示；
- AM 修复，以及部分版本中的 SI4732 / SSB / 多普勒卫星功能；
- 自定义开机文字、开机图片和多种菜单行为；
- 可扩展 EEPROM 数据区域，用于字库、输入法、卫星和中继等数据。

这些功能不是所有版本都同时启用。不要仅凭文件名判断功能，刷写前请查看发布说明和设备实际配置。

## 下载与刷写

最新发布目录与 GitHub Release：[`LOSEHU132-bin-20260820-final3`](https://github.com/HX-Wrdzgzs/uv-k5-losehu132-wrdzgzs/releases/tag/LOSEHU132-bin-20260820-final3)。刷写时优先选择带 `.packed.bin` 后缀的文件。

| 版本 | 尾音状态 | 刷写镜像 | 原始镜像 |
| --- | --- | --- | --- |
| `public` | **无私人尾音**，保留入口并使用普通 Roger 尾音 | [`...-public.packed.bin`](./release/LOSEHU132-bin-20260820-final3-public/LOSEHU132-bin-20260820-final3-public.packed.bin) | [`...-public.bin`](./release/LOSEHU132-bin-20260820-final3-public/LOSEHU132-bin-20260820-final3-public.bin) |
| `tail` | **带个人尾音**，内嵌过滤开场颤音后的 `1.wav` 单音近似，约 1.61 秒 | [`...-tail.packed.bin`](./release/LOSEHU132-bin-20260820-final3-tail/LOSEHU132-bin-20260820-final3-tail.packed.bin) | [`...-tail.bin`](./release/LOSEHU132-bin-20260820-final3-tail/LOSEHU132-bin-20260820-final3-tail.bin) |

两个版本都包含同一份 K5DB v3 中继数据库和校验清单。个人尾音已经编译进 `tail` 固件，不再使用外部 `tails.bin`；原始私人 `1.wav` 不上传仓库。数据库文件不是固件，不能放进 K5Web 固件刷写入口。

| 数据文件 | 用途 | SHA-256 |
| --- | --- | --- |
| [`repeaters.bin`](./release/LOSEHU132-bin-20260820-final3-public/repeaters.bin) | K5DB v3 中继数据库 | `E164021D9F52855917D4878647006273B2F90D035FF16182F96C2FE82E1AB721` |
| [`repeaters.build.json`](./release/LOSEHU132-bin-20260820-final3-public/repeaters.build.json) | 数据构建记录和来源信息 | `60AD5F503C1F1EC241E7D1A27237E0EE1945E42F9D4EAFFF55A0DD96F665C9A0` |

完整文件哈希见两个目录中的 [`SHA256SUMS.txt`](./release/LOSEHU132-bin-20260820-final3-public/SHA256SUMS.txt) 和 [`SHA256SUMS.txt`](./release/LOSEHU132-bin-20260820-final3-tail/SHA256SUMS.txt)。

### 固件刷写

1. 确认型号、硬件版本和 EEPROM 容量，先用 [K5Web](https://k5.vicicode.com/) 备份配置和校准数据。
2. 固件升级时让对讲机关机，按住 PTT 开机进入升级模式。
3. 在 K5Web 的固件页面选择对应的 `firmware.packed.bin`，刷写完成后等待设备自动重启。
4. 刷完后检查固件版本、菜单、收发和 EEPROM 容量。

除固件升级外，数据库写入和备份等操作使用正常开机模式，不要按 PTT 进入升级模式。

### 写入中继数据库（COM4）

`repeaters.bin` 不是固件，不能放到 K5Web 的固件刷写入口。当前 LOSEHU132 工程提供 [`tools/write_eeprom_repeaters.py`](./tools/write_eeprom_repeaters.py)，它只写入 K5DB v3 中继数据库，并逐块读回校验；尾音行为已经编译在所选固件中，不需要、不支持额外的 `tails.bin`。

先在不连接电台的情况下做文件校验：

```bat
cd /d <包含 repeaters.bin 的目录>
C:/Python313/python.exe <仓库目录>/tools/write_eeprom_repeaters.py COM4 repeaters.bin
```

连接写频线、确认电台正常开机后，先做只读比对：

```bat
C:/Python313/python.exe <仓库目录>/tools/write_eeprom_repeaters.py COM4 repeaters.bin --verify-device
```

确认端口和文件正确后，才执行实际写入：

```bat
C:/Python313/python.exe <仓库目录>/tools/write_eeprom_repeaters.py COM4 repeaters.bin --write
```

完成后再次执行 `--verify-device`。出现 `EEPROM update verified` 或 `Device EEPROM matches` 后，再在电台菜单进入“全国中继”检查。

### 两个固件版本如何选择

- `public`：无你的私人尾音，适合公开分享和普通用户刷写；
- `tail`：带你的个人尾音，已过滤开场颤抖音并上传到本仓库 Release，文件名明确标为 `tail`；
- `MDC 尾音`仍然是 MDC 协议尾音，不等于个人 `1.wav` 尾音；
- 两个版本的 `repeaters.bin` 相同，数据库需要通过 COM4 单独写入。

刷写或写库前请保证电池充足、写频线插到底，并保留原始 EEPROM 备份。不要在型号或 EEPROM 容量不确定时尝试高地址数据库写入。
## 本地构建

### Windows 构建

仓库内置的 Windows 构建入口是 `win_make.bat`。它需要安装 ARM GNU Toolchain 和 GNU Make，并可能需要根据本机安装路径修改脚本中的 PATH：

```powershell
.\win_make.bat
```

也可以在已配置 ARM GCC 和 Make 的环境中直接执行：

```bash
make clean
make full
```

构建会生成 `firmware.bin`。如果需要供部分 Windows 写入工具使用的封装镜像，还需要按 `fw-pack.py` 的说明生成 `firmware.packed.bin`。

发布时应：

1. 保留构建日志和版本信息；
2. 检查输出文件大小；
3. 计算 SHA-256；
4. 将最终文件放入 `release/<版本目录>/`；
5. 不提交 `build/`、`build_tmp/`、目标文件和其他中间缓存。

工程也保留 Docker 构建脚本和原始 Makefile，适合需要自行调整编译选项的开发者。修改编译选项后，应重新核验固件版本、EEPROM 需求和最终镜像大小。

## 当前数据快照

本版本内置的中继数据快照为 **K5DB v3**：

- 428 条模拟中继记录；
- 覆盖 151 个城市；
- 数据时间：`2026-07-28`；
- 记录可能包含停用、迁移或尚未被本地用户确认的频率。

中继频率不是一次性数据。频率、收发差、亚音、台站状态和覆盖范围都可能变化，使用前应结合当地管理部门、台站公告、维护者信息或实际守听结果核对。

## 全国中继数据协作（规划中）

全国中继数据不适合长期靠固件作者手工维护。后续计划建设独立的中继数据仓库和网站/API，由注册用户提交，系统自动校验，再由维护者只处理异常和高风险记录，最后向固件仓库导出版本化数据。

访问规则建议如下：

- 未登录用户：可以查看已经发布的公开中继数据；
- 注册用户：可以提交新增、修改、停用申请，查看自己的提交记录；
- 审核员：审核数据、合并重复记录、标记过期信息；
- 管理员：管理用户、权限、数据版本和回滚。

注册是上传和参与协作的门槛，不是查看公开数据的门槛。提交通过基础校验后可以先标记为“待核验”并展示，但只有“已核验”数据才进入固件导出。这样可以减少单个维护者的审核压力，又不会让未经确认的频率直接进入固件。

详细的注册、权限、审核、数据字段和分阶段开发计划见 [`docs/repeater-data-roadmap.md`](./docs/repeater-data-roadmap.md)。

## 目录说明

```text
app/                 应用层和菜单相关代码
bsp/                 板级支持包
driver/              外设和芯片驱动
hardware/            硬件相关配置
tools/               构建、打包和数据处理工具
ui/                  界面及相关资源
写频脚本/             写频和频道数据辅助脚本
release/             已核验的版本发布产物
```

## 贡献与问题反馈

提交中继数据时，请尽量附上来源、核验日期、当地城市、收发频率、偏移、亚音和台站状态。只说“这里能用”而没有来源或测试时间的信息，不适合作为长期数据依据。

提交代码问题时，请附上：

- 对讲机型号和 EEPROM 容量；
- 固件完整版本名；
- 复现步骤；
- 是否修改过频道、设置或 EEPROM；
- 必要的日志和截图。

## 来源与许可

本项目基于 UV-K5 系列开源固件及社区修改版本持续维护，相关上游项目包括：

- [egzumer/uv-k5-firmware-custom](https://github.com/egzumer/uv-k5-firmware-custom)
- [LOSEHU 自定义引导](https://github.com/losehu/uv-k5-bootloader-custom)
- [LOSEHU 多普勒固件](https://github.com/losehu/uv-k5-firmware-custom/tree/doppler)
- [LOSEHU 更大固件系统](https://github.com/losehu/uv-k5-system-custom/)

请遵守各上游项目的许可证和当地无线电管理规定。仓库许可证见 [`LICENSE`](./LICENSE)。

## 固件变体与中继数据

本仓库同时发布公共无私人尾音版和个人带尾音版。两者都保留尾音菜单入口；区别在于 `public` 使用普通 Roger 尾音，`tail` 将个人 `1.wav` 的单音/增益/静音近似编译进固件。原始 `1.wav` 和旧的 `tails.bin` 不上传。

公版发布前使用白名单打包并检查：

```powershell
python tools/package_release.py --source . --output .\public-release
python tools/check_public_release.py .\public-release
```

默认打包结果是 `public` 版；需要生成个人带尾音固件包时使用 `--include-tails`。两种包都会生成 `release-manifest.json` 和 `SHA256SUMS.txt`，并通过文件名明确区分 `public` 与 `tail`。发布前仍应单独运行 `tools/check_public_release.py` 检查公共目录。

中继数据库写入前先验证，默认只读：

```powershell
python tools/update_repeater_db.py COM4 repeaters.bin --verify-device
python tools/update_repeater_db.py COM4 repeaters.bin --write --confirm
```

备份和恢复工具默认保护 RSSI 校准区；未经明确确认不会写 EEPROM 或校准数据。网站数据协作站：[`HX-Wrdzgzs/uv-k5-repeater-web`](https://github.com/HX-Wrdzgzs/uv-k5-repeater-web)。
