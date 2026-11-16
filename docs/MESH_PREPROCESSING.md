# 网格预处理（Mesh Preprocessing）

本文说明 `studio_io/mesh_ops.py` 的能力、参数来源，以及**我们能做到什么、做不到什么**。

- 代码：`studio_io/mesh_ops.py`
- 测试：`tests/test_mesh_ops.py`
- 命令行：`.venv/Scripts/python.exe -m studio_io.mesh_ops <in.stl> --target-faces N --out out.stl`

---

## 1. 为什么需要这一层

Robot URDF Studio 的核心用途是"兼容各种板子的模型"。板子模型从 CAD 导出通常带三个问题：

| 问题 | 后果 | 本模块的处理 |
|---|---|---|
| 面数太大（几万–几十万） | URDF 加载慢、渲染卡、`<collision>` 让物理仿真爆 | `decimate()` |
| `<collision>` 必须凸 | 非凸碰撞体会被物理引擎静默替换或行为异常 | `convex_hull()` / `to_collision_mesh()` |
| CAD 导出脏（重复顶点、零面积面、重复面、孤立点） | 法线/包围盒错、渲染破面、后续算法炸 | `clean()` |

`mesh_stats()` 用来在前后各测一次，把"我确实改了什么"变成数字而不是感觉。

---

## 2. ⚠️ 许可证边界（必读）

| 项目 | 许可证 |
|---|---|
| Robot URDF Studio（本仓库） | README 标注 **MIT**（仓库根目录**无** `LICENSE` 文件，仅徽章声明） |
| **MeshLab**（参数与算法参考来源） | **GPL v3** |

**结论：本项目没有、也不会复制 MeshLab 的任何代码。**

- 参考的那几个文件**只读**，用于确认**参数名称、默认值、语义**；
- 参数名/默认值是**接口事实**（类似"函数叫 `target_count`"），不受版权保护；
- 算法实现来自 **`fast-simplification`（MIT）** 与 **`trimesh`/`scipy`（BSD-3）**，两者许可证与 MIT 兼容。

如果有人后续想把 MeshLab 的 C++ 实现直接搬进来：**不行**，GPL v3 的传染性会让整个 Studio 变成 GPL。

---

## 3. MeshLab quadric 简化参数 ↔ `fast_simplification` 对照表

MeshLab 侧参数取自 `MeshLab-src/src/meshlabplugins/filter_meshing/meshfilter.cpp` 的
`FP_QUADRATIC_EDGE_COLLAPSE` 分支（参数声明 `:469-481`，读取与应用 `:996-1008`），
默认值取自 `vcglib/vcg/complex/algorithms/local_optimization/tri_edge_collapse_quadric.h:85-104`。

`fast_simplification` 侧取自其 `simplify()` 签名（`fast_simplification/simplify.py:38` 起）。

### 3.1 能映射的（3 项）

| MeshLab 参数 | 类型 | 默认值 | 含义 | 映射到 | 备注 |
|---|---|---|---|---|---|
| `TargetFaceNum` | int | `fn/2`（有选区时为 `sfn/2`） | 目标面数 | `target_count=N` | 直接映射；本模块 `decimate(mesh, target_faces)` |
| `TargetPerc` | float | `0` | 非 0 时 `TargetFaceNum = fn × TargetPerc` | `target_count = fn × TargetPerc` | ⚠️ 标签写的是 "Percentage reduction"，但**代码里是"保留比例"**（`meshfilter.cpp:997`：`TargetFaceNum = m.cm.fn * TargetPerc`）。照标签理解会得到相反结果 |
| `PreserveBoundary` | bool | `false` | 尽量不动网格边界 | `preserve_border=True` | ⚠️ **部分映射**：只保证"不塌陷任何触及边界顶点的边"，没有权重可调 |

### 3.2 无法映射的（9 项）

