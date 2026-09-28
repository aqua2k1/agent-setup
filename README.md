# Agent Skills（skillshare）

本仓库只同步 **配置与来源清单**，以及没有上游来源的自建 skill：

- `config.yaml`：skillshare 的全局配置，含源目录和 universal 目标；`setup.sh` 自动接入默认配置路径。
- `source/.metadata.json`：skillshare 全局模式的远程 skill 来源清单，由 `skillshare install` 维护。
- `source/comfyui-imagegen/`：自建 skill，实体文件由 Git 同步。
- `source/.skillignore`：嵌套的 `SKILL.md` 不部署为独立 skill。
- `source/` 下其他技能目录：远端下载缓存，由 Git 忽略，可在各设备重新安装。
- `skills/`：skillshare 创建的 universal 目标链接，由 Git 忽略。

## 新设备

先安装 [skillshare](https://skillshare.runkids.cc/docs/)，然后：

```bash
git clone git@github.com:aqua2k1/agent-setup.git ~/.agents
~/.agents/setup.sh  # 接入配置、安装来源清单中的 skill 并同步目标
```

`setup.sh` 可重复运行；如果默认配置位置已有不同文件，它会报错而不会覆盖。无需编辑 `~/.env` 或配置任何 shell 的环境变量。Pi 等读取 `~/.agents/skills/` 的工具可以直接使用；如需某工具的专属目录，用 `skillshare init --discover` 添加目标。修改目标配置会写入共享的 `config.yaml`，跨设备使用不同目标时要留意配置差异。

## 日常使用

```bash
skillshare install owner/repo/path/to/skill  # 安装子目录中的单个 skill，并记录来源
skillshare update --all                     # 更新有来源记录的 skill
skillshare sync                             # 增删 skill 后同步本机链接
skillshare list                             # TUI 中按 M 设置仅手动调用
skillshare push -m "Update skills"          # 提交并推送配置/清单/自建 skill
skillshare pull                             # 拉取仓库改动
skillshare install && skillshare sync       # 安装本机缺失的远程 skill 并更新链接
```

新增自建 skill 时，记得在 `.gitignore` 为它加入例外；远程 skill 的本地修改（包括按 M 修改 `SKILL.md`）**不会**通过此清单方案跨设备同步。如需保存这些修改，请改为自建 skill 或单独管理补丁。历史 `npx skills` 锁文件和同步脚本已移除。

**现有 GitHub 仓库是公开的；推送前请检查 `config.yaml`、`source/.metadata.json` 和自建 skill 内容。**
