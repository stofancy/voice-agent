#!/bin/bash
# =============================================================================
# OpenClaw Voice - Service Manager
# =============================================================================
# 
# 完整的语音助手服务管理脚本，支持 Docker 部署和本地开发两种模式。
#
# 📚 快速开始:
#   ./start.sh              # 显示此帮助
#   ./start.sh help         # 显示详细帮助
#   ./start.sh --help       # 显示详细帮助
#   ./start.sh -h           # 显示简要帮助
#   ./start.sh --version    # 显示版本信息
#
# 🚀 常用命令:
#   本地开发：./start.sh gateway start && ./start.sh local start
#   完整部署：./start.sh docker up
#   停止所有：./start.sh stop
#
# 📖 完整文档：CONFIG_REFERENCE.md
# =============================================================================
# 
# 架构说明:
# ┌─────────────────────────────────────────────────────────────────┐
# │                      OpenClaw Voice 架构                        │
# ├─────────────────────────────────────────────────────────────────┤
# │                                                                 │
# │  ┌──────────────┐      HTTP /v1/chat/completions    ┌─────────┐│
# │  │ Voice Agent  │ ────────────────────────────────> │ Gateway ││
# │  │ (Python)     │                                   │(Docker) ││
# │  │ localhost:   │ <──────────────────────────────── │ :18789  ││
# │  │   8765(D)    │         OpenAI 兼容 API           │         ││
# │  │   8766(L)    │                                   └────┬────┘│
# │  └──────────────┘                                      │       │
# │         │                                              │       │
# │         │ WebSocket /ws                                │       │
# │         ▼                                              ▼       │
# │  ┌──────────────┐                               ┌─────────────┐│
# │  │   Browser    │                               │   Bailian   ││
# │  │  Client UI   │                               │   LLM API   ││
# │  └──────────────┘                               └─────────────┘│
# │                                                                 │
# │  模式说明：                                                      │
# │  - Docker 模式 (D): Voice + Gateway 都在 Docker 中 (生产/测试)     │
# │  - 本地模式 (L): Voice 本地运行 + Gateway Docker (开发/调试)       │
# │                                                                 │
# └─────────────────────────────────────────────────────────────────┘
#
# 版本：1.0.0
# 更新：2026-03-20
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="1.0.0"

# 颜色定义（使用 printf 确保跨平台兼容）
print_info() { printf "\033[0;34m💡 %s\033[0m\n" "$1"; }
print_success() { printf "\033[0;32m✅ %s\033[0m\n" "$1"; }
print_warning() { printf "\033[1;33m⚠️  %s\033[0m\n" "$1"; }
print_error() { printf "\033[0;31m❌ %s\033[0m\n" "$1"; }

# 显示简要帮助
show_short_help() {
    cat << EOF
🦞 OpenClaw Voice - Service Manager (v$VERSION)

用法：./start.sh [模式] [操作]

模式:
  docker      Docker 完整部署 (Gateway + Voice)
  local       本地开发模式 (需先启动 Gateway)
  gateway     仅管理 Gateway
  stop        停止所有服务

快捷命令:
  ./start.sh                    # 显示此帮助
  ./start.sh help               # 显示详细帮助
  ./start.sh --version          # 显示版本

示例:
  ./start.sh gateway start      # 启动 Gateway
  ./start.sh local start        # 启动本地 Voice
  ./start.sh docker up          # Docker 完整部署

📖 详细帮助：./start.sh help
EOF
}

