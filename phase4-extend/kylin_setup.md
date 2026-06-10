# 麒麟操作系统环境说明

## 1. 环境安装

### 1.1 下载镜像

麒麟操作系统（银河麒麟桌面/服务器版）可从官方渠道获取：
- 银河麒麟官网：https://www.kylinos.cn/
- 教育版/社区版适合学习使用

### 1.2 安装方式

| 方式 | 适用场景 | 说明 |
|------|---------|------|
| **虚拟机** | Windows/Mac 学习 | 使用 VMware/VirtualBox 安装麒麟 ISO |
| **双系统** | 实体机体验 | 与 Windows 共存 |
| **WSL** | Windows 轻量替代 | 用于部分命令行操作的模拟 |
| **Docker** | 服务器部署测试 | `docker pull kylin` |

### 1.3 虚拟机安装步骤 (VMware)

1. 下载银河麒麟 ISO 镜像
2. VMware 新建虚拟机 → 选择 ISO
3. 分配 4GB+ 内存、40GB+ 磁盘
4. 启动安装，选择中文语言
5. 创建用户账户
6. 安装 VMware Tools（增强兼容性）

## 2. 基础环境配置

### 2.1 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 2.2 安装 Python

```bash
# 麒麟系统通常预装 Python 3
python3 --version

# 如未安装
sudo apt install python3 python3-pip -y
```

### 2.3 安装 Git

```bash
sudo apt install git -y
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### 2.4 安装 SQLite

```bash
# 麒麟系统通常预装 sqlite3
sqlite3 --version

# 如未安装
sudo apt install sqlite3 -y
```

## 3. 本阶段使用的命令

### 3.1 文件操作

```bash
# 查看目录
ls -la

# 查看磁盘空间
df -h

# 查看系统信息
uname -a
cat /etc/os-release
```

### 3.2 进程管理

```bash
# 查看进程
ps aux | grep python

# 查看端口占用
netstat -tlnp
```

### 3.3 权限管理

```bash
# 修改文件权限
chmod +x setup_db.py

# 查看当前用户
whoami
```

## 4. 排查常见问题

| 问题 | 解决方式 |
|------|---------|
| pip 安装报权限错误 | `pip install --user` 或使用虚拟环境 |
| Python 版本过低 | `sudo apt install python3.12` |
| 中文显示乱码 | `export LANG=zh_CN.UTF-8` |
| 无法访问外网 | 检查网络代理设置，配置 DNS |
| 磁盘空间不足 | `sudo apt autoremove` 清理旧包 |

## 5. 环境截图要求

提交时需包含：
- 麒麟系统桌面截图
- 终端中 `uname -a` 输出截图
- Python 版本截图
- SQLite 版本截图

> 注：受限于当前开发环境为 Windows，实际麒麟环境截图将在部署时补充。