| MeshLab 参数 | 类型 | 默认值 | 含义 | 没有对应项意味着什么 |
|---|---|---|---|---|
| `QualityThr` | float | `0.3` | 面质量惩罚阈值 [0..1]，低于阈值的三角被按比例惩罚 | **丢失**：无法按形状质量取舍，细长三角会被当正常面保留/折叠 |
| `BoundaryWeight` | float | `0.5`（与 vcglib 默认 `BoundaryQuadricWeight` 相乘） | 边界重要性倍率 (0,+inf) | **丢失**：边界只有"全保/全不保"两档，不能"轻推" |
| `PreserveNormal` | bool | `false` | 避免翻面、尽量保持原始朝向 | **丢失**：简化后可能出现局部翻面（本模块不自动翻转修正） |
| `PreserveTopology` | bool | `false` | 不产生改变拓扑的塌陷（不闭洞、不捏掉手柄） | **丢失**：可能把孔洞闭合、把薄的环状特征捏成实心。`fast_simplification` 不提供该保证 |
| `OptimalPlacement` | bool | **`true`** | 折叠后新顶点放在最小化二次误差的位置 | **丢失（无开关）**：无法退回"新顶点只取原有顶点之一"的模式 |
| `PlanarQuadric` | bool | `false` | 对平面区域附加二次型约束，保留更多、更规整的平面三角 | **丢失**：大平面（板子正面最常见）可能被简化出畸形长条三角 |
| `PlanarWeight` | float | `0.001` | 平面保留的权重 | **丢失**：同上，且不可调 |
| `QualityWeight` | bool | `false` | 用逐顶点质量做误差放大 | **丢失**：本模块没有 per-vertex quality 通道（导入格式里也没有质量字段） |
| `Selected` | bool | 有选区时 `true` | 只简化选中的面 | **丢失**：无选择概念，`decimate()` 处理整网 |

### 3.3 「MeshLab 有、fast_simplification 也有，但概念不同」的 1 项

| MeshLab 参数 | 默认值 | 我们的做法 |
|---|---|---|
| `AutoClean` | **`true`** | `decimate()` **不自动** clean（保持纯函数、单一职责）。需要时显式调 `clean(decimate(...))`；CLI 里加 `--clean`。**这处差别是刻意的**：MeshLab 的自动清理会让人看不出"我的面怎么少了"，显式调用才可审计 |

### 3.4 「我们有、MeshLab 没有」的 1 项

| 参数 | 默认值 | 含义 |
|---|---|---|
| `aggressiveness`（→ `agg`） | `7.0` | 简化激进度 0–10。0 最保形（慢，可能到不了目标面数），10 最快最糙。MeshLab 的 quadric 实现没有这个旋钮 |

---

## 4. 清理（`clean()`）与 MeshLab `filter_clean` 的对应

| MeshLab filter | 参数 | 我们是否做 | 说明 |
|---|---|---|---|
| Merge Close Vertices | `MergeThr`（绝对距离） | ✅ `merge_tol=1e-6` | ⚠️ **实现方式不同**：我们按 `merge_tol` 对坐标做**网格量化**后去重（O(n log n)、确定性），MeshLab 按空间距离球合并。代价：跨网格边界的近邻点不会被合并 |
| Remove Duplicate Faces | — | ✅ | 以"顶点集合"判重，**与绕序无关**（`[0,1,2]` 与 `[0,2,1]` 视为重复） |
| Remove Zero Area Faces | — | ✅ | 面积 < `1e-12` 判为退化（三点共线 / 面内重复顶点索引） |
| Remove Unreferenced Vertices | — | ✅ | 删面之后**必然**做，否则孤立点会污染包围盒与法线统计 |
| Remove Duplicate Vertices | — | ✅ | 合并步骤已经覆盖 |

`clean()` 返回 `(新 MeshData, report_dict)`，报告里有 `vertices_merged` /
`faces_degenerate_removed` / `faces_duplicate_removed` / `vertices_unreferenced_removed`。
**不要忽略这个报告** —— 它是"清理是否真的发生了"的唯一证据。

