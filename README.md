# Robot URDF Studio

A Windows 11 desktop workspace for robot-arm development, CAD script generation, and embedded-device tooling.

## Language / 语言

- [English](#robot-urdf-studio)
- [中文](#中文)

## Current product direction

The product now unifies three layers:

1. **CAD generation and incremental editing**
   - Each part can be represented by its own Python script
   - AI can edit the script directly instead of rewriting original files
   - The `@cad` handle system tags geometric features so fine-grained edits can target holes, faces, fillets, slots, and mounting regions
   - Export targets include STEP, STL, DXF, GLB, topology data, and URDF

2. **Robot structure and visualization**
   - URDF import and parsing
   - Robot link/joint structure viewing
   - 2D skeleton preview as the current fallback viewport
   - 3D viewport backend abstraction ready for a future real renderer

3. **Operator workflow and device tools**
   - Joint sliders and pose presets
   - Workspace navigation and selection details
   - Serial/network/device console scaffolding
   - Telemetry, logs, and packaging-ready Windows launcher scripts

The long-term goal is to make the system feel like a professional engineering workbench where CAD generation, robot assembly, and model operation all stay connected.

## Run

Preferred launchers on Windows:

```powershell
.\run.ps1
```

or double-click:

```bat
start.bat
```

Fallback:

```bash
py -3.12 main.py
```

## Current product version

- Current tracked line: `v0.5.0`
- The CAD runway is visible in the main UI, with overview, workflow link, edit demo, export metadata, and CAD-to-robot interop snapshot support
- The telemetry and device-console snapshot chain is now validated in the live workflow path
- The product remains stable and launchable while preserving the robot workspace as the primary interactive area

## What this prototype includes

- Dark engineering desktop shell
- 2D skeleton viewport with auto-centering and joint-driven kinematics
- 3D placeholder viewport ready for a real backend swap-in
- Pluggable rendering backend architecture
- Joint sliders and pose presets (`Home`, `Reach`, `Inspect`)
- Workspace browser scaffold
- Project tree, URDF structure tree, selection details panel, and resource summary panel
- Unified robot model layer (`robot_model.py`)
- Viewport render protocol (`rendering.py`)
- Kinematic chain builder and FK solver
- Serial/network/task panel placeholders
- Modular layout prepared for telemetry and embedded workflows

## CAD workflow vision

The CAD layer is designed around per-part Python scripts under `models/<robot>/`.

Example concept:

```python
from cad import workspace

with workspace("wrist_link") as w:
    body = w.box(60, 50, 30)
    body = body.edges("|Z").fillet(2)      # @cad: edge_rounding
    body = body.faces(">Y").workplane()     # @cad: shaft_mount
    body = body.circle(15).extrude(20)
    w.export("wrist_link", ["step", "stl", "dxf", "glb"])
```

The important product rule is that AI should be able to:
- identify the feature through a stable handle
- edit only the relevant part of the script
- re-export without regenerating the entire model from scratch
- carry the result into URDF and robot-view workflows

## Project memory

- `CLAUDE.md` stores the long-context working contract for future development
- Keep changes stability-first and preserve launchability

## Dependencies

```bash
pip install -r requirements.txt
```

Planned CAD dependencies not yet committed to runtime requirements:

```bash
pip install cadquery trimesh ezdxf
```

## Windows packaging direction

Build a desktop executable with:

```powershell
.\build.ps1
```

The output exe will be created by PyInstaller in the `dist` folder.

---

# 中文

一个面向 Windows 11 的机器人与 CAD 工程工作台，用于机器人机械臂开发、CAD 脚本化建模和设备联动调试。

## 语言 / Language

- [English](#robot-urdf-studio)
- [中文](#中文)

## 项目方向

本项目统一了三层能力：

1. **CAD 生成与增量编辑**
   - 每个零件都可以对应独立的 Python 脚本
   - AI 可以直接编辑脚本，而不是重写原始模型文件
   - `@cad` 句柄系统用于标记关键几何特征，便于局部修改孔位、面、倒角、槽位和安装区域
   - 导出目标包括 STEP、STL、DXF、GLB、拓扑数据和 URDF

2. **机器人结构与可视化**
   - URDF 导入与解析
   - 机器人 link / joint 结构查看
   - 当前以 2D 骨架视图作为回退渲染路径
   - 预留 3D 视图后端抽象，方便未来接入真实渲染器

3. **操作工作流与设备工具**
   - 关节滑块和姿态预设
   - 工作区导航与选中详情
   - 串口 / 网络 / 设备控制台骨架
   - 远程遥测、日志和适合 Windows 打包发布的启动脚本

长期目标是让整个系统像一个专业工程工作台一样，把 CAD 生成、机器人装配和模型操作真正连成一体。

## 运行方式

Windows 上推荐使用：

```powershell
.\run.ps1
```

或者双击：

```bat
start.bat
```

也可以使用：

```bash
py -3.12 main.py
```

## 当前版本

- 当前版本线：`v0.5.0`
- CAD 跑道已进入主界面，包含概览、工作流链接、编辑演示、导出元数据和 CAD 到机器人联动快照
- telemetry 与设备控制台的状态链路已经在真实工作流路径中完成验证
- 产品仍保持稳定可启动，同时保留机器人工作区作为主交互区域

## 原型包含内容

- 深色工程风格桌面壳
- 2D 骨架视图，支持自动居中和关节驱动运动学
- 3D 占位视图，后续可替换为真实后端
- 可插拔渲染后端架构
- 关节滑块和姿态预设（`Home`、`Reach`、`Inspect`）
- 工作区浏览骨架
- 项目树、URDF 结构树、详情面板和资源摘要面板
- 统一机器人模型层（`robot_model.py`）
- 视图渲染协议（`rendering.py`）
- 运动链构建与正向运动学求解
- 串口 / 网络 / 任务面板骨架
- 为 telemetry 和嵌入式工作流预留的模块化布局

## CAD 工作流愿景

CAD 层以 `models/<robot>/` 下的独立 Python 脚本为核心。

示例概念：

```python
from cad import workspace

with workspace("wrist_link") as w:
    body = w.box(60, 50, 30)
    body = body.edges("|Z").fillet(2)      # @cad: edge_rounding
    body = body.faces(">Y").workplane()     # @cad: shaft_mount
    body = body.circle(15).extrude(20)
    w.export("wrist_link", ["step", "stl", "dxf", "glb"])
```

项目的关键规则是，AI 应该能够：
- 通过稳定句柄识别特征
- 只编辑相关脚本局部
- 在不重新生成整个模型的情况下完成再导出
- 把结果继续带入 URDF 和机器人视图工作流

## 项目记忆

- `CLAUDE.md` 保存长期上下文工作约定
- 所有改动坚持稳定优先，保持可启动和可运行

## 依赖安装

```bash
pip install -r requirements.txt
```

当前尚未正式纳入运行依赖的 CAD 计划依赖：

```bash
pip install cadquery trimesh ezdxf
```

## Windows 打包方向

使用以下命令构建可执行文件：

```powershell
.\build.ps1
```

生成的 exe 会由 PyInstaller 输出到 `dist` 目录。
