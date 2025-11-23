# 推送到 GitHub 的完整指南

## 当前状态
- 远程仓库已配置：`https://github.com/oikreese/saving-advisor-system.git`
- 当前分支：`opensource-migration`

## 如果遇到 "Repository not found" 错误

### 方案 1：检查仓库是否存在
访问 https://github.com/oikreese/saving-advisor-system 确认仓库是否存在

### 方案 2：如果仓库名称不同
如果仓库名称不是 `saving-advisor-system`，更新远程 URL：

```bash
# 替换为正确的仓库名称
git remote set-url origin https://github.com/oikreese/<正确的仓库名>.git
```

### 方案 3：配置 GitHub 认证（私有仓库需要）

#### 使用 Personal Access Token (推荐)

1. 生成 Token：
   - 访问：https://github.com/settings/tokens
   - 点击 "Generate new token" > "Generate new token (classic)"
   - 选择权限：至少勾选 `repo` (完整仓库访问权限)
   - 生成并复制 token

2. 使用 Token 推送：
```bash
# 方法 A：在 URL 中包含 token（一次性）
git remote set-url origin https://<你的token>@github.com/oikreese/saving-advisor-system.git
git push -u origin opensource-migration

# 方法 B：使用 Git Credential Helper（推荐）
git config --global credential.helper osxkeychain  # macOS
# 然后正常推送，会提示输入用户名和密码（密码处输入 token）
git push -u origin opensource-migration
```

#### 使用 SSH（如果已配置 SSH key）

```bash
# 切换到 SSH URL
git remote set-url origin git@github.com:oikreese/saving-advisor-system.git

# 推送
git push -u origin opensource-migration
```

## 推送命令

### 如果远程仓库是空的：

```bash
# 推送当前分支
git push -u origin opensource-migration

# 或者推送到 main 分支
git checkout main
git merge opensource-migration
git push -u origin main
```

### 如果远程仓库已有内容：

#### 选项 1：合并后推送（推荐）
```bash
# 先拉取并合并
git pull origin main --allow-unrelated-histories

# 解决可能的冲突后
git push -u origin opensource-migration
```

#### 选项 2：强制推送（会覆盖远程，谨慎使用）
```bash
git push -u origin opensource-migration --force
```

## 验证推送成功

```bash
# 查看远程分支
git branch -r

# 查看远程信息
git remote show origin
```

## 常见问题

### Q: 提示需要认证
A: 私有仓库需要配置 Personal Access Token 或 SSH key

### Q: 提示仓库不存在
A: 检查仓库名称是否正确，或确认仓库是否已创建

### Q: 推送时提示冲突
A: 使用 `git pull --allow-unrelated-histories` 先合并，或使用 `--force` 强制推送（谨慎）

## 下一步

推送成功后：
1. 在 GitHub 上检查文件是否都上传了
2. 确认 `.env` 文件不在仓库中（应该在 .gitignore 中）
3. 设置仓库描述和主题标签
4. 可选：创建 Release 版本