---

## 5. 凸包（`convex_hull()`）与 MeshLab `filter_qhull`

MeshLab 的 "Convex Hull" 除视野相关选项（`Use ViewPoint from Mesh Camera` / `ViewPoint`）外**没有几何参数**，
本质是 Qhull 的 `qhull` 调用。我们用 `trimesh.Trimesh.convex_hull`（后端 Scipy/Qhull），
**语义一致**：输入点集 → 最小凸多面体。

差异：
- MeshLab 支持"只对可见点求凸包"（用相机视点剔除背面的点）——**我们不做**，URDF 碰撞体不需要这个；
- 输入共面/共线时 trimesh 抛 `QhullError`，本模块包装成 `ValueError` 并说明原因。

`to_collision_mesh(mesh, max_faces=64)` = 凸包 → 减面到 `max_faces`。

---

## 6. 两个实现陷阱（写给后来改这个文件的人）

### 6.1 `MeshData.indices` 是**扁平** `M*3`，trimesh 要 `(M,3)`

`MeshData.indices` 存的是扁平数组，`len(indices)` 是**面数的三倍**。
直接喂给 trimesh 会得到一个"只有 1/3 面"的网格 —— 症状是"减面怎么减没了"，极难定位。

本模块在 `_as_face_matrix()` 里强制检查 `size % 3 == 0`，并在 `_to_trimesh()` 里
`assert len(tri.faces) == expected_faces`。**不要删这两个检查。**

### 6.2 `trimesh.Trimesh.unique_faces()` 返回**布尔掩码**，不是索引数组

```python
mask = tm.unique_faces()        # array([True, True, False, True])  ← 长度 == 面数
n_unique = int(mask.sum())      # 正确
n_unique = len(mask)            # 错误：恒等于面数 → 重复面永远报 0
```

这个 bug 在开发时真的写出来过，是被 `test_clean_removes_duplicate_and_degenerate_faces`
的反向断言（"fixture 必须先脏"）抓到的。

### 6.3 为什么 `decimate()` / `convex_hull()` 会清空 `parts`

`MeshPart.vertex_offset` / `triangle_offset` 是**相对原网格的索引**。减面与凸包都会
重新编号顶点与三角形，因此：

- 保留旧 offset ⇒ **不会崩**，但会把网格切成乱七八糟的碎块（最糟的一类 bug：静默出错）；
- 所以本模块**清空 `parts`**，并在 docstring 写明。

如果业务需要"每个 part 分别减面"，正确做法是**先按 part 拆网格，再逐个 decimate**，而不是减完再拆。

---

## 7. 依赖与许可证

| 包 | 版本（实测） | 许可证 | 用途 |
|---|---|---|---|
| `trimesh` | 4.12.2 | MIT | 网格容器、凸包、STL 导出、统计 |
| `scipy` | 1.18.1 | BSD-3 | trimesh 凸包的 Qhull 后端 |
| `fast-simplification` | 0.2.0 | MIT | quadric edge collapse 减面 |

三者均已写入 `requirements.txt`。

---

## 8. 已知限制

1. **只处理 STL / GLB / GLTF**：`load_mesh_auto()` 仍只认这三种（`studio_io/mesh_loader.py:452-457`）。
   OBJ / 3MF 支持是后续单，不在本次范围。
2. **不支持保留 UV / 顶点色**：减面后 `colors=None`；`clean()` 也不保留 `colors`。
3. **不保证减面后仍是流形**：`fast_simplification` 没有拓扑保持开关（见 §3.2）。
   做 `<collision>` 时因为先求凸包，这个问题被掩掉了；但如果你对 `<visual>` 减面，
   减完建议跑一次 `clean()` 并检查 `mesh_stats().watertight`。
4. **`merge_tol` 是网格量化而非球合并**（见 §4），跨边界近邻点不合并。
