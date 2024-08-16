#!/bin/bash

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null
then
    echo "Python is not installed or not in the PATH. Please install Python and try again."
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 构建完整的 Python 脚本路径
PYTHON_SCRIPT="${SCRIPT_DIR}/bren.py"

# 检查 Python 脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# 将所有参数传递给 Python 脚本
python3 "$PYTHON_SCRIPT" "$@"

# 检查 Python 脚本的返回值
if [ $? -ne 0 ]; then
    echo "An error occurred while running the Python script."
    exit $?
fi