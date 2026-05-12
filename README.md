<p align="center">
  <h1 align="center">🌠 DaysMatter</h1>
  <p align="center"><em>流星划过许愿单 — 你的私人倒数日、愿望矩阵与备忘录系统</em></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.4.6.1-blue" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="python">
  <img src="https://img.shields.io/badge/docker-ready-brightgreen" alt="docker">
</p>

---

## ✨ 功能概览

### 📅 倒数日
- 多倒数本分类管理（首页 / 全部 / 归档 / 自定义）
- 重复事件（按天 / 周 / 月循环），**今天到期时显示提醒标识**
- 置顶、首页展示、高亮醒目、emoji 图标
- **附图管理**：上传图片、Lightbox 预览、左右切换浏览，按事项 ID 独立文件夹存储

### 🌟 愿望单
- **Wish Matrix 2×2 象限**：人生影响力 × 内心渴望值
- **优先级 ROI 公式**：`(Ripple × Fire) / Difficulty`
- 拖拽卡片跨象限移动、双滑块坐标选择
- 步骤拆解（1:N），进度自动计算
- 愿景板 ≤30 张，GLightbox 灯箱预览
- **心路历程**：Quill.js 富文本、QQ 签名式管理、荣誉墙滚动 + 渐变遮罩
- 状态筛选（全部 / 草稿 / 进行中 / 已达成）
- 庆祝达成 🎉 confetti 特效 + Canvas 流星许愿星空

### 📝 备忘录
- Gmail 式列表：星标 / 摘要 / 时间 / 附件图标
- **Vditor Markdown 编辑器**：实时预览、大纲目录、代码高亮、图片拖拽粘贴上传
- 读写分离：阅读模式 → 点击编辑 → 原地切换编辑器
- 附件管理：文件夹扫描、图片 Lightbox 预览、文件下载、延迟删除

### ⚙️ 系统功能
- **登录鉴权**：Flask-Login + werkzeug 密码哈希 + 记住我 (30天) + 暴力破解防护
- **SPA 导航**：无刷新页面切换，浏览器前进/后退支持
- **壁纸系统**：上传 / 随机切换 / 定时轮换 / localStorage 生命周期
- **内容区透明度**：滑块实时调节，CSS Variables 持久化
- **全量备份**：一键打包 `data/` 文件夹为 zip 镜像下载
- **调试日志**：RotatingFileHandler 10MB×10，开关控制
- **i18n 双语**：中文 / English

---

## 📦 快速开始 (Docker)

```bash

```

默认登录凭证: `admin` / `change_me_please`（**生产环境务必修改！**）

---

## 📁 数据持久化

所有用户数据存储在 Docker 卷映射的宿主机目录：

```
/opt/docker-stacks/daysmatter/
├── database/
│   └── main.db          # SQLite 数据库
├── uploads/
│   ├── countdown_days/  # 倒数日附图 (按 ID 分文件夹)
│   ├── wishlist/        # 愿望单愿景板
│   └── memos/           # 备忘录附件 + content.md
├── backgrounds/         # 壁纸图片
├── json/                # 配置文件 (settings.json / quotes.json / i18n)
└── log/                 # 调试日志 (app.log)
```

---

## 🔧 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_USERNAME` | `admin` | 登录用户名 |
| `APP_PASSWORD` | `daysmatter2024` | 登录密码 |
| `SECRET_KEY` | 随机生成 | Flask Session 签名密钥（生产环境建议固定） |
| `TZ` | `Asia/Shanghai` | 容器时区 |

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 / Flask 3.0 / SQLite (WAL) / Flask-Login |
| 前端 | Vanilla JS (ES6+) / SPA 导航 / CSS Variables |
| 编辑器 | Vditor (Markdown) / Quill.js (富文本) |
| 媒体 | GLightbox (灯箱) / Flatpickr (日期) / canvas-confetti (特效) |
| 部署 | Docker / Docker Compose / Alpine Linux |

---

## 📖 文档

完整技术文档请阅读 [`TECHNICAL_REFERENCE.md`](TECHNICAL_REFERENCE.md)，包含：

- 系统架构图与数据流向
- 数据库 Mermaid ER 图（全部 8 张表）
- 所有 API 端点字典（40+ 路由）
- 核心业务逻辑详解
- 完整版本演进历史

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源发布。

---

<p align="center">
  <sub>每一颗流星，都是一个未完成的愿望 ✨</sub>
</p>
