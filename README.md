<div align="center">

<img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+">
<img src="https://img.shields.io/badge/PySide6-6.9.2-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PySide6 6.9.2">
<img src="https://img.shields.io/badge/OpenGL-2.1%2FES-5586A4?style=for-the-badge&logo=opengl&logoColor=white" alt="OpenGL 2.1/ES">
<img src="https://img.shields.io/badge/Platform-Windows%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 11">
<img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License: MIT">
<img src="https://img.shields.io/badge/Tests-95%20passed-4ADE80?style=for-the-badge" alt="Tests: 95 passed">
<img src="https://img.shields.io/badge/Version-v0.7.5--dev-9B59B6?style=for-the-badge" alt="Version v0.7.5-dev">

<br>
<br>

# 🤖 Robot URDF Studio

**Industrial Engineering Workbench for Robot Modelling, CAD Scripting, and Device Tooling**

A Windows 11 desktop application that unifies CAD generation, URDF-based robot visualisation, and embedded-device operator workflows into a single professional workspace.

</div>

<p align="center">
  <b><a href="#english">English</a></b> &nbsp;|&nbsp;
  <b><a href="#中文">中文</a></b> &nbsp;|&nbsp;
  <b><a href="#日本語">日本語</a></b>
</p>

---

## 📸 Preview

```
 ┌──────────────────────────────────────────────────────────────┐
 │  [File]  [CAD]  [Device]  [View]  [Run]  [Logs]  [About]   │  ← Top Navigation
 ├──────────────┬────────────────────────┬──────────────────────┤
 │              │                        │   Joint control      │
 │  Project     │                        │   ┌────────────────┐ │
 │  Recent      │   3D / 2D Viewport     │   │ base_yaw    0° │ │
 │  Tree        │                        │   │ [══════╪══════] │ │
 │              │    ░░░░░░░░░░░░░░      │   │ shoulder    30° │ │
 │  Selection   │    ░░ Robot   ░░░░     │   │ [════╪════════] │ │
 │  Details     │    ░░  Model  ░░░░     │   │ elbow       45° │ │
 │              │    ░░░░░░░░░░░░░░      │   │ [════════╪════] │ │
 │  URDF        │                        │   └────────────────┘ │
 │  Resources   │    Grid · Axes · Cam   │   [Home][Reach][Ins] │
 │              │                        │   [Reset]  [Copy]    │
 ├──────────────┴────────────────────────┴──────────────────────┤
 │  Event log and telemetry output                               │
 └──────────────────────────────────────────────────────────────┘
```

---

<h2 id="english">🇬🇧 English</h2>

## ✨ Features

<table>
  <tr>
    <td width="50%">
      <h4>🎨 CAD Generation & Editing</h4>
      <ul>
        <li>Per-part Python scripts (CadQuery-ready)</li>
        <li><code>@cad</code> handle system for precise geometric feature targeting</li>
        <li>Export to STEP, STL, DXF, GLB, URDF, topology data</li>
        <li>Incremental editing without full model regeneration</li>
      </ul>
    </td>
    <td width="50%">
      <h4>🦾 Robot Visualisation</h4>
      <ul>
        <li>URDF import, parsing, and structure tree inspection</li>
        <li>Real-time 3D mesh viewport with multi-link FK transforms</li>
        <li>3D picking (face/edge/vertex raycasting)</li>
        <li>Pluggable rendering backend (2D skeleton / 3D OpenGL)</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td>
      <h4>🎮 Joint Control & Animation</h4>
      <ul>
        <li>Per-joint sliders with spin-box and range limits</li>
        <li>Pose presets with quintic-eased tweening</li>
        <li>EMA-follow for smooth real-time slider response</li>
        <li>Dynamic panel rebuilt from parsed URDF joint data</li>
      </ul>
    </td>
    <td>
      <h4>🔧 Device & Operator Tools</h4>
      <ul>
        <li>Serial / TCP / CAN console scaffolding</li>
        <li>Telemetry dashboard (heartbeat, temperature, voltage, motion)</li>
        <li>Workflow snapshot with delta-change detection</li>
        <li>Windows packaging via PyInstaller</li>
      </ul>
    </td>
  </tr>
