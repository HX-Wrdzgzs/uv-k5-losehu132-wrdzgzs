# LOSEHU132 UV-K5 / UV-K6 固件

这是一个面向 Quansheng UV-K5/UV-K6 的自定义固件维护仓库。当前版本以 **LOSEHU132** 为主，重点维护中文功能、扩展功能、可复核的构建产物，以及一份持续更新的全国中继频率数据快照。

> 中文 README 是本仓库的项目说明和使用入口。`README_en.md` 保留为英文参考文档，版本和中继数据说明可能滞后于本页。

## 先看这里

| 你的目的 | 从这里开始 |
| --- | --- |
| 下载并刷写固件 | [当前公开发布目录（不含个人尾音）](./release/LOSEHU132-bin-20260803-public/) |
| 自己构建固件 | [本地构建](#本地构建) |
| 查阅中继数据 | [当前数据快照](#当前数据快照) |
| 参与更新中继 | [全国中继数据协作](#全国中继数据协作) |
| 了解源码结构 | [目录说明](#目录说明) |

## 当前版本

- 固件版本：`LOSEHU132`
- 构建时间：`2026-07-30`
- 公开发布：`2026-08-03`（公开包不含个人自定义尾音资源）
- 目标设备：Quansheng UV-K5 / UV-K6 系列；不同硬件批次和 EEPROM 容量的兼容性需要自行确认
- 构建环境：Windows + Python 3.13
- 中继数据：K5DB v3 快照，数据时间 `2026-07-28`

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

当前公开发布目录：[`release/LOSEHU132-bin-20260803-public/`](./release/LOSEHU132-bin-20260803-public/)。该目录只提供公开固件和中继数据库，不包含个人自定义尾音资源。

| 文件 | 用途 | 大小 | SHA-256 |
| --- | --- | ---: | --- |
| [`firmware.packed.bin`](./release/LOSEHU132-bin-20260803-public/firmware.packed.bin) | 通常用于 K5Web 或兼容工具刷写 | 58,474 B | `BB380265614F73D268BA290966F3AB70E6C7E9023505510F0F406529CB6A8DE9` |
| [`firmware.bin`](./release/LOSEHU132-bin-20260803-public/firmware.bin) | 未封装的原始固件镜像 | 58,456 B | `C51763BDF93031956DDEADD874DEF0A5855EF24B299B6B1D36BC77AF8E635334` |
| [`firmware.stable.packed.bin`](./release/LOSEHU132-bin-20260803-public/firmware.stable.packed.bin) | Stable 封装固件镜像 | 59,126 B | `CC49FB61AC14194F135946A70BB313A8B93D0F212CD9201B87A9A9271ED0240B` |
| [`firmware.stable.bin`](./release/LOSEHU132-bin-20260803-public/firmware.stable.bin) | Stable 原始固件镜像 | 59,108 B | `0090C982F0BF19A5468BBDE32663BF2F6420A720CDABDA6C046761ECE0858A43` |
| [`repeaters.bin`](./release/LOSEHU132-bin-20260803-public/repeaters.bin) | K5DB v3 中继数据库 | 9,904 B | `84CCB5DEEB211DF62467D7B6F5DC19908EC34F96B36F1EEA773F319627070483` |
| [`repeaters.stable.bin`](./release/LOSEHU132-bin-20260803-public/repeaters.stable.bin) | Stable 中继数据库 | 9,904 B | `84CCB5DEEB211DF62467D7B6F5DC19908EC34F96B36F1EEA773F319627070483` |

公开发布目录中没有 `tails.bin` 或 `tails.stable.bin`。固件本体的自定义尾音入口仍保留；被排除的是个人尾音资源文件。

### 固件刷写

1. 确认型号、硬件版本和 EEPROM 容量，先用 [K5Web](https://k5.vicicode.com/) 备份配置和校准数据。
2. 固件升级时让对讲机关机，按住 PTT 开机进入升级模式。
3. 在 K5Web 的固件页面选择对应的 `firmware.packed.bin`，刷写完成后等待设备自动重启。
4. 刷完后检查固件版本、菜单、收发和 EEPROM 容量。

除固件升级外，数据库写入和备份等操作使用正常开机模式，不要按 PTT 进入升级模式。

### 写入中继数据库（COM4）

`repeaters.bin` 不是固件，不能放到 K5Web 的固件刷写入口。当前 LOSEHU132 工程提供 [`tools/write_eeprom_repeaters.py`](./tools/write_eeprom_repeaters.py)，它会把中继库写入扩展 EEPROM，并逐块读回校验；写入时也会同步写入同目录下的 `tails.bin`。

个人带尾音目录必须同时包含 `repeaters.bin` 和 `tails.bin`。公开 GitHub 目录没有尾音文件，不能直接用来执行这个命令。

先在不连接电台的情况下做文件校验：

```bat
cd /d <包含 repeaters.bin 和 tails.bin 的目录>
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

### 个人带尾音包

个人版不上传到 GitHub，只保存在本机下载文件夹。普通版本对应 `firmware.bin` + `tails.bin`，Stable 版本对应 `firmware.stable.bin` + `tails.stable.bin`。`tails.bin` 和 `tails.stable.bin` 是资源文件，不是固件镜像。

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

- 430 条模拟中继记录；
- 覆盖 152 个城市；
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
