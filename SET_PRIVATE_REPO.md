# 将GitHub仓库设置为私有

## 方法1: 通过GitHub网页界面（推荐）

1. 访问您的仓库: https://github.com/bryanzk/CallTraceSniffer
2. 点击仓库页面右上角的 **Settings**（设置）
3. 向下滚动到 **Danger Zone**（危险区域）
4. 点击 **Change visibility**（更改可见性）
5. 选择 **Make private**（设为私有）
6. 输入仓库名称确认: `bryanzk/CallTraceSniffer`
7. 点击 **I understand, change repository visibility**

## 方法2: 使用GitHub CLI（如果已安装）

```bash
# 安装GitHub CLI（如果还没有）
# macOS: brew install gh
# Linux: 参考 https://cli.github.com/manual/installation

# 登录GitHub
gh auth login

# 将仓库设为私有
gh repo edit bryanzk/CallTraceSniffer --visibility private
```

## 方法3: 使用GitHub API

```bash
# 需要Personal Access Token（需要repo权限）
curl -X PATCH \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/bryanzk/CallTraceSniffer \
  -d '{"private":true}'
```

## 验证设置

设置完成后，访问 https://github.com/bryanzk/CallTraceSniffer
- 如果看到登录提示或404，说明已成功设为私有
- 只有您和您授权的协作者可以访问

## 添加协作者（可选）

如果需要允许特定人员访问：

1. 进入仓库 Settings → Collaborators
2. 点击 **Add people**
3. 输入GitHub用户名或邮箱
4. 选择权限级别（Read/Write/Admin）
5. 发送邀请

## 注意事项

⚠️ **重要提示**:
- 设为私有后，仓库将不再公开可见
- 只有您和您添加的协作者可以访问
- 私有仓库在GitHub免费账户中有限制（但通常足够使用）
- 如果使用GitHub Actions，私有仓库可能需要付费计划

## 恢复为公开仓库

如果需要改回公开：

1. Settings → Danger Zone
2. Change visibility → Make public
3. 确认操作

