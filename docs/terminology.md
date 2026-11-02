# 术语定义表（Terminology / Operational Definitions）

> 本表给出 findings 清单与 oracle 实验中所有概念的**操作化定义**(怎么测的),供论文
> Definitions 节 / 附录直接引用。每条:**中文(英文)** — 定义 +(操作化/代码依据)。

---

## A. 三个核心二分（全文骨架）

**接地（grounding）** — agent 的内部信念与环境真实状态之间的对齐;源自认知科学/AI 的 symbol grounding。在本文语境:agent 对"环境处于什么状态、任务要求什么、命令产生了什么结果"的理解,是否锚定在它实际观察到的证据上。

**接地缺失（grounding failure / ungrounded）** — 信念脱离环境真实状态:agent 基于未验证假设、误读输出或缺失信息行动,而不用环境证据校准。**T0 主线**:失败发生(认知错误)、成败分野(验证纪律)、失败昂贵化(锁死后停止接地)、失败难检测(监视器缺规格参照)四层的共同底层机制。

**认知性失败（epistemic failure）** — 失败源于 agent 对信息的获取/解释/注意方式出错:它有、或本可获得正确信息,但**处理错了**。操作化:trigger_mechanism ∈ {false_premise, misread_output, ignored_signal, spec_neglect, premature_action}(占 57.9%)。

**能力性失败（competence failure）** — 失败源于 agent **根本不具备**所需的知识或实现能力,而非处理方式错。操作化:trigger_mechanism ∈ {knowledge_gap, capability_limit}(占 32.8%)。

---

## B. 时间点几何（RQ1 的核心框架）

**步（step）** — agent 的一个回合(一段推理 + 一个动作),1-indexed。

**m** — 轨迹总步数(trajectory length)。

**t_err（犯错点）** — 最早一步,agent 做出决定性错误(采纳错误信念或错误动作),即使当时看似仍可挽回。中位 7。

**t_commit（锁死点）** — 最早一步,在此之后、给定 agent 的**实际后续行为**,失败结果已被锁定(agent 此后不再有意义地重新审视该决定)。中位 12。描述性判断,非反事实。

**t_surface（暴露点）** — 最早一步出现**可观察的失败信号**(报错、失败测试、矛盾输出);若运行结束前无信号则为 null(=静默)。

**犯错–锁死窗口 / 承诺滞后（commitment lag）** — `t_commit − t_err`,从犯错到锁死之间的可干预步数。lag≥1 占 60.9%、lag≥3 占 43.9%。

**锁死风险率（hazard）** — 第 t 步的条件锁死率 = (在第 t 步锁死的轨迹数)/(在第 t 步仍存活、即 t_commit≥t 的轨迹数)。峰值 0.084 在第 13 步。

**不变式** — `1 ≤ t_err ≤ t_commit ≤ m`;`t_surface ∈ [t_err, m]` 或 null。

---

## C. 触发机制（trigger_mechanism，在 t_err 那一刻，9 类）

**认知组（epistemic，57.9%）**
- **false_premise（错误前提，30.7%）** — 基于关于环境/任务/状态的、未验证的错误假设行动。
- **spec_neglect（规格忽视，14.9%）** — 从未读/遗忘/丢弃了一条明确的任务要求。
- **misread_output（误读输出，4.4%）** — 误解了它确实读到的报错或命令输出。
- **ignored_signal（无视信号，4.1%）** — 看见明确的反证仍照样推进。
- **premature_action（过早行动，3.7%）** — 在最起码的探索/验证之前就提交构建/运行。

**能力组（competence，32.8%）**
- **knowledge_gap（知识缺口，24.0%）** — 缺少该步所需的领域/工具/API 知识(87% 为 model-layer;"查证也需能力理解"的硬核,非"该查未查")。
- **capability_limit（能力上限，8.8%）** — 计划正确,但生成/实现质量不行。

**环境/其他（9.4%）**
- **environment_obstacle_mishandled（环境障碍误处理）** — 存在真实环境阻碍,agent 处理方式错误。
- **other** — 不属以上,需填 trigger_mechanism_other。

---

## D. 行为编码（action codes，逐步分段覆盖 1..m）

| 码 | 中文 | 含义 |
|---|---|---|
| **E** | 探索/读取 | explore/read:查看文件、环境、文档 |
| **P** | 纯规划 | pure planning:只思考不动作 |
| **W** | 写/改 | write/edit:写或修改代码/文件 |
| **X** | 执行/运行 | execute/run:跑命令/程序 |
| **V** | 验证/测试 | verify/test:检验结果是否正确 |
| **C** | 完成宣称 | completion claim:声称任务已完成 |
| **R** | 恢复 recover | 重试一个失败过的步骤(re-attempt a failed step;原始标注 prompt 用词 retry) |
| **O** | 其他 | other |

