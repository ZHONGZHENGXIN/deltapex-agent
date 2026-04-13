# Build AI Template API - Makefile
# 
# 常用开发命令的快捷方式

.PHONY: help install dev clean-imports check-imports format lint test

# 默认目标
help:
	@echo "Build AI Template API - 开发工具"
	@echo ""
	@echo "可用命令:"
	@echo "  install        安装依赖"
	@echo "  dev           启动开发服务器"
	@echo "  clean-imports  清理未使用的 import"
	@echo "  check-imports  检查代码格式（不修改）"
	@echo "  format        格式化代码"
	@echo "  lint          代码检查"
	@echo "  test          运行测试"
	@echo "  db-migrate    创建数据库迁移"
	@echo "  db-upgrade    执行数据库迁移"
	@echo ""

# 安装依赖
install:
	@echo "📦 安装依赖..."
	uv sync

# 启动开发服务器
dev:
	@echo "🚀 启动开发服务器..."
	python -m app.main

# 清理未使用的 import（修复模式）
clean-imports:
	@echo "🧹 清理未使用的 import..."
	./scripts/clean_imports.sh

# 检查代码格式（检查模式）
check-imports:
	@echo "🔍 检查代码格式..."
	./scripts/clean_imports.sh check

# 格式化代码（仅格式化，不清理 import）
format:
	@echo "✨ 格式化代码..."
	black --line-length 128 app
	isort --profile black --line-length 128 app

# 代码检查
lint:
	@echo "🔍 代码检查..."
	black --line-length 128 --check app
	isort --profile black --line-length 128 --check-only app
	autoflake --remove-all-unused-imports --remove-unused-variables --ignore-init-module-imports --check --recursive app

# 运行测试（如果有的话）
test:
	@echo "🧪 运行测试..."
	@echo "暂未配置测试"

# 创建数据库迁移
db-migrate:
	@echo "📊 创建数据库迁移..."
	@read -p "请输入迁移描述: " desc; \
	alembic revision --autogenerate -m "$$desc"

# 执行数据库迁移
db-upgrade:
	@echo "📊 执行数据库迁移..."
	alembic upgrade head

# 查看数据库迁移历史
db-history:
	@echo "📊 数据库迁移历史..."
	alembic history

# 清理指定文件
clean-file:
	@read -p "请输入文件路径: " file; \
	./scripts/clean_imports.sh "$$file"

# 检查指定文件
check-file:
	@read -p "请输入文件路径: " file; \
	./scripts/clean_imports.sh check "$$file"
