# Skills

## install

```bash
git clone git@github.com:aqua2k1/agent-setup.git ~/.agent
```

```bash
git clone --depth=1 https://github.com/aqua2k1/pi-setup.git ~/.agent
```

## Skills

```
~/.agents/skills/
├── u/                              # disable-model-invocation: true（仅人触发）
│   ├── grill-me/        — 纯盘问
│   ├── grill-with-docs/ — 盘问 + 领域建模 + 写文档
│   ├── handoff/         — 会话交接
│   ├── caveman/         — 极简 token 节省模式
│   └── teach/            — 多会话教学
│
└── m/                              # 模型可自动触发
    ├── grilling/         — 盘问循环原语
    ├── domain-modeling/  — 术语表 + ADR 维护
    ├── codebase-design/  — 深度模块设计词汇
    ├── tdd/              — 红-绿-重构循环
    ├── code-review/      — 双轴并行审查
    └── diagnosing-bugs/  — 6 阶段调试纪律
```

## Ref

[mattpocock/skills](https://github.com/mattpocock/skills)