</table>

## 🏗 Architecture

```
robot-urdf-studio/
├── app/                   # Application bootstrap & main window
│   ├── main.py            #   Entry point, QApplication init
│   └── window.py          #   MainWindow shell & signal wiring
├── ui/                    # UI panels, widgets, navigation
│   ├── shell.py           #   WorkspaceShell — layout orchestrator
│   ├── top_nav.py         #   TopNavigationBar — dynamic i18n menus
│   ├── cad_panel.py       #   CadOverviewPanel — runway status
│   ├── cad_workspace.py   #   CadWorkflowPanel — interop bridge
│   ├── workflow_status.py #   Snapshot model & delta comparison
│   └── collapsible.py     #   Reusable collapsible section widget
├── robot/                 # Kinematics, animation, chain building
│   ├── fk.py              #   3D FK (Rodrigues rotation, tree DFS)
│   ├── chain.py           #   KinematicChain with auto-topology
│   └── animation.py       #   Quintic easing, EMA follow, wrap-around
├── cad/                   # CAD scripting & editing layer
│   ├── handles.py         #   @cad feature handle system
│   ├── editors.py         #   CadFeatureEditor — handle-driven edits
│   ├── pipeline.py        #   Export pipeline (STEP/STL/DXF/GLB/URDF)
│   ├── edit_bridge.py     #   Undo/redo + pick-to-handle mapping
│   └── _demo_factory.py   #   Shared demo part builders
├── studio_io/             # I/O adapters & data contracts
│   ├── mesh_data.py       #   MeshData / MeshPart canonical contract
│   ├── mesh_loader.py     #   STL, GLB/GLTF, primitive mesh loaders
│   ├── urdf_mesh_builder.py # URDF visual → MeshData + FK posing
│   ├── picking.py         #   Möller-Trumbore raycasting, MeshPicker
│   ├── urdf_io.py         #   URDF parse, validate, convert
│   ├── urdf_writer.py     #   Model → URDF XML export
│   ├── cad_mesh_bridge.py #   CadQuery → MeshData (optional)
│   └── viewport_state.py  #   Camera/display state persistence
├── models/                # Robot URDFs, STL meshes, CAD scripts
├── tests/                 # 95-unit test suite (pytest)
├── assets/                # QSS theme, icons, static resources
├── rendering.py           # OpenGL Mesh3DWidget, backends, lighting
├── robot_model.py         # RobotModel, JointSpec, ViewState domain
├── i18n.py                # en/zh language manager (140+ keys)
├── config.py              # Central StudioConfig geometry defaults
├── CLAUDE.md              # Long-context development contract
├── VERSIONING.md          # Milestone plan & 3D readiness assessment
└── main.py                # Launch entry point
```

## 🚀 Quick Start

### Prerequisites

- **Windows 11** (primary target platform)
- **Python 3.12** (standard install — Windows Store version has sandbox limitations)
- Git

### Install

```bash
git clone https://github.com/Nagi-226/Robot-URDF.git
cd Robot-URDF
pip install -r requirements.txt
```

Optional CAD and mesh dependencies:

```bash
pip install cadquery trimesh ezdxf
```

### Launch

```powershell
.\run.ps1
```

Or double-click `start.bat`, or run directly:

```bash
py -3.12 main.py
```

### Run Tests

```bash
pytest tests/ -v
```

### Build Windows EXE

```powershell
.\build.ps1 -Mode onefile -SkipInstall -SmokeTest
```

Packaging outputs `dist\RobotURDFStudio.exe`. For a debug-friendly folder build, use `.\build.ps1 -Mode onedir -SkipInstall -SmokeTest`. Dev signing is available through `scripts\sign_windows_dev.ps1`; see `packaging\RELEASE_CHECKLIST.md`.

## ⌨️ Key Bindings

