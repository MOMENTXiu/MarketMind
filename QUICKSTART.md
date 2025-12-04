# 快速开始指南

## ✅ 环境已配置完成

您的 MarketMind 项目环境已经配置完成！

- ✅ Python 3.13.9
- ✅ 虚拟环境: `.venv/`
- ✅ 依赖锁文件: `uv.lock`
- ✅ 62 个包已安装

---

## 🚀 常用命令

### 激活虚拟环境

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```cmd
.venv\Scripts\activate
```

### 使用 uv run 直接运行（推荐）

无需手动激活环境，直接使用 `uv run`:

```bash
# 运行 Web 界面
uv run streamlit run app.py

# 运行完整分析
cd analysis
uv run python marketing_modeling.py

# 运行 Python 脚本
uv run python your_script.py
```

### 包管理

```bash
# 添加新包
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 删除包
uv remove package-name

# 更新所有包
uv sync --upgrade

# 查看已安装的包
uv pip list
```

---

## 📦 已安装的核心包

| 包名 | 版本 | 用途 |
|------|------|------|
| pandas | 2.3.3 | 数据处理 |
| numpy | 2.3.5 | 数值计算 |
| scikit-learn | 1.7.2 | 机器学习 |
| mlxtend | 0.23.4 | 关联规则 |
| matplotlib | 3.10.7 | 可视化 |
| seaborn | 0.13.2 | 统计可视化 |
| streamlit | 1.52.0 | Web界面 |
| plotly | 6.5.0 | 交互式图表 |
| edge-tts | 7.2.3 | 语音合成 |
| statsmodels | 0.14.5 | 统计模型 |

---

## 🎯 快速测试

### 1. 测试环境
```bash
uv run python -c "import pandas, numpy, sklearn, streamlit; print('✅ 环境正常')"
```

### 2. 运行 Web 界面
```bash
uv run streamlit run app.py
```
然后在浏览器访问: http://localhost:8501

### 3. 运行数据分析
```bash
cd analysis
uv run python marketing_modeling.py
```

---

## 📁 项目结构

```
MarketMind/
├── .venv/                 # 虚拟环境（不要提交到git）
├── analysis/              # 数据分析模块
│   ├── dataset.csv       # 原始数据
│   ├── marketing_modeling.py  # 主分析程序
│   └── *.png             # 生成的图表
├── app.py                # Streamlit Web界面
├── pyproject.toml        # 项目配置
├── uv.lock               # 依赖锁文件
├── .python-version       # Python版本锁定
├── README.md             # 项目说明
└── QUICKSTART.md         # 本文档
```

---

## 🔧 常见问题

### Q: 如何添加新的依赖包？
```bash
uv add package-name
```

### Q: 如何更新某个包？
```bash
uv add package-name@latest
```

### Q: 如何在新机器上恢复环境？
```bash
git clone your-repo
cd MarketMind
uv sync
```

### Q: 如何检查 Python 版本？
```bash
uv run python --version
# 应该显示: Python 3.13.9
```

---

## 🎓 开发工作流

### 日常开发
```bash
# 1. 编写代码
vim your_script.py

# 2. 运行测试
uv run python your_script.py

# 3. 添加新依赖（如果需要）
uv add new-package

# 4. 提交代码
git add .
git commit -m "描述你的修改"
```

### 团队协作
```bash
# 1. 拉取最新代码
git pull

# 2. 同步依赖
uv sync

# 3. 开发...
# 4. 提交时确保 uv.lock 也提交
git add pyproject.toml uv.lock
```

---

## 📚 相关文档

- [uv 官方文档](https://docs.astral.sh/uv/)
- [项目规划文档](PROJECT_PLAN.md)
- [分析报告](analysis/分析报告.md)

---

**配置完成时间**: 2025-12-04
**Python 版本**: 3.13.9
**uv 版本**: 0.9.5
