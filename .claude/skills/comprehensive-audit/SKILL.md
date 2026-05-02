---
name: comprehensive-audit
description: "Robot URDF Studio 项目专用综合排查：架构可行性验收、BUG/冗余/代码耦合全项目总排查、优化修复建议。覆盖模块导入、测试套件、重复代码、死代码、i18n完整性、架构分层、信号连接、Windows路径等 12 个检查维度。"
category: project
risk: safe
source: project
date_added: "2026-05-02"
---

# Robot URDF Studio — 综合排查 Skill

项目专用全维度审计工作流。每次执行时按顺序完成以下检查清单，发现问题立即修复。

## 检查清单

### 1. 模块导入健康检查

```bash
python -c "
import sys; sys.path.insert(0, '.')
modules = [
    'app.main', 'app.window',
    'ui.shell', 'ui.top_nav', 'ui.collapsible',
    'ui.cad_panel', 'ui.cad_workspace', 'ui.workflow_status',
    'robot.chain', 'robot.fk', 'robot.animation',
    'robot_model', 'rendering', 'config', 'i18n',
    'studio_io', 'studio_io.mesh_data', 'studio_io.mesh_loader',
    'studio_io.urdf_io', 'studio_io.urdf_writer', 'studio_io.urdf_mesh_builder',
    'studio_io.picking', 'studio_io.cad_mesh_bridge', 'studio_io.file_io',
    'cad', 'cad.handles', 'cad.editors', 'cad.pipeline',
    'cad.demo', 'cad.interop', 'cad.edit_bridge', 'cad._demo_factory',
]
for m in modules:
    try:
        __import__(m)
        print(f'  OK  {m}')
    except Exception as e:
        print(f'FAIL {m}: {e}')
"
```

**判定标准**：全部 32 个模块必须 OK。

### 2. 全量测试套件

```bash
python -m pytest tests/ -v --tb=short
```

**判定标准**：100% 通过。

### 3. 重复代码检测

检查以下已知重复模式：

| 风险点 | 主副本位置 | 应删除的副本 |
|--------|-----------|-------------|
| 法线计算 | `studio_io/mesh_loader.py:_compute_normals` | `rendering.py:Mesh3DWidget._compute_vertex_normals`（已删除） |
| 4x4 矩阵乘法 | `robot/fk.py:_mult` | `studio_io/urdf_mesh_builder.py:_mult_m4`（注意） |
| origin→matrix | `studio_io/urdf_mesh_builder.py:_origin_to_matrix` | `robot/fk.py:_translate+_rotate_rpy` 组合等效（前者合并了translate+rotate，后者分开，功能等价但不算完全重复） |

使用 grep 验证：

```bash
grep -rn "def _compute_vertex_normals\|def _compute_normals" --include="*.py"
grep -rn "def _mult\|def _mult_m4" --include="*.py"
```

### 4. 死代码检测

- 搜索 `_apply_pose_immediate` — 应已删除
- 搜索只定义从未调用的方法：检查每个 `def` 是否有对应的调用点
- 检查未使用的 import：`grep -rn "from.*import\|^import"` 后逐项验证

### 5. i18n 完整性检查

```bash
# 搜索所有硬编码英文字符串（非 tr() 包裹的）
grep -rn '"[A-Z][a-z]* [a-z]*' ui/*.py app/*.py --include="*.py" | grep -v "tr(" | grep -v "__"
```

重点检查：
- `QLabel("...")`、`QPushButton("...")`、`setText("...")`、`setPlaceholderText("...")` 是否都走 `tr()`
- 新增的 i18n key 是否在 `i18n.py` 中已定义
- `_LANG_EN` 和 `_LANG_ZH` 是否长度一致

### 6. 架构分层验证

验证依赖方向符合 CLAUDE.md 规则：**UI → robot/rendering/CAD/studio_io，不可反向。**

```bash
# 检查反向依赖：robot/ 不应导入 ui/
grep -rn "from ui\." robot/ studio_io/ cad/ --include="*.py"
# 检查反向依赖：studio_io/ 不应导入 ui/
grep -rn "from ui\." studio_io/ --include="*.py"
# 检查反向依赖：rendering 不应导入 ui/
grep -rn "from ui\." rendering.py
```

### 7. 信号/槽连接验证

检查所有 `Signal()` 定义和 `.connect()` 调用是否匹配：
- `RobotViewport.pick_changed` ↔ `WorkspaceShell._update_details_from_pick`
- `JointSlider.spin.valueChanged` ↔ `WorkspaceShell._sync_view`
- `TopNavigationBar.*` signals ↔ `MainWindow._wire_top_nav` connections
- `I18nManager.language_changed` ↔ `TopNavigationBar._on_language_changed`

### 8. OpenGL 资源检查

- `_upload_buffers` 中旧 buffer 是否正确 `destroy()` 后再 `create()`
- `_install_backend_widget` 中旧 widget 是否正确 `deleteLater()`
- `initializeGL` 只在 OpenGL context 激活时调用一次

### 9. Windows 路径兼容性

```bash
grep -rn "Path(" --include="*.py" | grep -v "Path(__file__)"
grep -rn "str.*path\|path.*str" --include="*.py"
```

确保所有路径使用 `Path` 对象而非字符串拼接，斜杠统一为 `/`。

### 10. 未提交文件审计

```bash
git status --short
```

检查 `??` (untracked) 文件是否都有明确的模块归属，无用临时文件应清理。

### 11. 测试覆盖缺口

对比 `tests/` 目录与源文件：

| 已有测试 | 缺少测试 |
|---------|---------|
| test_cad_package.py (CAD) | i18n.py |
| test_rendering.py (viewport) | config.py |
| test_robot_package.py (FK) | ui/top_nav.py |
| test_ui.py (telemetry/snapshot) | cad/edit_bridge.py |
| — | robot/animation.py |

### 12. 启动验证

```bash
python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from app.window import MainWindow
w = MainWindow()
print('MainWindow OK - title:', w.windowTitle())
print('Top nav buttons:', len(w.top_nav._buttons))
from i18n import current_lang, set_language
print('Current lang:', current_lang())
set_language('en')
print('After switch:', current_lang())
app.quit()
"
```

---

## 使用方式

在对话中输入 `/comprehensive-audit` 或 "综合排查"、"全面检查"、"项目审计" 即可触发本 skill。

## 修复优先级

| 优先级 | 类型 | 示例 |
|--------|------|------|
| P0 立即 | 测试失败、模块导入错误、崩溃 bug | 95→93 退步 |
| P1 高 | 硬编码字符串(无 i18n)、信号连接错配 | `_update_details_from_pick` |
| P2 中 | 重复代码、死代码、未使用 import | `_apply_pose_immediate` |
| P3 低 | 测试覆盖缺口、代码风格 | animation.py 无测试 |
