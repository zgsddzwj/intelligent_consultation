# 智能问诊项目微调管线（Qwen2.5-7B-Instruct + QLoRA + LLaMA-Factory）

用本项目的知识资产（知识图谱种子、两篇诊疗指南、意图模板库）与线上 Prompt 人设，蒸馏 DeepSeek-V3 构造混合多任务 SFT 数据，微调一个 7B 小模型替换线上对话模型。

**混合任务构成（约 3000 条）**

| 任务 | 数量 | 说明 |
|---|---|---|
| 问诊对话（单轮） | 1200 | 使用流式生产接口实际采用的“医疗咨询”system/user Prompt + 带编号的 RAG 上下文 |
| 问诊对话（多轮） | 600 | 3 轮追问对话，教师一次生成，含追问/复查/生活管理 |
| 医疗 NER | 800 | 标签程序化构造（零噪声），对齐 `entity_recognizer` 的 JSON 契约 |
| 指南摘要/患者教育 | 300 | 两篇指南分章节的三种任务 |
| 高风险安全处置 | 20 | 不调用教师模型的固定安全样本；覆盖急症、严重过敏、误服药、自伤风险等，须经医疗/安全负责人复核 |

**关键设计**：问诊训练样本使用 `/chat/stream` 实际使用的 `MEDICAL_CONSULTATION_SYSTEM` 与 `format_medical_prompt` 形态。RAG 上下文统一使用 `[来源N: 标题]`，回答只能引用上下文中存在的 `[来源N]`；API `sources` 也返回对应的 `citation_id`。

---

## 步骤 0：环境准备

GPU 要求：**本地无显卡也没关系**——只有训练/评测两步需要 GPU（约 2~3 小时），推荐租 AutoDL RTX 4090（约 ¥5~15 全包），一步步操作见 **[deploy/云端训练指南.md](deploy/云端训练指南.md)**；本地有 24GB 卡则按本页命令直接跑。QLoRA 7B 约占 10~12GB 显存。训练环境与 backend 隔离：

```bash
conda create -n finetune python=3.11 -y
conda activate finetune

# LlamaFactory：固定版本，避免 main 分支参数变更导致训练不可复现
git clone --depth 1 --branch v0.9.5 https://github.com/hiyouga/LlamaFactory.git
cd LLaMA-Factory
pip install -e .
pip install -r requirements/metrics.txt

# 本目录数据/评测脚本依赖
cd ../finetune
pip install -r requirements.txt
```

前置检查：`backend/.env` 中 `SILICONFLOW_API_KEY` 已配置（数据合成复用它，不另配 Key）。

## 步骤 1：生成 SFT 数据（教师模型 = DeepSeek-V3，预估花费 ¥20~50）

```bash
cd finetune

# 先小样试跑（约 65 次 API 调用，<¥1），产物在 data/samples/，人工抽查
python data_gen/gen_consultation_sft.py --dry-run
python data_gen/gen_ner_sft.py --dry-run
python data_gen/gen_summary_sft.py --dry-run
python data_gen/gen_safety_sft.py --dry-run
python data_gen/validate_data.py --dir samples

# 抽查通过后全量
python data_gen/gen_consultation_sft.py                # 1200 单轮 + 600 多轮
python data_gen/gen_ner_sft.py                         # 800 条
python data_gen/gen_summary_sft.py                     # 300 条
python data_gen/gen_safety_sft.py                      # 20 条固定高风险处置样本，无 API 费用
python data_gen/gen_eval_set.py                        # 评测集（不调 API，免费）
python data_gen/validate_data.py --merge               # 校验并合并 → data/sft_train.jsonl
```

`--fix` 可去重；校验报告含任务分布、平均长度、来源编号闭环、Prompt 同步检查。Prompt 不同步、引用不存在或安全样本缺少升级处置会阻断合并。

### 可选：用火山引擎 CodingPlan 当教师模型（免按量付费）

数据合成的教师模型默认走项目现配的硅基流动（按量付费，全量约 ¥20~50）。如果你订阅了火山引擎 CodingPlan（方舟 Ark 接口同样 OpenAI 兼容），可改用它，零额外费用：

1. 在火山引擎控制台 CodingPlan 页面找到「第三方工具接入 / API 接入信息」，拿到 **Base URL**、**API Key** 和可用**模型名**（选通用旗舰模型更好，如豆包 Seed 1.6 / DeepSeek-V3 系列；代码专用模型也可以用，但本任务是中文医疗对话，通用模型通常更合适）
2. 复制 `finetune/.env.example` 为 `finetune/.env`，填入：
   ```ini
   TEACHER_BASE_URL=<你的Base URL>
   TEACHER_API_KEY=<你的API Key>
   TEACHER_MODEL=<模型名>
   ```
3. 生成命令完全不变（解析优先级：CLI 参数 > `finetune/.env` 的 `TEACHER_*` > `backend/.env` 的 `SILICONFLOW_*`）

注意：
- CodingPlan 配额按编码工具场景设计，批量生成约 500 万 token 请留意套餐配额与限流；如遇 429 可降并发 `--workers 2`
- 配额中断**直接重跑即可**：`--n-*` 是目标总量，脚本只补齐缺口；已达目标时不会再调用教师模型
- 使用前请确认你的套餐条款允许在自研脚本中调用该端点

## 步骤 2：训练（约 1~1.5 小时 / RTX 4090）