`action_segments` = 连续 `[start, end, code]` 段,无缝覆盖 1..m。

---

## E. 验证（verification，F4/F9/F12 核心）

**验证纪律（verification discipline）** — agent 在做出不可逆决定/宣称前,是否先检验结果正确性。本文成败的最强分水岭。

**验证前置率（fail 侧）** — `verification_ever 且 first_relevant_verification_step ≤ t_commit` 的比例(锁死前验证);fail 24.4% vs pass 96.1%。

**验证错位（misplaced verification）** — 失败 agent 不是不验证,而是把验证推迟到锁死之后:V 占比 5.2%(犯错前)→17.8%(锁死后)(三阶段 pre/mid/post=5.2/10.1/17.8%,旧记录 4.5→29.9 与当前数据不符,已更正)。验证成了收尾仪式,非事前把关。

**宣称卫生（claim hygiene）** — 在最终完成宣称(C)前 3 步内是否有验证动作(V)。fail 69.6% vs pass 83.0%(仅差 13 点,远小于 F4 的 72 点)→ 失败"形式上讲流程"但流程是空壳。

---

## F. 锁死后动态（RQ2）

**察觉（awareness，t_commit 之后，4 类）**
- **never_aware（从未察觉，58.7%）** — 始终没意识到已失败。
- **aware_wrong_fix（察觉但错修，34.9%）** — 意识到了但用了错误的修法。
- **aware_abandoned（察觉后放弃，4.3%）** — 意识到并放弃。
- **aware_too_late（察觉太晚，2.1%）** — 意识到时已无步数挽回。

**察觉延迟（awareness latency）** — `first_awareness_step − t_surface`,信号浮出到察觉的步数;中位仅 1 步(p75=4)→ 瓶颈不在反应速度。

**尾部主导行为（tail_dominant_behavior，6 类）** — 锁死后的主要行为:thrash_repeat(反复折腾)、new_wrong_direction(转新错向)、cosmetic_progress(表面进展)、fabrication(造假)、verification_theater(验证剧场)、immediate_claim(立即宣称)。

**五种死法 / 退化模式（degradation regimes，M14，按 awareness×尾部行为分型,先匹配先得)**
- **theatrical_winddown（仪式收尾，27.6%）** — 尾部=verification_theater;走一遍验证流程然后宣称。
- **misdiagnosed_repair（误诊修复，24.1%）** — awareness∈{aware_wrong_fix, aware_too_late};以 1/4 案例吞 39.3% 浪费,**最贵**。
- **quick_capitulation（快速投降，18.2%）** — 尾部=immediate_claim;锁死即宣称收手,尾巴最短(2 步)。
- **fabricated_exit（造假退场，15.1%）** — 尾部=fabrication;以编造收场。
- **blind_persistence（盲目坚持，14.9%）** — 其余(never_aware/aware_abandoned 的折腾)。

**尾部 / 浪费（tail / waste）** — `m − t_commit`,锁死后白跑的步数。锁死后总浪费 27,424 步;`waste_share` = 某模式占总浪费的比例。

**恢复（recovery）** — agent 从错误中纠回的尝试(fail 侧 `num_recovery_attempts`;pass 侧 `num_recoveries`)。

**绕路长度（detour length，pass 侧）** — 成功轨迹中一次偏离-纠回的步数;成功恢复中位 5 步、91% 在 20 步内("20 步保质期")。

---

## G. 造假与可疑通过（fabrication & suspicious pass）

**造假（fabrication）** — agent 伪造内容以制造完成假象;占失败 25.7%,其中 83.9% 起始于 t_commit 当步或之后 → 是退场策略(coping),非根因。

**造假四型（fabrication types）**
- **direct_fabrication** — 凭空捏造内容/数据/事实。
- **fake_artifact_or_execution** — 伪造产物或执行(假装运行过、伪造输出文件/终端输出)。
- **false_completion_or_validation** — 虚假的完成或验证声明(没做却称做了/通过)。
- **proxy_or_shortcut** — 用代理/捷径替代真正解法(如硬编码期望输出)。

**可疑通过（suspicious_pass）** — 通过了测试但未真正解决任务(proxy 解、硬编码输出、测试过拟合、环境侥幸);占成功 6.4% [4.4–8.4] → benchmark 及格线本身约 6% 水分。

**险过（near_miss）** — 成功但接近失败的轨迹(pass 侧标记)。

---

## H. 可观测性与先兆（observability，F5/F8）

**先兆（forewarning）** — t_commit **严格之前**出现的可观察警示信号;占失败 61.8%,中位提前 6 步。

**先兆五型（forewarning types）** — command_error(命令报错)、empty_or_unexpected_output(空/异常输出)、repeated_command(重复命令)、self_doubt_language(自我怀疑措辞)、contradictory_evidence(矛盾证据)。

