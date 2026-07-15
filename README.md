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
├── u/ (7)                              # disable-model-invocation: true
│   ├── grill-me/           — 纯盘问
│   ├── grill-with-docs/    — 盘问 + 领域建模 + 写文档
│   ├── to-spec/            — 对话 → .scratch/<slug>/spec.md
│   ├── to-tickets/         — spec → .scratch/<slug>/issues/NN-slug.md
│   ├── implement/          — 读 ticket → /tdd → /code-review → commit
│   ├── caveman/            — 极简 token 节省模式
│   └── teach/              — 多会话教学
│
└── m/ (7)                              # 模型可自动触发
    ├── grilling/           — 盘问循环原语
    ├── domain-modeling/    — 术语表 + ADR 维护
    ├── codebase-design/    — 深度模块设计词汇
    ├── tdd/                — 红-绿-重构循环
    ├── code-review/        — 双轴并行审查
    ├── diagnosing-bugs/    — 6 阶段调试纪律
    └── prototype/          — 一次性原型（逻辑/UI）
```

## Workflow

```
/grill-with-docs              ← 盘清楚 + 建术语
    │
    ├── /to-spec              ← .scratch/<slug>/spec.md
    ├── /to-tickets           ← .scratch/<slug>/issues/NN-slug.md
    │
    └── 每个 ticket：
        新会话 → /implement ticket → commit
        （文件桥接，不 fork）
```

## Ref

[mattpocock/skills](https://github.com/mattpocock/skills)