> **本地无显卡 → 走云端**：先 `python deploy/pack_for_cloud.py` 打包，然后全程按 **[deploy/云端训练指南.md](deploy/云端训练指南.md)** 操作（租卡 → 上传 → 训练 → 云端评测 → 量化 GGUF → 下载 4.7GB → 释放实例），下面的本地命令在云端一字不改。

```bash
# 首次运行自动从 ModelScope 下载 Qwen2.5-7B-Instruct（约 15GB）
llamafactory-cli train configs/qwen2.5-7b-qlora-sft.yaml

# 监控（可选）
tensorboard --logdir saves/qwen2.5-7b-qlora-sft
```

- 显存不够 / bitsandbytes 在 Windows 报错：注释 YAML 中 `quantization_bit: 4`（纯 bf16 LoRA，24GB 够用）
- 训练中断时，显式从最近 checkpoint 继续，例如：`llamafactory-cli train configs/qwen2.5-7b-qlora-sft.yaml resume_from_checkpoint=saves/qwen2.5-7b-qlora-sft/checkpoint-100`
- 想快速跑通流程：把 `model_name_or_path` 换成 `Qwen/Qwen2.5-1.5B-Instruct`（十几分钟出结果）

## 步骤 3：评测（基座 vs 微调对比）

先起两个服务（任意 OpenAI 兼容方式），再分别评测：

```bash
# 例：vLLM 起基座对照
vllm serve Qwen/Qwen2.5-7B-Instruct --served-model-name base --port 8001
python eval/run_eval.py --base-url http://localhost:8001/v1 --model base --api-key empty

# 合并后测微调模型（见步骤 4）
python eval/run_eval.py --base-url http://localhost:11434/v1 --model qwen2.5-7b-medical-sft --api-key ollama
```

达标线：RAG 事实覆盖率 ≥80%、高风险行为规范 100%、NER F1 ≥85%。报告还会输出无 RAG 事实覆盖率（仅诊断模型记忆，不作为上线门槛）。任何一项未达标、出现严重安全失败，或未经医疗人员抽样审核，均不得切换生产流量。

## 步骤 4：合并部署 → 接入项目

```bash
llamafactory-cli export configs/merge_export.yaml   # 合并 LoRA → models/qwen2.5-7b-medical-sft/
```

之后转 GGUF + ollama 部署（Windows 推荐）或 WSL2 + vLLM，以及 `.env` 切换三行配置，见 **[deploy/接入说明.md](deploy/接入说明.md)**。

## 步骤 5：端到端验证

```bash
cd backend && uv run uvicorn app.main:app --reload
```

前端发起问诊对话，检查：`[来源N]` 与 `sources[].citation_id` 一一对应、免责声明只出现一次、高风险场景就医提示、流式输出正常。图片分析与嵌入模型走独立配置不受影响。

---

## 目录说明

```
finetune/
├── README.md                 本文件
├── requirements.txt          数据/评测脚本依赖
├── data_gen/
│   ├── kg_seed.py            项目知识资产副本（KG种子/指南/模板/Prompt），生成数据的事实锚点
│   ├── common.py             共享工具：问句池、KG上下文构建、ShareGPT格式
│   ├── llm_client.py         硅基流动教师模型客户端（复用 backend/.env Key）
│   ├── gen_consultation_sft.py   问诊对话数据（单轮+多轮）
│   ├── gen_ner_sft.py            NER 数据（程序化标签+教师改写）
│   ├── gen_summary_sft.py        指南摘要/患者教育
│   ├── gen_safety_sft.py         固定高风险安全处置样本（无教师调用）
│   ├── gen_eval_set.py           评测集（免费，程序化构造）
│   └── validate_data.py          校验 + 合并训练集
├── data/                     数据产物（sft_train.jsonl、分任务文件、eval/）
├── configs/
│   ├── dataset_info.json     LLaMA-Factory 数据集注册
│   ├── qwen2.5-7b-qlora-sft.yaml  训练配置
│   └── merge_export.yaml     LoRA 合并配置
├── eval/run_eval.py          三套评测 → Markdown 报告
├── deploy/                   Modelfile + 项目接入说明
└── saves/                    训练产物（LoRA 权重、日志）
```

## 注意事项

- **重新生成条件**：若修改 `backend/app/prompts/consultation.py`、来源上下文格式或 `kg_seed.py`，必须重新生成全部数据；校验会在 Prompt 不同步时失败，但不会替你修复已生成的旧数据
- **知识范围**：训练语料锚定项目 KG 的 13 种疾病与两篇指南，超纲问题模型应答"暂无明确指南支持"——这是训练目标而非缺陷
- **数据规模**：约 2920 条对 7B 仍是小数据，靠 LoRA（rank 16）+ 3 epochs 控制过拟合；以固定种子、验证损失与外部保留评测共同决定是否采用最佳 checkpoint
- **医疗审核**：KG 种子、指南摘录、固定安全样本和教师生成回答均不是临床批准材料；训练前后应由具备相应资质的人员审核事实、禁忌、分诊和引用正确性
- **成本控制**：全量数据生成约 500 万 token（¥20~50 量级）；`--dry-run` 先验证管线
- **进阶方向**：从 PostgreSQL `consultations` 表导出真实问诊对话脱敏后做第二轮 SFT；或用 `KTO`/`DPO` 做偏好对齐
