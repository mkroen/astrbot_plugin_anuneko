# AstrBot AnuNeko 插件

基于 [anuneko.com](https://anuneko.com) 的 AI 对话插件。

## 功能

- 🐱 支持两种 AI 模式：橘猫 / 黑猫
- 💬 流式对话，支持上下文
- 🔄 每个用户独立会话管理
- 🌐 支持 HTTP 代理

## 指令

| 指令 | 说明 | 示例 |
|------|------|------|
| `/neko <内容>` | 与 AI 对话 | `/neko 你好` |
| `/neko切换模式 <1/2>` | 切换 AI 模式 | `/neko切换模式 1` (橘猫) 或 `/neko切换模式 2` (黑猫) |
| `/neko新会话` | 创建新的对话会话 | `/neko新会话` |

## 配置

在 AstrBot 管理面板中配置：

| 配置项 | 说明 | 必填 |
|--------|------|------|
| `token` | AnuNeko 的 x-token | ✅ |
| `proxy` | HTTP 代理地址（如 `http://127.0.0.1:7890`） | ❌ |

### 获取 Token

1. 访问 [anuneko.com](https://anuneko.com) 并登录
2. 打开浏览器开发者工具 (F12)
3. 在 Network 标签页中找到任意 API 请求
4. 复制请求头中的 `x-token` 值

## Session 管理

- **群聊**：整个群共享一个会话，所有群成员共用同一个对话上下文
- **私聊**：每个用户私聊拥有独立会话
- 会话在插件重启后会重置
- 使用 `/新会话` 可手动重置当前会话

## 安装

将 `astrbot_plugin_anuneko` 文件夹放入 AstrBot 的插件目录即可。

## 致谢

- [AnuNeko](https://anuneko.com) - AI 服务提供方
- [afoim/AnuNeko_NoneBot2_Plugins](https://github.com/afoim/AnuNeko_NoneBot2_Plugins) - 原始 NoneBot2 插件，本项目基于此迁移
- [AstrBot](https://github.com/Soulter/AstrBot) - 机器人框架

## 免责声明

本插件仅为第三方前端，与 anuneko.com 官方无关。请遵守相关服务条款。
