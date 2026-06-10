# D05 Git 协作笔记

## PR 流程记录

1. **Fork 仓库** → 从教师仓库 fork 到个人账号
2. **Clone 到本地** → `git clone <fork-url>`
3. **创建 feature 分支** → `git checkout -b feature/clean-d4`
4. **提交清洗模块** → `git add .` → `git commit -m "feat: add D4 consolidation module"`
5. **Push 到远程** → `git push origin feature/clean-d4`
6. **创建 Pull Request** → 在 Gitee/GitHub 上发起 PR，描述改动
7. **Code Review** → 教师/同伴审查
8. **Merge** → 合并到主分支

## 遇到问题与解决

- 冲突解决：手动编辑冲突标记 (<<<<<<<, =======, >>>>>>>)，保留双方有用改动
- `.gitignore` 遗漏：补充忽略 `__pycache__/`、`.env`、`*.db`

## 学到的 Git 命令

| 命令 | 作用 |
|------|------|
| `git init` | 初始化仓库 |
| `git branch <name>` | 创建分支 |
| `git checkout <name>` | 切换分支 |
| `git merge <branch>` | 合并分支 |
| `git push` | 推送到远程 |
| `git pull` | 拉取并合并 |
