# Rogue Tower 中文汉化补丁

《Rogue Tower》（Steam）的非官方简体中文汉化。基于资源级文本替换实现：
覆盖主菜单、升级卡（约 800 张）、怪物图鉴、炮塔说明、新手提示、
墓志铭彩蛋、怪物战斗台词等 4000+ 处游戏内文本，并将游戏内嵌字体替换为
思源黑体，中文渲染清晰无乱码。

![汉化效果预览](docs/menu-preview.jpg)

**使用流程**：Steam 安装好游戏 → 拉取本仓库 → 双击一键脚本，即可完成汉化并启动游戏。

## 快速开始

1. 在 Steam 上安装并**至少运行过一次**《Rogue Tower》
2. 拉取本仓库：
   ```
   git clone <仓库地址>
   ```
3. 双击仓库目录里的 **`一键汉化启动.bat`**

脚本会自动完成：

- 定位游戏安装目录（读取 Steam 库配置，无需手动填路径）
- 首次运行时联网安装 Python 依赖（UnityPy，约 1 分钟）
- 备份原始英文资源到 `Rogue Tower_Data\backup_original\`
- 写入中文文本 + 内嵌思源黑体，校验通过后安装
- 通过 Steam 启动游戏（成就、创意工坊均不受影响）

再次双击脚本会直接启动游戏（已汉化则自动跳过重复操作）。

## 环境要求

- Windows + Steam 版 Rogue Tower（AppID 1843760）
- Python 3.8+（[python.org](https://www.python.org/downloads/) 安装时勾选 *Add to PATH*；装完后重新双击脚本即可）
- 首次运行需要联网

## 常用命令

| 操作 | 方式 |
|---|---|
| 汉化并启动 | 双击 `一键汉化启动.bat` |
| 只汉化不启动 | `一键汉化启动.bat --no-launch` |
| 指定游戏目录 | `一键汉化启动.bat --game "D:\Steam\steamapps\common\Rogue Tower"` |
| 还原英文原版 | `一键汉化启动.bat --restore` |
| 强制重新汉化 | `一键汉化启动.bat --reapply` |

## 工作原理

游戏是 Unity (Mono) 构建，无任何本地化系统，全部 UI 文本硬编码在
`level0` / `level1` / `sharedassets0.assets` / `sharedassets1.assets` 的
uGUI `Text` 与自定义组件字段中。本补丁：

1. 按 Unity 序列化格式（长度前缀 + UTF-8 + 4 字节对齐）扫描组件数据中的字符串
2. 用词典将英文替换为中文（重写对象原始数据，偏移自动修正）
3. 将 `sharedassets0.assets` 中唯一的内嵌动态字体 Acme 的 TTF 数据替换为
   思源黑体，运行时按需光栅化中文字形
4. 严格跳过所有非显示文本：内部升级 ID（如 `BallistaSlow1`）、按钮动画
   触发器名、UnityEvent 方法名等，保证游戏逻辑不受影响

## 已知限制

- 代码运行时动态拼接的文本（如实时伤害数字）、烘焙在贴图中的英文、
  Steam 成就名称不在汉化范围内
- Steam「验证文件完整性」会把资源还原为英文——重新双击一键脚本即可再次汉化
- 游戏版本更新后资源文件变化，需要重新提取文本（见下节）

## 修改译文 / 维护

译文词典是 `resources/translations.json`（英文 → 中文，1700+ 条）。
改完词典后重新运行一键脚本（加 `--reapply`）即可生效。

维护者工具在 `tools/`（需要自行安装 UnityPy）：

- `extract.py` — 从游戏资源提取全部字符串清单
- `final_list.py` — 按组件白名单过滤出待译文本
- `apply.py` — 命令行替换工具（localize.py 的底层逻辑来源）

游戏更新后：跑一遍 extract + final_list，对照 `translations.json`
补翻新增条目，再用一键脚本重新汉化。

## 致谢与许可

- 字体：[Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC)，
  遵循 [SIL OFL 1.1](resources/OFL-LICENSE.txt)
- 资源解析：[UnityPy](https://github.com/K0lb3/UnityPy)
- 本汉化仅供学习交流，请支持正版游戏
