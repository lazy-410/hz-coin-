# NUEDC 自动签到工具

一个用于自动登录 NUEDC 培训网站并完成每日签到以获取 Hz 币的 Python 工具，包含命令行和网页界面两种使用方式，并支持通过 GitHub Actions 实现自动签到。

## 功能特点

- ✅ 自动通过 myTI SSO 单点登录系统登录 NUEDC 网站
- ✅ 自动执行每日签到操作获取 Hz 币
- ✅ 支持 cookie 持久化，避免重复登录
- ✅ 提供命令行和网页界面两种使用方式
- ✅ 显示连续签到天数和赫兹币余额
- ✅ 详细的错误处理和日志输出
- ✅ 支持多账号管理（网页版）
- ✅ 简洁美观的用户界面
- ✅ 响应式设计，适配不同设备
- ✅ 通过 GitHub Actions 实现自动签到

## 项目结构

```
├── app.py              # Flask 主应用（网页版）
├── signin.py           # 核心签到逻辑
├── nuedc_hz_signin.py  # 命令行版本
├── auto_signin_multi.py # 多账号自动签到脚本
├── requirements.txt    # 依赖配置
├── templates/
│   └── index.html      # 网页界面模板
├── .github/
│   └── workflows/
│       ├── auto-signin.yml        # 单账号自动签到 workflow
│       └── auto-signin-multi.yml  # 多账号自动签到 workflow
├── .gitignore          # Git 忽略文件
└── README.md           # 项目说明
```

## 安装方法

### 1. 克隆项目

```bash
git clone <repository-url>
cd nuedc-signin
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方法一：网页界面（推荐）

1. **启动服务**

```bash
python app.py
```

2. **访问网页**

在浏览器中打开 `http://127.0.0.1:5000`，输入 TI 账号信息后点击"开始签到"按钮即可。

### 方法二：命令行

```bash
# 交互式输入
python nuedc_hz_signin.py

# 命令行参数
python nuedc_hz_signin.py --username "your_email@example.com" --password "your_password"

# 环境变量
NUEDC_TI_USERNAME=your_email@example.com NUEDC_TI_PASSWORD=your_password python nuedc_hz_signin.py
```

## 网页界面功能

- **快速签到**：直接输入账号密码进行签到
- **账号选择**：从下拉菜单选择已保存账号（自动填充信息）
- **账号管理**：通过模态框添加和删除账号
- **结果反馈**：实时显示签到结果、连续签到天数和赫兹币余额
- **详细日志**：可查看详细的签到过程
- **自动签到设置**：可设置每天自动签到的时间

## 命令行参数

- `--username`：TI 用户名/邮箱
- `--password`：TI 密码
- `--timeout`：HTTP 请求超时时间（默认 30 秒）
- `--cookie-file`：cookie 文件路径（默认 `.nuedc_cookies.txt`）
- `--no-cookie`：禁用 cookie 持久化
- `--verbose`：显示详细日志

## 环境变量

- `NUEDC_TI_USERNAME`：TI 用户名/邮箱
- `NUEDC_TI_PASSWORD`：TI 密码

## 自动签到配置（GitHub Actions）

### 1. 单账号配置

1. **创建 GitHub Secrets**：
   - 进入仓库 Settings → Secrets and variables → Actions
   - 点击 "New repository secret"
   - 添加以下 Secrets：
     - `NUEDC_USERNAME`：你的 TI 用户名/邮箱![alt text](image.png)
     - `NUEDC_PASSWORD`：你的 TI 密码

2. **启用 Workflow**：
   - 进入仓库 Actions 页面
   - 找到 "Auto Signin" workflow
   - 点击 "Run workflow" 测试

### 2. 多账号配置

1. **创建 GitHub Secrets**：
   - 进入仓库 Settings → Secrets and variables → Actions
   - 点击 "New repository secret"
   - 添加 `NUEDC_ACCOUNTS` Secret，值为 JSON 格式的账号列表：
     ```json
     [
       {"username": "user1@example.com", "password": "password1"},
       {"username": "user2@example.com", "password": "password2"}
     ]
     ```

2. **启用 Workflow**：
   - 进入仓库 Actions 页面
   - 找到 "Auto Signin Multi" workflow
   - 点击 "Run workflow" 测试

### 3. 自动执行时间

- 默认为每天 UTC 时间 0 点执行（北京时间 8 点）
- 可修改 `.github/workflows/` 目录下的 workflow 文件中的 cron 表达式

## 注意事项

1. **安全性**：
   - 网页版：账号信息存储在浏览器的 localStorage 中，只在本地保存
   - GitHub Actions：账号信息存储在 GitHub Secrets 中，加密存储
   - 本工具不会将账号信息上传到任何服务器

2. **网络连接**：需要网络连接以访问 NUEDC 和 TI 登录页面

3. **账号绑定**：首次使用时可能需要在浏览器中完成 myTI 账号与 NUEDC 账号的绑定

4. **页面结构**：由于 NUEDC 网站的页面结构可能会变化，获取赫兹币的功能可能需要根据网站更新进行调整

5. **依赖更新**：定期更新依赖包以确保兼容性

## 常见问题

### Q: 无法登录或获取赫兹币

**A:** 可能的原因：
- 账号密码错误
- 网络连接问题
- NUEDC 网站结构变化
- 需要完成账号绑定

请检查网络连接，确保账号密码正确，并在浏览器中尝试手动登录 NUEDC 网站完成必要的绑定操作。

### Q: 如何查看详细的签到过程

**A:** 在网页界面中勾选"显示详细日志"选项，或在命令行中使用 `--verbose` 参数。

### Q: GitHub Actions 执行失败

**A:** 可能的原因：
- Secrets 配置错误
- JSON 格式不正确
- 网络连接问题

检查 Secrets 配置，确保 JSON 格式正确，并查看 Actions 日志了解具体错误。

### Q: 分享仓库后，别人会看到我的账号信息吗

**A:** 不会。账号信息存储在 GitHub Secrets 中，只有仓库所有者和有相应权限的协作者才能访问。分享仓库时，Secrets 不会被包含在代码中。

## 技术实现

- **后端**：Python 3.7+
- **Web 框架**：Flask 3.0.0
- **网络请求**：requests 2.31.0
- **HTML 解析**：BeautifulSoup4 4.14.3
- **前端**：HTML5 + CSS3
- **自动化**：GitHub Actions

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 更新日志

### v1.0.0
- 初始版本
- 支持命令行和网页界面
- 实现自动签到和赫兹币查询功能

### v1.1.0
- 新增多账号管理功能
- 优化网页界面设计
- 改进赫兹币获取算法
- 增强错误处理和日志输出

### v1.2.0
- 全新的简洁美观用户界面
- 响应式设计，适配不同设备
- 模态框式账号管理
- 优化的账号选择和自动填充功能
- 更详细的项目文档

### v1.3.0
- 添加 GitHub Actions 自动签到功能
- 支持多账号自动签到
- 增强安全性和稳定性
- 完善项目文档
