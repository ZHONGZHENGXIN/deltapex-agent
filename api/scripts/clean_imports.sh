#!/bin/bash

# 清理 API 代码中未使用的 import 脚本
# 
# 使用方法:
# ./scripts/clean_imports.sh                    # 清理整个 app 目录
# ./scripts/clean_imports.sh check             # 检查模式，不修改文件
# ./scripts/clean_imports.sh app/routers/      # 清理指定目录
# ./scripts/clean_imports.sh app/main.py       # 清理指定文件

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查工具是否安装
check_tool() {
    local tool=$1
    if ! command -v $tool &> /dev/null; then
        print_error "$tool 未安装，请先运行: uv sync"
        exit 1
    fi
}

# 运行命令并处理结果
run_command() {
    local cmd="$1"
    local description="$2"
    
    print_info "$description"
    echo "执行: $cmd"
    
    if eval $cmd; then
        print_success "$description 完成"
        return 0
    else
        print_error "$description 失败"
        return 1
    fi
}

# 主函数
main() {
    local target_path="app"
    local check_mode=false
    
    # 解析参数
    if [[ $# -gt 0 ]]; then
        if [[ "$1" == "check" ]]; then
            check_mode=true
            if [[ $# -gt 1 ]]; then
                target_path="$2"
            fi
        else
            target_path="$1"
        fi
    fi
    
    # 检查目标路径是否存在
    if [[ ! -e "$target_path" ]]; then
        print_error "目标路径不存在: $target_path"
        exit 1
    fi
    
    print_info "开始处理: $target_path"
    print_info "模式: $([ "$check_mode" = true ] && echo "检查" || echo "修复")"
    echo "=================================================="
    
    # 检查必要工具
    check_tool "autoflake"
    check_tool "isort" 
    check_tool "black"
    
    local success=true
    
    # 步骤 1: 清理未使用的 import
    echo
    print_info "1️⃣ 清理未使用的 import..."
    local autoflake_cmd="autoflake --remove-all-unused-imports --remove-unused-variables --ignore-init-module-imports"
    
    if [[ "$check_mode" = true ]]; then
        autoflake_cmd="$autoflake_cmd --check"
    else
        autoflake_cmd="$autoflake_cmd --in-place"
    fi
    
    if [[ -d "$target_path" ]]; then
        autoflake_cmd="$autoflake_cmd --recursive $target_path"
    else
        autoflake_cmd="$autoflake_cmd $target_path"
    fi
    
    if ! run_command "$autoflake_cmd" "清理未使用的 import"; then
        success=false
    fi
    
    # 步骤 2: 整理 import 顺序
    echo
    print_info "2️⃣ 整理 import 顺序..."
    local isort_cmd="isort --profile black --line-length 128"
    
    if [[ "$check_mode" = true ]]; then
        isort_cmd="$isort_cmd --check-only"
    fi
    
    isort_cmd="$isort_cmd $target_path"
    
    if ! run_command "$isort_cmd" "整理 import 顺序"; then
        success=false
    fi
    
    # 步骤 3: 格式化代码
    echo
    print_info "3️⃣ 格式化代码..."
    local black_cmd="black --line-length 128"
    
    if [[ "$check_mode" = true ]]; then
        black_cmd="$black_cmd --check"
    fi
    
    black_cmd="$black_cmd $target_path"
    
    if ! run_command "$black_cmd" "格式化代码"; then
        success=false
    fi
    
    # 输出结果
    echo
    echo "=================================================="
    if [[ "$success" = true ]]; then
        if [[ "$check_mode" = true ]]; then
            print_success "检查完成，代码格式良好"
        else
            print_success "清理完成，所有文件已优化"
        fi
    else
        print_error "处理过程中出现错误"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "清理 API 代码中未使用的 import"
    echo
    echo "使用方法:"
    echo "  $0                    # 清理整个 app 目录"
    echo "  $0 check             # 检查模式，不修改文件"
    echo "  $0 app/routers/      # 清理指定目录"
    echo "  $0 app/main.py       # 清理指定文件"
    echo "  $0 check app/main.py # 检查指定文件"
    echo
    echo "功能:"
    echo "  - 移除未使用的 import"
    echo "  - 整理 import 顺序"
    echo "  - 格式化代码"
    echo
}

# 检查参数
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# 执行主函数
main "$@"
