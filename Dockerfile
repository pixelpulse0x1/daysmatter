# DaysMatter — Docker 镜像构建文件
# 基础镜像: Python 3.12 Alpine (最小化体积)

FROM python:3.12-alpine

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# tzdata: 时区数据，支持容器内设置 Asia/Shanghai
RUN apk add --no-cache tzdata

# 设置容器默认时区
ENV TZ=Asia/Shanghai

# 安装 Python 依赖
# 先复制 requirements.txt 以利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 预置壁纸已随 app/static/default_bg/ 一起复制

# 预创建数据目录结构
# 确保 /data 下的子目录存在，避免首次启动时的权限问题
RUN mkdir -p /data/database /data/uploads/photos /data/backgrounds /data/json

# 暴露应用端口
EXPOSE 3150

# 启动命令:
# 1. 初始化数据库 (建表 + 迁移)
# 2. 创建 Flask 应用
# 3. 监听 0.0.0.0:3150，允许外部访问
CMD ["python", "-c", "from app import create_app; from app.modules.database import init_db; init_db(); app = create_app(); app.run(host='0.0.0.0', port=3150, debug=False)"]