**静默失败（silent failure）** — `t_surface is None`:运行结束前无任何可观察失败信号;占 28%。

**可观测性三层（observability tiers，M4）**
- **Tier A（可观测窗口，68.2%）** — 有先兆 或 lag≥3:存在可被监控利用的预警窗口。
- **Tier C（不可见，9.5%）** — 静默 且 lag=0 且 无先兆:锁死当下毫无可观察痕迹。
- **Tier B（中间）** — 其余。

**事后可见 vs 实时可见** — 标注者看全程能辨认 68% 有先兆(回溯性),但实时监视器只看前缀几乎只在锁死当步/之后才报警(F5 的核心鸿沟)。

---

## I. Detection Oracle 实验（RQ1 的 F5/F6/F14/F7）

**检测预言机 / 监视器（detection oracle）** — 一个 Sonnet 4.6 模型,只看轨迹**前缀**,判断该轨迹是否已进入不可恢复的失败路径。

**前缀（prefix）** — 轨迹截断到第 t 步;切点 = t_commit × {0.25, 0.5, 0.75, 1.0, 1.25}(成功轨迹用自身 m 同比例)。

**三类标签（按"干死那一刻"定，不按任务难易）**
- **POSITIVE（577）** — 失败轨迹、t ≥ t_commit:已锁死,该报警。
- **NOTYET（900）** — 失败轨迹、t < t_commit:尚未锁死,正确答案"否";若报警=提前预警(单独统计,不算误报)。
- **NEGATIVE（1182）** — 成功轨迹任意前缀:永不该报警。

**自暴露 vs 规格相对（self-revealing vs spec-relative）** — 失败可检测性的两个 regime:*自暴露*(造假/环境报错,行为本身就暴露,光看动作能抓)vs *规格相对*(违背要求,必须知道任务规格才能判)。F6 核心二分。

**recall（召回）** — 抓住的 POSITIVE / 全部 POSITIVE(抓得全不全);只在 POSITIVE vs NEGATIVE 上算。

**precision（精确）** — 报警且真 POSITIVE / 所有报警(喊得准不准,含误伤成功轨迹)。

**操作点 τ\*（operating threshold）** — alarm = `committed=true 且 confidence ≥ τ`;扫描 τ,报告 F1 最大处。

**提前量（lead time）** — `t_commit − 最早报警切点`;>0 = 锁死前喊住。oracle 的 lead_median=0、lead_mean 0.7–1.9。

**抓住率（caught share）** — 至少被报警一次的失败轨迹占比;caught_before_commit = 锁死前就报警的占比。

**早停（early-stop）** — 反事实策略:首次报警即停手。save=省下的失败尾部步数比例(保守,只算 t_commit 当时/之后的报警);cost=成功轨迹被误停切掉的步数比例;net=save−cost。

**决定性步一致性（decisive_step within-2）** — 监视器独立指认的"决定性错误步"落在标注 t_commit ±2 步内的比例(86–88%);独立可靠性背书。

**难度泄漏（difficulty leakage）** — 监视器靠"任务一看就难"而非"轨迹当下状态"猜失败的作弊风险;§4 检查 = 成功轨迹早期前缀误报率须低(实测 2–3%,通过)。

**长轨迹续写（continuation artifact）** — 超长前缀下监视器"入戏"继续扮演 agent 写轨迹而非给判断;按"未报警"保守计入。

---

## J. 统计方法

**任务内配对（within-task paired）** — 同一任务的 pass 与 fail 配对比较,每个任务自己当对照,消除任务难度混杂(M7)。

**Cliff's delta（δ）** — 非参效应量 = P(a>b) − P(a<b),范围 [−1,1];|δ|<0.15 视为小效应。

**Mann–Whitney U** — 两独立组分布差异的非参检验(秩和)。

**Wilcoxon signed-rank** — 配对样本的非参检验(M11 逐轨迹前后对比)。

**sign test（符号检验）** — 仅看配对差值符号的精确二项检验(M7)。

**bootstrap CI（自助置信区间）** — 重采样 10,000 次得到的百分位 95% 置信区间。

**Cramér's V** — 列联表关联强度,范围 [0,1];<0.15 为弱关联(M16 model/agent × trigger)。

**二因素方差分解（two-way variance decomposition）** — 把某指标的跨格方差拆成 model 主效应、agent(scaffold)主效应、interaction(交互)三部分,带任务-bootstrap CI(M15)。

**交互项（interaction term）** — 方差中既不能单独归 model 也不能单独归 agent 的部分;成功率上它最大(40%)→ 成败是 model×scaffold 配对属性。

**near-cap（近上限）** — 轨迹步数接近该 agent 步数上限(≥0.95×max)的比例;用于排除"失败只是撞了步数墙"的混杂(实测 0.2–0.3%,已排除)。