| Input | Action |
|-------|--------|
| `Left-drag` | Orbit camera |
| `Scroll wheel` | Zoom in / out |
| `Click` (no drag) | Pick face / edge / vertex |
| `Right panel sliders` | Adjust joint angles |
| `Pose presets` | Animate to Home / Reach / Inspect |

## 🗺 Roadmap

| Milestone | Focus |
|-----------|-------|
| **v0.6.6** | Complete edge/vertex picking, selection highlighting |
| **v0.6.7** | URDF mesh integration, multi-light shader upgrade |
| **v0.6.8** | Animation wiring, viewport chrome (grid, axes, toolbar) |
| **v0.6.9** | CAD geometry pipeline (CadQuery → MeshData → Viewport) |
| **v0.7.0** | Integrated 3D workspace — CAD + Robot in one scene |
| **v1.0.0** | Production-ready Windows packaging & direct exe delivery |

See [VERSIONING.md](VERSIONING.md) for detailed milestones and the 3D readiness assessment.

## 🤝 Contributing

This project follows a **stability-first** development strategy:

1. Keep the application launchable at every step
2. Build features in thin vertical slices
3. Prefer small modular files over monoliths
4. Avoid speculative abstractions
5. All changes must pass the existing test suite

The [CLAUDE.md](CLAUDE.md) file serves as the long-context working contract for both human and AI contributors.

---

<h2 id="中文">🇨🇳 中文</h2>

## ✨ 功能特性

<table>
  <tr>
    <td width="50%">
      <h4>🎨 CAD 生成与编辑</h4>
      <ul>
        <li>每个零件对应独立 Python 脚本（CadQuery 兼容）</li>
        <li><code>@cad</code> 句柄系统，精确定位几何特征</li>
        <li>导出格式：STEP、STL、DXF、GLB、URDF、拓扑数据</li>
        <li>增量编辑，无需重新生成整个模型</li>
      </ul>
    </td>
    <td width="50%">
      <h4>🦾 机器人可视化</h4>
      <ul>
        <li>URDF 导入、解析与结构树查看</li>
        <li>实时 3D 网格视口，多连杆 FK 变换</li>
        <li>3D 拾取系统（面/边/顶点射线检测）</li>
        <li>可插拔渲染后端（2D 骨架 / 3D OpenGL）</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td>
      <h4>🎮 关节控制与动画</h4>
      <ul>
        <li>逐关节滑块 + 数值框 + 范围限制</li>
        <li>姿态预设，五次缓动过渡动画</li>
        <li>EMA 跟随，滑块实时响应平滑</li>
        <li>面板由 URDF 关节数据动态构建</li>
      </ul>
    </td>
    <td>
      <h4>🔧 设备与操作工具</h4>
      <ul>
        <li>串口 / TCP / CAN 控制台骨架</li>
        <li>遥测仪表板（心跳、温度、电压、运动状态）</li>
        <li>工作流快照 + 增量变更检测</li>
        <li>PyInstaller Windows 打包</li>
      </ul>
    </td>
  </tr>
</table>

## 🏗 项目架构

```
robot-urdf-studio/
├── app/                   # 应用启动与主窗口
├── ui/                    # UI 面板、控件、导航
├── robot/                 # 运动学、动画、链构建
├── cad/                   # CAD 脚本与编辑层
├── studio_io/             # I/O 适配器与数据合约
├── models/                # 机器人 URDF、STL 网格、CAD 脚本
├── tests/                 # 95 项单元测试 (pytest)
├── assets/                # QSS 主题、图标、静态资源
├── rendering.py           # OpenGL 渲染引擎与后端
├── robot_model.py         # 机器人领域模型
├── i18n.py                # 中英文语言管理器 (140+ 键)
├── config.py              # 统一配置数据中心
├── CLAUDE.md              # 长期开发上下文合约
├── VERSIONING.md          # 里程碑规划与 3D 就绪评估
└── main.py                # 启动入口
```

## 🚀 快速开始

### 环境要求

- **Windows 11**（主要目标平台）
- **Python 3.12**（需使用标准安装，Windows Store 版本存在沙箱限制）

### 安装

