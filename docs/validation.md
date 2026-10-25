# 实测结果与验收边界

日期 2026-10-25，Asia/Shanghai。

| 检查 | 结果 |
| --- | --- |
| 正式 AstrBot / WebUI | 4.29.3 / v4.29.3 |
| HTTP `/`、`/api/stat/versions`、`/api/v1/stats/versions` | 均 200 |
| Python | 3.12.3，`/opt/py3_12/bin/python` |
| 系统 Python 3.11 隔离 | system-site-packages=false，sys.path 无 Python 3.11/dist-packages |
| uv 依赖检查 | 150 包，All installed packages are compatible |
| 实际版本对照目标清单 | 150/150 完全相同 |
| 服务重启 | active/running，NRestarts=0 |
| 插件 / QQ 官方适配器 | 加载 6 个 / 2 个 |
| 本次启动错误 | 0；原始业务日志不发布 |
| 主数据库 / 知识库数据库 | SQLite quick_check 均 ok |
| FAISS 导入路径 | 正式 `/opt/py3_12/lib/python3.12/site-packages/faiss` |
| FAISS / NumPy | 1.14.3 / 2.4.4 |
| QEMU、隔离板上测试、正式环境测试 | 均通过 |
| 从旧公开 venv 构建新版干净包 | 150 包、pip check、核心导入及 FAISS 测试通过 |

FAISS 的 8 组检查：FlatL2 距离/排序对比 NumPy；大于 2^31 的 int64 ID；reconstruct；Flat/IDMap/IVF 序列化往返；IVFFlat 训练与搜索；C++ 调用 Python selector 并正确删除向量；HNSW；OnDiskInvertedLists 分配、缩容和释放。

最终 ELF 为 ARMv7 hard-float、NEON/VFPv4。核心和 callbacks 静态并入 `_swigfaiss.so`，不再依赖旧 `libfaiss.so`。RUNPATH=`$ORIGIN`；BLAS/LAPACK、OpenMP、libstdc++ 等动态库在实机全部找到，不依赖 OpenBLAS。

干净恢复包的来源为旧公开 `py3_12.tar.gz`（134 包）加 20 个 SHA256 已校验 wheel，得到与板上相同的 150 个版本。没有从生产业务目录复制内容进入恢复包。

未覆盖：对外 IM 消息、付费模型调用、每个插件的所有业务功能、满负载压力测试、全部上游 FAISS 测试；知识库没有已存在的 FAISS 索引文件可供迁移验收。2 个 QQ 适配器加载且启动 websocket 会话，不把这项日志单独等同于消息收发端到端验收。

继承旧 runtime 的已知缺项 `_lzma`、SILK 编码后端、PyYAML C 加速仍保持原状态。需要这些功能时另行构建 Python 3.12 对应扩展；不能用系统 Python 3.11 的 `.so` 顶替。没有把本次 AstrBot 版本更新描述成完整 CPython runtime 重建。

完整脱敏证据见 validation 目录；源码哈希、构建包版本和 ABI 见 manifests 目录。