# 显示详细帮助
show_help() {
    cat << EOF
🦞 OpenClaw Voice - Service Manager (v$VERSION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 完整文档：CONFIG_REFERENCE.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️  架构说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──────────────┐                    ┌─────────────┐
  │ Voice Agent  │  HTTP /v1/*        │   Gateway   │
  │  (Python)    │ ─────────────────> │  (Docker)   │
  │  :8765/:8766 │  OpenAI Compatible │   :18789    │
  └──────────────┘                    └──────┬──────┘
         │                                   │
         │ WebSocket /ws                     │
         ▼                                   ▼
  ┌──────────────┐                    ┌─────────────┐
  │   Browser    │                    │   Bailian   │
  │   Client     │                    │  LLM API    │
  └──────────────┘                    └─────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 使用模式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  Docker 模式（完整部署）
   所有服务运行在 Docker 容器中，适合生产环境或完整测试。
   
   端口:
   - Gateway: 18789
   - Voice:   8765

2️⃣  本地模式（开发推荐）
   Gateway 在 Docker 中，Voice 本地运行，支持代码热重载。
   
   端口:
   - Gateway: 18789 (Docker)
   - Voice:   8766 (本地，避免与 Docker 冲突)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 命令参考
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Docker 模式:
  ./start.sh docker up          # 启动所有 Docker 服务
  ./start.sh docker down        # 停止所有 Docker 服务
  ./start.sh docker restart     # 重启所有 Docker 服务
  ./start.sh docker status      # 查看 Docker 服务状态
  ./start.sh docker logs        # 查看所有日志
  ./start.sh docker logs voice  # 查看 Voice 日志
  ./start.sh docker logs gw     # 查看 Gateway 日志

本地模式:
  ./start.sh local start        # 启动本地 Voice Agent
  ./start.sh local stop         # 停止本地 Voice Agent
  ./start.sh local restart      # 重启本地 Voice Agent
  ./start.sh local status       # 查看本地 Voice 状态

Gateway 管理:
  ./start.sh gateway start      # 启动 Gateway (Docker)
  ./start.sh gateway stop       # 停止 Gateway
  ./start.sh gateway restart    # 重启 Gateway
  ./start.sh gateway status     # 查看 Gateway 状态

其他命令:
  ./start.sh stop               # 停止所有服务（快捷方式）
  ./start.sh help               # 显示此帮助
  ./start.sh --help, -h         # 显示帮助
  ./start.sh --version, -v      # 显示版本

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 常用工作流
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌱 本地开发（推荐）:
  $ ./start.sh gateway start    # 1. 启动 Gateway
  $ ./start.sh local start      # 2. 启动本地 Voice
  $ ./start.sh local stop       # 3. 停止 Voice
  $ ./start.sh stop             # 4. 停止所有

📦 完整部署:
  $ ./start.sh docker up        # 一键启动所有
  $ ./start.sh docker down      # 一键停止所有

🔍 查看状态:
  $ ./start.sh gateway status   # Gateway 状态
  $ ./start.sh local status     # 本地 Voice 状态
  $ ./start.sh docker status    # Docker 服务状态

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️  配置文件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  .env                          # 环境变量配置
  docker-compose.yml            # Docker 配置
  gateway-config/openclaw.json  # Gateway 配置

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐛 故障排查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 端口被占用:
   $ lsof -i :8765
   $ lsof -i :8766
   $ lsof -i :18789

2. 查看日志:
   $ ./start.sh docker logs
   $ tail -f .voice.log

3. 重置所有服务:
   $ ./start.sh stop
   $ ./start.sh docker up

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 完整文档：CONFIG_REFERENCE.md
EOF
}

# 显示版本
show_version() {
    echo "OpenClaw Voice Service Manager v$VERSION"
    echo "Updated: 2026-03-20"
}

# 检查 Docker
check_docker() {
    if ! docker info &>/dev/null; then
        print_error "Docker 未运行，请先启动 Docker"
        exit 1
    fi
    
    if docker compose version &>/dev/null; then
        COMPOSE_CMD="docker compose"
    elif docker-compose version &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        print_error "未找到 Docker Compose"
        exit 1
    fi
}

# 检查 .env 文件
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env 不存在，从 .env.example 创建..."
        cp .env.example .env
        print_success ".env 已创建，请编辑配置"
    fi
}

# ==================== Docker 模式 ====================
docker_up() {
    check_docker
    check_env
    
    print_info "启动所有 Docker 服务..."
    $COMPOSE_CMD up -d --build
    
    sleep 3
    print_success "服务已启动"
    docker_status
}

docker_down() {
    check_docker
    
    print_info "停止所有 Docker 服务..."
    $COMPOSE_CMD down
    
    # 同时停止本地 Voice 进程
    local_stop 2>/dev/null || true
    
    print_success "服务已停止"
}

docker_restart() {
    check_docker
    
    print_info "重启所有 Docker 服务..."
    $COMPOSE_CMD restart
    
    print_success "服务已重启"
}

docker_status() {
    check_docker
    
    echo ""
    print_info "Docker 服务状态:"
    $COMPOSE_CMD ps
    echo ""
}

docker_logs() {
    check_docker
    local service="$1"
    
    case "$service" in
        voice) $COMPOSE_CMD logs -f openclaw-voice ;;
        gw|gateway) $COMPOSE_CMD logs -f openclaw-gateway ;;
        *) $COMPOSE_CMD logs -f ;;
    esac
}

# ==================== Gateway 模式 ====================
gateway_start() {
    check_docker
    
    print_info "启动 Gateway..."
    $COMPOSE_CMD up -d openclaw-gateway
    
    sleep 3
    
    if curl -s http://localhost:18789/ > /dev/null; then
        print_success "Gateway 已启动 (http://localhost:18789)"
    else
        print_error "Gateway 启动失败"
        $COMPOSE_CMD logs openclaw-gateway
        exit 1
    fi
}

gateway_stop() {
    check_docker
    
    print_info "停止 Gateway..."
    $COMPOSE_CMD stop openclaw-gateway
    
    print_success "Gateway 已停止"
}

gateway_restart() {
    check_docker
    
    print_info "重启 Gateway..."
    $COMPOSE_CMD restart openclaw-gateway
    
    print_success "Gateway 已重启"
}

gateway_status() {
    check_docker
    
    echo ""
    print_info "Gateway 状态:"
    $COMPOSE_CMD ps openclaw-gateway
    echo ""
    
    if curl -s http://localhost:18789/ > /dev/null; then
        print_success "Gateway 运行正常 (http://localhost:18789)"
    else
        print_warning "Gateway 未响应"
    fi
}

# ==================== 本地模式 ====================
get_pid_file() {
    echo "$SCRIPT_DIR/.voice.pid"
}

get_log_file() {
    echo "$SCRIPT_DIR/.voice.log"
}

local_start() {
    check_env
    
    # 检查是否已在运行
    PID_FILE=$(get_pid_file)
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            print_warning "Voice Agent 已在运行 (PID: $PID)"
            print_info "使用 './start.sh local restart' 重启"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    # 加载环境变量
    set -a
    source .env
    set +a
    
    print_info "启动 Voice Agent (本地模式)..."
    echo ""
    print_info "配置:"
    echo "  - Voice Port: ${OPENCLAW_PORT:-8766} (local)"
    echo "  - Gateway: http://localhost:18789 (docker)"
    echo "  - LLM Provider: ${OPENCLAW_LLM_PROVIDER:-openclaw_gateway}"
    echo "  - LLM Model: ${OPENCLAW_LLM_MODEL:-main}"
    echo "  - Gateway Token: ${OPENCLAW_LLM_API_KEY:0:16}..."
    echo ""
    
    # 检查虚拟环境
    if [ -d ".venv" ]; then
        print_info "激活虚拟环境..."
        source .venv/bin/activate
    else
        print_warning "虚拟环境不存在，使用系统 Python"
    fi
    
    # 后台启动
    LOG_FILE=$(get_log_file)
    nohup python -m uvicorn src.server.main:app --reload \
        --host 0.0.0.0 \
        --port ${OPENCLAW_PORT:-8766} \
        > "$LOG_FILE" 2>&1 &
    
    echo $! > "$PID_FILE"
    
    sleep 3
    
    # 检查是否启动成功
    if curl -s http://localhost:${OPENCLAW_PORT:-8766}/ > /dev/null; then
        print_success "Voice Agent 已启动 (http://localhost:${OPENCLAW_PORT:-8766})"
        echo ""
        print_info "日志：tail -f $LOG_FILE"
        print_info "停止：$0 local stop"
    else
        print_error "Voice Agent 启动失败，查看日志："
        cat "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

local_stop() {
    PID_FILE=$(get_pid_file)
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "Voice Agent 未运行"
        return 0
    fi
    
    PID=$(cat "$PID_FILE")
    
    if kill -0 "$PID" 2>/dev/null; then
        print_info "停止 Voice Agent (PID: $PID)..."
        kill "$PID"
        sleep 2
        
        # 如果还在运行，强制停止
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID"
        fi
        
        rm -f "$PID_FILE"
        print_success "Voice Agent 已停止"
    else
        print_warning "进程不存在，清理 PID 文件"
        rm -f "$PID_FILE"
    fi
}

local_restart() {
    local_stop
    sleep 2
    local_start
}

local_status() {
    PID_FILE=$(get_pid_file)
    
    echo ""
    print_info "Voice Agent 状态:"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            print_success "运行中 (PID: $PID)"
            
            if curl -s http://localhost:${OPENCLAW_PORT:-8766}/ > /dev/null; then
                print_success "服务正常 (http://localhost:${OPENCLAW_PORT:-8766})"
            else
                print_warning "服务未响应"
            fi
        else
            print_warning "进程不存在 (PID: $PID)"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "未运行"
    fi
    echo ""
}

# ==================== 主程序 ====================
MODE="${1:-}"
ACTION="${2:-}"

# 处理帮助和版本参数
case "$MODE" in
    --help|-h)
        show_help
        exit 0
        ;;
    --version|-v)
        show_version
        exit 0
        ;;
    help)
        show_help
        exit 0
        ;;
    "")
        show_short_help
        exit 0
        ;;
esac

case "$MODE" in
    docker)
        case "$ACTION" in
            up) docker_up ;;
            down) docker_down ;;
            restart) docker_restart ;;
            status) docker_status ;;
            logs) shift; docker_logs "$@" ;;
            *) print_error "未知操作：$ACTION"; echo "使用：$0 docker [up|down|restart|status|logs]"; exit 1 ;;
        esac
        ;;
    
    local)
        case "$ACTION" in
            start) local_start ;;
            stop) local_stop ;;
            restart) local_restart ;;
            status) local_status ;;
            *) print_error "未知操作：$ACTION"; echo "使用：$0 local [start|stop|restart|status]"; exit 1 ;;
        esac
        ;;
    
    gateway)
        case "$ACTION" in
            start) gateway_start ;;
            stop) gateway_stop ;;
            restart) gateway_restart ;;
            status) gateway_status ;;
            *) print_error "未知操作：$ACTION"; echo "使用：$0 gateway [start|stop|restart|status]"; exit 1 ;;
        esac
        ;;
    
    stop)
        # 快捷方式：停止所有服务
        local_stop 2>/dev/null || true
        check_docker && $COMPOSE_CMD down 2>/dev/null || true
        print_success "所有服务已停止"
        ;;
    
    *)
        print_error "未知模式：$MODE"
        echo ""
        show_short_help
        exit 1
        ;;
esac