```bash
git clone https://github.com/Nagi-226/Robot-URDF.git
cd Robot-URDF
pip install -r requirements.txt
```

可选 CAD 与网格依赖：

```bash
pip install cadquery trimesh ezdxf
```

### 启动

```powershell
.\run.ps1
```

或双击 `start.bat`，或直接运行：

```bash
py -3.12 main.py
```

### 运行测试

```bash
pytest tests/ -v
```

## 🗺 路线图

| 里程碑 | 重点 |
|--------|------|
| **v0.6.6** | 完成边/顶点拾取、选中高亮 |
| **v0.6.7** | URDF 网格集成、多灯光着色器 |
| **v0.6.8** | 动画接入、视口装饰（网格、坐标轴、工具栏） |
| **v0.6.9** | CAD 几何管线（CadQuery → MeshData → 视口） |
| **v0.7.0** | 一体化 3D 工作台 — CAD + 机器人同场景 |
| **v1.0.0** | 生产就绪的 Windows 打包与 exe 交付 |

详见 [VERSIONING.md](VERSIONING.md)。

---

<h2 id="日本語">🇯🇵 日本語</h2>

## ✨ 機能

<table>
  <tr>
    <td width="50%">
      <h4>🎨 CAD 生成と編集</h4>
      <ul>
        <li>パーツごとの Python スクリプト（CadQuery 対応）</li>
        <li><code>@cad</code> ハンドルシステムで形状特徴を精密に指定</li>
        <li>STEP、STL、DXF、GLB、URDF、トポロジデータにエクスポート</li>
        <li>モデル全体を再生成しない差分編集</li>
      </ul>
    </td>
    <td width="50%">
      <h4>🦾 ロボット可視化</h4>
      <ul>
        <li>URDF インポート、解析、構造ツリー表示</li>
        <li>マルチリンク FK 変換対応のリアルタイム 3D メッシュビュー</li>
        <li>3D ピッキング（面・辺・頂点のレイキャスト）</li>
        <li>プラグ可能なレンダリングバックエンド（2D 骨格 / 3D OpenGL）</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td>
      <h4>🎮 関節制御とアニメーション</h4>
      <ul>
        <li>関節ごとのスライダー＋スピンボックス＋範囲制限</li>
        <li>五次緩和イージングによるポーズプリセット遷移</li>
        <li>EMA フォローによるスムーズなリアルタイム応答</li>
        <li>URDF 関節データから動的に再構築されるパネル</li>
      </ul>
    </td>
    <td>
      <h4>🔧 デバイス・オペレータツール</h4>
      <ul>
        <li>シリアル / TCP / CAN コンソールスキャフォールド</li>
        <li>テレメトリダッシュボード（心拍、温度、電圧、動作状態）</li>
        <li>ワークフロースナップショット＋差分検出</li>
        <li>PyInstaller による Windows パッケージング</li>
      </ul>
    </td>
  </tr>
</table>

## 🚀 クイックスタート

### 前提条件

- **Windows 11**（主要ターゲットプラットフォーム）
- **Python 3.12**（標準インストール — Windows Store 版はサンドボックス制限あり）

### インストール

```bash
git clone https://github.com/Nagi-226/Robot-URDF.git
cd Robot-URDF
pip install -r requirements.txt
```

### 起動

```powershell
.\run.ps1
```

または `start.bat` をダブルクリック、もしくは直接：

```bash
py -3.12 main.py
```

## 🗺 ロードマップ

| マイルストーン | 焦点 |
|---------------|------|
| **v0.6.6** | 辺・頂点ピッキングの完成、選択ハイライト |
| **v0.6.7** | URDF メッシュ統合、マルチライトシェーダー |
| **v0.6.8** | アニメーション接続、ビューポートクローム |
| **v0.6.9** | CAD ジオメトリパイプライン |
| **v0.7.0** | 統合 3D ワークスペース |
| **v1.0.0** | プロダクション向け Windows パッケージング |

詳細は [VERSIONING.md](VERSIONING.md) を参照してください。

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built with Python · PySide6 · OpenGL · CadQuery · trimesh</sub>
</p>
