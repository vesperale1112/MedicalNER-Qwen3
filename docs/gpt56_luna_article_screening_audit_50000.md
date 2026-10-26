# GPT-5.6 Luna 前 50,000 篇文章筛选抽样调查

调查日期：2026-08-04

本报告检查 `gpt-5.6-luna` 对 `articles.json` 中索引 `0-49999` 的筛选结果。该批结果使用当时的 v2 prompt（`2.0.0-draft.2`），结果来自 `data/treatment_related_articles/filtering/gpt56_luna_article_screening_checkpoint.jsonl`。prompt 文件后来已更新为 v3，因此不能把下文 v2 指标与文末的 v3 试跑指标直接合并。

2026-08-10 又对索引 `50000-50049` 进行了 v3.0.0 补充试跑和逐条复核，结果见文末“v3.0.0 补充试跑”一节。

**KEEP 的整体质量较好，但 DROP 的漏召回比较明显，尤其会系统性漏掉量表、问卷和评分工具对应的 `assesses_for` 关系。因此，当前 DROP 不适合作为不可逆删除结果。**

下文中的“原文”均指文章标题或摘要中与判断直接相关的句子。为了便于阅读，只给出忠实的中文译文，不再重复英文全文。

## 抽样方法和总体结果

前 50,000 条 checkpoint 没有索引缺失或重复，索引连续覆盖 `0-49999`。运行结果如下：

| 项目            |   数量 |
| --------------- | -----: |
| 已尝试文章      | 50,000 |
| 严格验证通过    | 47,597 |
| 完成但验证失败  |  2,301 |
| JSON 解析失败   |     99 |
| API 请求失败    |      3 |
| 模型输出 KEEP   | 25,362 |
| 模型输出 REVIEW |  1,649 |
| 模型输出 DROP   | 22,887 |
| 未解析出决策    |    102 |

语义抽样只从严格验证通过的 47,597 条中进行，避免把 JSON、schema 或证据片段格式问题混入语义判断。可抽样总体为：

- 23,190 条有效 KEEP；
- 1,520 条有效 REVIEW；
- 22,887 条有效 DROP。

使用固定随机种子 `20260804`，把 `0-49999` 分成五个连续的 10,000 索引段。每段抽取：

- 30 条 DROP；
- 20 条 KEEP；
- 5 条 REVIEW。

因此总样本为 `5 × 55 = 275` 条，其中包括 150 条 DROP、100 条 KEEP 和 25 条 REVIEW。逐条重新扫描标题与完整摘要，按照当时 v2 prompt 的 17 个 active relations 和允许的实体属性给出复核决策。

这些标签来自一次逐条语义复核，没有经过两名独立标注者和第三方仲裁，因此应视为质量审计与风险信号，而不是正式 gold standard。对于边界不够清楚、需要轻微推断或实体类型可能变化的记录，本报告优先标为 REVIEW，而不是强行判为 KEEP 或 DROP。

本次调查只读取现有文章和 checkpoint，没有发送任何新的 API 请求。

本次 275 条样本中有 270 条 Embase、5 条 Cochrane，没有 PubMed。原因是前 50,000 条原始数据本身由 796 条 Cochrane 和 49,204 条 Embase 组成。因此，本报告主要反映当前这部分 Embase/Cochrane 数据，不能直接代表后面的 PubMed 数据。

复核矩阵如下。单元格顺序均为“复核 KEEP / REVIEW / DROP”。

| 索引范围    |       抽中的 30 条 DROP |    抽中的 20 条 KEEP |   抽中的 5 条 REVIEW |
| ----------- | ----------------------: | -------------------: | -------------------: |
| 0-9999      |              2 / 4 / 24 |           20 / 0 / 0 |            1 / 4 / 0 |
| 10000-19999 |              5 / 3 / 22 |           18 / 1 / 1 |            1 / 4 / 0 |
| 20000-29999 |              2 / 2 / 26 |           17 / 2 / 1 |            1 / 4 / 0 |
| 30000-39999 |              4 / 4 / 22 |           19 / 0 / 1 |            1 / 4 / 0 |
| 40000-49999 |              5 / 3 / 22 |           18 / 1 / 1 |            0 / 5 / 0 |
| 合计        | **18 / 16 / 116** | **92 / 4 / 4** | **4 / 21 / 0** |

主要结果是：

- 在 150 条模型 DROP 中，116 条确实可以 DROP，18 条应该明确 KEEP，16 条至少应该 REVIEW。也就是 **34/150（22.7%）不应被不可逆删除**。其 Wilson 95% 区间为 16.7%-30.0%。
- 其中明确应该 KEEP 的假 DROP 为 **18/150（12.0%）**，95% 区间为 7.7%-18.2%。
- 在 100 条模型 KEEP 中，92 条支持 KEEP，4 条更适合 REVIEW，4 条应该 DROP。也就是模型 KEEP 的直接接受率为 **92.0%**；如果只关心“是否保留给下一阶段”，96/100 仍然应该保留。
- 在 25 条模型 REVIEW 中，21 条维持 REVIEW，4 条其实可以直接 KEEP，没有发现应该明确 DROP 的样本。REVIEW 的使用整体比较合理，只是有少量过于保守。

如果仅为了风险评估而把 DROP 样本点估计粗略投影到全部 22,887 条 DROP，大约可能有 5,188 条应该保留为 KEEP 或 REVIEW，其中约 2,746 条可能是明确 KEEP。按区间估算，应保留数量可能在约 3,822-6,866 条之间。**这只是单次语义复核的风险投影，不是金标准计数，不能直接据此批量改标签。**

## DROP 判断的合理与不合理案例

### 合理的 DROP

以下文章虽然与治疗有关，但没有落入当前 KG schema，模型 DROP 是合理的。

#### 索引 1058：微波消融与双极电凝治疗特发性鼻出血

标题：`A comparative analysis of microwave ablation versus bipolar electrocautery in patients with idiopathic epistaxis`

关键原文中文译文：

> 特发性复发性鼻出血是最常见的耳鼻喉急症之一。研究比较微波消融与双极电凝的效果，并认为微波消融对特发性复发性鼻出血是一种良好的治疗方案。

模型给出 DROP，理由是文章只比较操作性治疗及其结局，没有允许的关系或可复用属性。该判断合理。微波消融和双极电凝属于操作或器械治疗，不是 schema 中的 Medication；当前 schema 也没有“手术/操作治疗某疾病”的关系。即使研究结论认为疗效良好，也不能映射成 `Medication.indications`。

#### 索引 6836：认知行为治疗用于 PTSD

标题：`COGNITIVE-BEHAVIORAL THERAPY METHODS IN THE TREATMENT OF POST-TRAUMATIC STRESS DISORDER AND THEIR ROLE IN MENTAL HEALTH RECOVERY`

关键原文中文译文：

> 认知行为治疗方法是治疗 PTSD 的优先选择，可减少症状并改善生活质量。

这句话在临床上有意义，但 CBT 是心理治疗，不是 Medication。当前 schema 没有“心理治疗适用于疾病”的 active relation，也明确禁止把 CBT、咨询或生活方式干预标成 Medication。因此 DROP 合理。

#### 索引 20100：剖宫产与围产期情绪、焦虑和创伤症状

标题：`Preventing Maternal Mood, Anxiety, and Trauma Symptoms After Cesarean Delivery`

关键原文中文译文：

> 高危妊娠诊断和剖宫产都与围产期情绪、焦虑及创伤症状风险升高有关。剖宫产后的患者中约三分之一报告这些症状升高。

这里描述的是症状发生风险，而不是疾病确诊后的预后因素，也没有说明剖宫产会影响某疾病的诊断。当前 schema 没有一般的“风险因素导致疾病发生”关系，因此不能为了医学相关性强行映射为 `associated_with_poor_prognosis_in` 或 `affects_diagnosis_of`。DROP 合理。

#### 索引 44280：术后谵妄与新发痴呆风险

标题：`Postoperative delirium after hip surgery is a potential risk factor for incident dementia: A systematic review and meta-analysis of prospective studies`

关键原文中文译文：

> 髋部手术后的术后谵妄显著增加新发痴呆和认知下降的风险；荟萃分析认为术后谵妄是新发痴呆的风险因素。

该结果是“新发疾病风险”，不是已经患有目标疾病后的不良预后；文章也没有把谵妄明确描述为痴呆的躯体病因。根据 prompt 的边界，不能把发病风险自动转换为 `associated_with_poor_prognosis_in` 或 `somatic_cause_of`，所以 DROP 合理。

### 明确不合理的 DROP：应该 KEEP

这类错误大多来自模型把量表视为“只是研究结局”，但当前 prompt 明确要求扫描 `assesses_for`。量表被用于 RCT 结局，并不妨碍“量表评估某症状/疾病”本身成为可复用关系。

#### 索引 3071：PCL-5、PHQ-8、DERS-16 和 WSAS

标题：`A Randomized Controlled Trial Comparing Brief Peer Supported webSTAIR to Enhanced Wait List`

关键原文中文译文：

> 研究评估四项结局：PTSD 症状和抑郁症状的减少，分别由 PCL-5 和 PHQ-8 测量；情绪调节和工作及社会适应的改善，分别由 DERS-16 和 WSAS 测量。

模型以“干预研究及结局不属于允许事实”为由 DROP。但原文直接给出了工具与目标：`PCL-5 assesses_for PTSD symptoms`、`PHQ-8 assesses_for depression symptoms`，并且 DERS-16、WSAS 也对应情绪调节问题和功能损害。至少前两项已经足以 KEEP。

#### 索引 15090：BDI 和 HAM-D 评估卒中后抑郁

标题：`Impact of Intensive Social Interaction on Post-Stroke Depression in Individuals With Aphasia`

关键原文中文译文：

> 主要结局是治疗一个月后自评和临床评定的抑郁严重程度变化；共同主要结局工具为贝克抑郁量表（BDI）和汉密尔顿抑郁量表（HAM-D）。

这是直接、可复用的 `assesses_for`。模型因为文章是计划中的干预试验而 DROP，但“试验是否完成”只影响治疗效果结论，不影响量表的明确评估目标。该条应 KEEP。

#### 索引 16613：PHQ-9 评估抑郁严重程度

标题：`Knowledge of HIV status decreases depressive symptoms among female sex workers`

关键原文中文译文：

> 我们使用 PHQ-9 抑郁量表测量参与者抑郁症状的严重程度，并估计可能抑郁的患病比例；得分达到 10 分表示临床抑郁。

原文同时提供工具、目标和评分解释，明确支持 `PHQ-9 assesses_for depressive symptoms/depression`，也可能支持 Interview Tool 的可复用属性。模型把它当作研究测量后直接 DROP，属于明显漏检。

#### 索引 18135：精神分裂症谱系障碍中的社会认知损害

标题：`Neuromodulation of Social Cognitive Circuitry in People With Schizophrenia Spectrum Disorders`

关键原文中文译文：

> 研究考察 rTMS 和 iTBS 对精神分裂症谱系障碍患者社会认知损害的影响，并预计刺激能够改善这些社会认知缺陷。

即使不保留刺激治疗效果，原文仍直接把“社会认知损害/缺陷”归属于精神分裂症谱系障碍患者，可形成 `social cognitive impairments is_associated_symptom_of schizophrenia spectrum disorders`。模型只看到干预设计而忽略了症状关系，应 KEEP。

#### 索引 26648：PCL-5 评估 DSM-5 PTSD 症状

标题：`Treatment of traumatic stress in people with intellectual disabilities: Preliminary results from a randomised controlled trial on the effectiveness of EMDR for DSM 5 PTSD`

关键原文中文译文：

> 主要结局为 PTSD Checklist for DSM-5（PCL-5）所测量的创伤后应激障碍症状。

这是最直接的 `PCL-5 assesses_for PTSD symptomatology`，不需要依赖外部知识。模型将其 DROP 不符合当前 prompt 的 relation-first 和 recall-first 原则。

#### 索引 40382：多种标准量表评估失眠、疼痛、抑郁、焦虑和疲劳

标题：`Telehealth-delivered cognitive behavioral therapy - a potential solution to improve sleep quality and normalize the salience network in fibromyalgia: a pilot randomized trial`

关键原文中文译文：

> 基线和治疗后使用标准量表评估临床状态，包括失眠严重程度指数、简明疼痛量表、数字疼痛评分、贝克抑郁量表、贝克焦虑量表、情境疲劳量表和纤维肌痛影响问卷。

虽然这些工具用于试验结局，但工具名称和上下文已经直接标识其评估目标。至少 ISI 对失眠、疼痛量表对疼痛、抑郁和焦虑量表对相应症状构成多个 `assesses_for`。该条应 KEEP。

#### 索引 43832：Roland-Morris 功能障碍问卷

标题：`A Randomized, Placebo-Controlled Trial of Ibuprofen Plus Metaxalone, Tizanidine, or Baclofen for Acute Low Back Pain`

关键原文中文译文：

> 患者须在 Roland-Morris 功能障碍问卷上得分超过 5 分；该问卷包含 24 个条目，用于评估由腰痛造成的功能损害。

原文不只是使用一个结局指标，而是直接定义了该问卷评估的对象，支持 `Roland-Morris Disability Questionnaire assesses_for functional impairment caused by low back pain`。模型 DROP 明显过严。

#### 索引 44302：MMSE、焦虑和老年抑郁量表

标题：`Effects of cognitive stimulation program on cognition and mood in older adults, stratified by cognitive levels: A randomized controlled trial`

关键原文中文译文：

> 主要结局为西班牙语版简易精神状态检查量表所测量的总体认知；次要结局由 Barthel 指数、Lawton-Brody 量表、Goldberg 问卷焦虑分量表和简版 Yesavage 老年抑郁量表测量。

MMSE 对认知、Goldberg 焦虑分量表对焦虑、Yesavage 量表对抑郁的评估目标都可以从原文直接定位。该条应该 KEEP，而不是因为属于结局测量就 DROP。

### 不宜直接 DROP、但更适合 REVIEW 的例子

#### 索引 9899：PHQ-9、HADS 和营养评估工具

标题：`Effect of nurse-led multi-disciplinary treatment on patients with head and neck tumors: A randomized controlled trial`

关键原文中文译文：

> 营养状态使用 NRS 2002 和 PG-SGA 评估，心理状态使用 DT、PHQ-9 和 HADS 评估。

工具与大类目标是明确的，但一句话没有逐一说明 DT、PHQ-9 和 HADS 分别对应何种具体疾病或症状。直接 KEEP 某一精确关系需要少量语义补全，因此 REVIEW 比 DROP 更安全。

#### 索引 19374：HAM-D、MADRS 与产后抑郁

标题：`Phase 3 study evaluating brexanolone, a gabaa receptor modulator, in moderate postpartum depression`

关键原文中文译文：

> 中度产后抑郁女性按 HAM-D 总分 20 至 25 分入组；主要结局为 HAM-D 总分变化，次要结局包括 MADRS 评分变化、HAM-D 应答和缓解。

标题和上下文强烈提示这些量表用于评估产后抑郁，但摘要主要把它们写成入组和结局指标，没有一句完整的“量表评估产后抑郁”定义。按照严格直接证据要求，至少应进入 REVIEW，而不是 DROP。

#### 索引 41408：HADS、MINI 自杀量表和 MoCA

标题：`Transcutaneous Auricular Vagus Nerve Stimulation (ta-VNS) for Treatment of Drug-Resistant Epilepsy: A Randomized, Double-Blind Clinical Trial`

关键原文中文译文：

> 患者接受生活质量评估、汉密尔顿焦虑抑郁量表、MINI 自杀量表和 MoCA 量表评估。

量表名称提示焦虑、抑郁、自杀风险和认知目标，但句法上没有把每个工具与目标逐一连接。保留到 REVIEW 由更强模型确认，符合 recall-first；直接 DROP 风险偏高。

## KEEP 判断的合理与不合理案例

### 合理的 KEEP

#### 索引 151：ADHD 核心症状

标题：`Family therapy for attention-deficit disorder or attention-deficit/hyperactivity disorder in children and adolescents`

关键原文中文译文：

> ADHD 由注意力不集中、冲动和多动这些核心症状构成。

这是明确的疾病核心症状定义，可形成多个 `is_core_symptom_of` 关系，KEEP 合理。

#### 索引 14794：CIWA-Ar 与 DOS

标题：`Hyperbaric Oxygenation in Treatment of Alcohol Dependence Syndrome`

关键原文中文译文：

> 戒断症状的严重程度使用临床酒精戒断评估量表（CIWA-Ar）评定；谵妄使用谵妄观察筛查量表（DOS）评定。

工具、目标和方向都直接出现，支持 `CIWA-Ar assesses_for withdrawal symptoms` 和 `DOS assesses_for delirium`。KEEP 合理。

#### 索引 31178：已批准用途和常见不良事件

标题：`Efficacy and safety of JZP-258 in a phase 3, placebo-controlled, double-blind, randomized withdrawal study in adults with narcolepsy with cataplexy`

关键原文中文译文：

> 羟丁酸钠已获批用于治疗发作性睡病患者的猝倒和日间过度嗜睡。JZP-258 常见的治疗期间不良事件包括头痛 20.4%、恶心 12.9% 和头晕 10.4%。

“已获批用于治疗”明确支持 Medication.indications；“常见不良事件”还带有频率，支持 common_side_effects。KEEP 合理，并且不依赖对试验疗效的推断。

#### 索引 45359：哌甲酯是一线治疗

标题：`The Effects of Methylphenidate on Spontaneous Fluctuations in Reward and Cognitive Control Networks in Children With Attention-Deficit/Hyperactivity Disorder`

关键原文中文译文：

> 哌甲酯是注意缺陷多动障碍的一线治疗。

这句话直接支持 `Methylphenidate first_line_for ADHD`，是当前 schema 中最明确的一类保留事实。

### 明确不合理的 KEEP：应该 DROP

#### 索引 13323：把试验目的当成药物适应证

标题：`Evaluation of SPN 812 (Viloxazine Extended-release Capsule) 200 and 400 mg Efficacy and Safety in Adolescents With ADHD`

关键原文中文译文：

> 这是一项随机、双盲、安慰剂对照研究，用于评估 SPN-812 作为单药治疗 12 至 17 岁 ADHD 青少年的有效性和安全性。

模型把它标为 `SPN-812.indications = ADHD`。但这只是研究目的和试验用药方案，没有说药物已获批、已被认可使用或具有既定适应证。prompt 明确规定“研究目的、干预组和一般疗效本身不能建立适应证”，因此本条不应 KEEP。

#### 索引 27590：把围术期风险标志误当作疾病症状

标题：`Effect of electroencephalography-guided anesthetic administration on postoperative delirium among older adults undergoing major surgery`

关键原文中文译文：

> 术中脑电图波形抑制通常提示全身麻醉过深，并且与术后谵妄有关。

模型构造了 `EEG waveform suppression is_associated_symptom_of postoperative delirium`。但 EEG 抑制是围术期生理标志或风险相关因素，不是谵妄症状。当前 schema 没有普通 biomarker/risk-factor 关系，不能因为“associated with”就标成症状关系，应 DROP。

#### 索引 32023：把 14 人单剂量研究中的样本不良事件泛化为通用副作用

标题：`Impact of the moderate CYP3A4 inhibitor diltiazem on the single-dose pharmacokinetics of the dual orexin receptor antagonist ACT-541468`

关键原文中文译文：

> 研究纳入 14 名健康男性，给予单剂量 ACT-541468。该研究中最常见的不良事件为嗜睡 92.9% 和头痛 50.0%。

模型把这两个事件标成 ACT-541468 的 `common_side_effects`。但“最常见”只描述这个很小的健康志愿者 PK 样本，且是单剂量和特定药物相互作用背景。prompt 明确禁止用孤立或仅在单项研究中出现的不良事件建立通用常见副作用，因此应 DROP，至少不能直接 KEEP。

#### 索引 40079：把研究样本严重程度当作疾病亚型知识

标题：`Effectiveness of strengthening oropharyngeal myofunctional therapy combined with cervical spine exercises in mild to moderate obstructive sleep apnoea`

关键原文中文译文：

> 随机试验纳入 32 名被诊断为轻至中度阻塞性睡眠呼吸暂停的参与者。

模型把 `mild to moderate` 标成 OSA 的 subtype。该句只是本研究纳入人群的严重程度范围，没有定义或讨论 OSA 的疾病亚型。按照“研究队列信息不能单独触发 KEEP”的边界，应 DROP。

### 更适合 REVIEW、而不是直接 KEEP 的例子

#### 索引 12886：共病目标不具体

标题：`Estimating the Acute Impact of Competing Mental Imagery on Craving in Alcohol Use Disorder`

关键原文中文译文：

> 文献已经充分描述酒精使用障碍与“另一种精神疾病”双重诊断的患者。

模型构造了 AUD 与 `another psychiatric condition` 的 `co_occurs_with_frequency`。但目标只是泛称，没有可落地的具体疾病实体，且没有数字或清晰的定性频率。文章可能包含可复用共病信息，但当前候选关系不够具体，应 REVIEW。

#### 索引 20237：病例中的奥氮平增重

标题：`Probable Olanzapine-Related Idiopathic Intracranial Hypertension in an Adolescent With First-Episode Psychosis`

关键原文中文译文：

> 作者报告一例青少年病例，其可逆性颅内高压可能与奥氮平引起的体重增加有关；多数非典型抗精神病药具有导致显著体重增加的倾向。

模型把 `olanzapine-induced weight gain` 直接标成奥氮平的通用 common_side_effects。文章确实给出药物类别层面的已知倾向，但奥氮平对应的是单病例表述，属性 owner 和通用性仍需确认。REVIEW 比直接 KEEP 更稳妥。

#### 索引 23630：把 22 人队列结果标成疾病核心特征

标题：`The clinical, electrocardiographic, echocardiographic profile and in-patient outcomes of adult Filipino patients with methamphetamine drug use associated cardiomyopathy at a tertiary hospital`

关键原文中文译文：

> 研究纳入 22 名患者；超声心动图显示多心腔扩张和射血分数降低。

模型把这一结果标为甲基苯丙胺相关心肌病的 core_features。它可能是有价值的临床表现，但证据来自单中心小样本描述性队列，原文没有称其为定义性或核心特征。至少应 REVIEW，不能直接把队列发现泛化为疾病定义。

#### 索引 47305：从单病例时序推断通用症状关系

标题：`THE EYES AS A WINDOW TO THE HEART: A CASE OF INFECTIVE ENDOCARDITIS PRESENTING WITH ENDOPHTHALMITIS`

关键原文中文译文：

> 一名患者病情恶化时突然出现双眼视力丧失，随后发现双眼前房积脓，并被诊断为内源性细菌性眼内炎和感染性心内膜炎。

模型将“突然双眼视力丧失”直接标为眼内炎的通用 associated symptom。病例中两者确实同时出现，但原文主要描述个体诊疗过程，没有明确给出一般性症状定义，而且还存在多个同时发生的严重疾病。应 REVIEW，避免从单病例时序过度泛化。

## REVIEW 判断的表现

REVIEW 整体使用合理。25 条中有 21 条维持 REVIEW，4 条可以更有把握地 KEEP，没有发现必须明确 DROP 的记录。以下是三个代表性例子。

#### 索引 7567：标题与摘要内容冲突，REVIEW 合理

标题：`Comparison of Ketamine Versus Saline During Sedation in Patients With Major Depressive Disorder: a Double-blind Trial`

关键原文中文译文：

> 标题描述重度抑郁障碍患者接受氯胺酮与生理盐水比较，但摘要正文却描述健康成人中的异丙酚方案。

标题和摘要的研究对象、药物及人群相互冲突，无法安全决定 KEEP 或 DROP。模型使用 `REVIEW_CONTRADICTORY_EVIDENCE` 是正确的。

#### 索引 5647：实际上可以直接 KEEP

标题：`Behavioral and Pharmacologic Treatment of Binge Eating and Obesity`

关键原文中文译文：

> 暴食障碍是最常见的正式进食障碍，并且与肥胖及生物—心理—社会功能损害强烈相关。

模型认为 BED 的 `comorbidity_types = obesity` 仍然含糊而给 REVIEW。这里疾病 owner、共病对象和“强烈相关”都很明确，支持可复用的 Disease.comorbidity_types 属性，因此可以直接 KEEP。这个错误不会造成数据丢失，因为 REVIEW 本来就会进入后续强模型。

#### 索引 22037：量表目标已经足够清楚，可以 KEEP

标题：`Safety, Tolerability and Effectiveness of Dolutegravir/Lamivudine Compared With Bictegravir/Tenofovir Alafenamide/Emtricitabine in People Living With HIV Without Antiretroviral Experience`

关键原文中文译文：

> 神经精神障碍将使用抑郁、焦虑和失眠量表评估，包括 HADS-D/HADS-A、失眠严重程度指数和 PHQ-9。

模型因为这些是未来的研究程序而给 REVIEW。但句子已经明确说明各量表的评估目标；计划在未来使用不等于量表用途本身不确定。按当前 prompt，可以直接 KEEP 对应的 `assesses_for` 关系。

## 调查结论

这次扩大到 275 条后，结论比最初 55 条抽样更稳定：

1. **主要风险是 DROP 漏召回，而不是 KEEP 大量过度保留。** 150 条 DROP 中有 34 条至少应该保留，占 22.7%；这个信号在五个索引段中都出现，并非集中于某一个批次。
2. **`assesses_for` 是最明显的系统性漏检点。** 模型经常说“这只是试验结局”，但 prompt 允许并要求抽取量表、问卷和评估工具与疾病/症状的关系。是否属于 RCT outcome 不应自动否定该关系。
3. **KEEP 质量相对较好。** 100 条 KEEP 中 92 条可以直接接受，4 条需要 REVIEW，只有 4 条应 DROP。主要过度保留模式是：把试验目的当适应证、把小样本不良事件当通用副作用、把队列严重程度当疾病亚型、把风险标志误标为症状。
4. **REVIEW 路径本身有效。** 25 条 REVIEW 都值得保留，其中 21 条确实存在合理歧义，4 条只是过于保守而可以 KEEP。
5. **格式验证不能发现语义漏召回。** 所有 22,887 条 DROP 都通过了本地严格验证；验证器只能检查 JSON、schema、类型组合和原文片段，无法判断摘要中是否遗漏了另一条允许关系。

因此，不建议把当前 22,887 条 DROP 直接删除。比较安全的处理方式是先做一个不调用 API 的本地救援层：凡是 DROP 中出现明确量表/问卷/评分工具，并在同句或邻近句中出现被评估疾病、症状或功能损害的，先提升为 REVIEW；再对这些高风险 DROP 使用更强模型或人工复核。与此同时，后续正式评估应制作 300-500 条双人标注或仲裁后的 gold set，重点增加 `assesses_for`、Medication.indications、common_side_effects、队列属性和风险因素边界案例。

最后需要区分语义问题和技术问题：本报告的 275 条全部来自严格有效输出；另外仍有 2,301 条完成但验证失败、99 条解析失败和 3 条请求失败。它们需要单独做本地证据修复或有限重试，不能用本报告的语义比例直接解释。

<details>
<summary>本次 275 条可复现样本索引</summary>

- 0-9999：151, 159, 334, 690, 714, 856, 1043, 1058, 1332, 1402, 1630, 1633, 1817, 1899, 1949, 2013, 2043, 2048, 2128, 2551, 2632, 2796, 2942, 3064, 3071, 3194, 3251, 3313, 3735, 4094, 4096, 4912, 5158, 5201, 5330, 5647, 5657, 5680, 6067, 6301, 6521, 6755, 6836, 7567, 7613, 8120, 8247, 8265, 8312, 8865, 8993, 9762, 9791, 9899, 9958
- 10000-19999：10003, 10804, 10832, 11236, 11402, 11621, 11863, 11993, 12034, 12414, 12587, 12618, 12789, 12808, 12886, 13197, 13313, 13323, 13374, 13684, 13836, 13957, 14433, 14617, 14794, 15048, 15090, 15261, 15493, 15758, 15853, 16074, 16091, 16109, 16115, 16228, 16245, 16432, 16613, 17148, 17601, 17866, 17899, 18092, 18135, 18173, 18299, 18512, 19116, 19374, 19413, 19437, 19476, 19587, 19760
- 20000-29999：20100, 20237, 20435, 20503, 20566, 21313, 21378, 21550, 21882, 22037, 22093, 22152, 22172, 22477, 22588, 22637, 22662, 22802, 22848, 23474, 23630, 23723, 23748, 23947, 24216, 24330, 24776, 24800, 25155, 25272, 25320, 25412, 25660, 25769, 25780, 25858, 25924, 26313, 26381, 26605, 26648, 26768, 26999, 27282, 27386, 27590, 27607, 27645, 28119, 28710, 29348, 29354, 29440, 29852, 29948
- 30000-39999：30236, 30805, 30928, 31068, 31128, 31178, 31241, 31339, 31579, 31610, 31848, 32023, 32157, 32217, 32248, 32255, 32478, 32679, 32692, 32921, 33101, 33149, 33634, 33715, 34344, 34955, 35295, 35765, 35786, 35843, 35903, 36179, 36264, 36542, 36780, 37343, 37349, 37410, 37761, 37832, 37962, 38490, 38582, 38818, 39056, 39158, 39209, 39240, 39244, 39272, 39278, 39642, 39778, 39894, 39943
- 40000-49999：40079, 40265, 40270, 40382, 40547, 40549, 41223, 41229, 41237, 41408, 41494, 41755, 42001, 42276, 42322, 42478, 42486, 42692, 42696, 42708, 43029, 43211, 43266, 43832, 44085, 44280, 44302, 44932, 45208, 45236, 45279, 45359, 45658, 45836, 45880, 46026, 46371, 46473, 46505, 46569, 47100, 47305, 47633, 48058, 48105, 48324, 48336, 48674, 48948, 48949, 49025, 49319, 49345, 49964, 49965

</details>

## v3.0.0 补充试跑：索引 50000-50049

审计日期：2026-08-10

本节单独检查 v3 prompt（`3.0.0-draft.1`）生成的连续 50 条结果。模型仍为 `gpt-5.6-luna`，索引范围为 `50000-50049`，原始输出整理在 `data/treatment_related_articles/filtering/gpt56_luna_article_screening_v3_trial_50000_50049.json`。本次逐条阅读了每篇文章的标题、完整摘要和全部候选事实；人工标签仍属于单人质量审计，不是正式 gold standard。

### v3 复核口径

本次不仅检查 KEEP/REVIEW/DROP，还检查候选实体类型、关系方向和证据片段。结合 v3 schema 及其原始表格说明，采用以下边界：

- `Risk` 表示自杀、自伤等风险结局或风险状态；环境暴露和危险因素应优先建成 `Etiology`。
- `Etiology.contributes_to -> Disease` 包括“病因或危险因素增加疾病发生概率”，不要求把统计相关夸大为确定因果。
- `Assessment Scale` 指 PHQ-9 等临床量表；Newcastle-Ottawa Scale 这类研究质量评价工具不属于临床量表。
- `Evidence.study_type` 虽然是 schema 属性，但“本文是 systematic review”本身不具有 prompt 所要求的独立、可复用临床意义，不能单独触发 KEEP。
- REVIEW 用于关系确实可能成立、但类型、方向、断言强度或上下文仍不安全的记录；纯研究相关性不自动进入 REVIEW。

### 运行和格式结果

| 项目 | 数量 |
| --- | ---: |
| 试跑文章 | 50 |
| 严格验证通过 | 45 |
| 完成但验证失败 | 5 |
| JSON 解析失败 | 0 |
| API 请求失败 | 0 |
| 模型输出 KEEP | 33 |
| 模型输出 REVIEW | 8 |
| 模型输出 DROP | 9 |
| 总 token | 145,321 |

5 条验证失败全部是 `evidence_quote` 不是连续原文片段，没有 schema version、关系类型、JSON 解析或请求错误：

- `50017`：把原文的 `Posttraumatic stress disorder (PTSD)` 改写成了 `PTSD`；
- `50021`、`50024`、`50042`、`50049`：在证据中使用了 `...` 省略中间文字。

这 5 条的 KEEP 决策都有真实 schema 事实支持，可以本地修复证据片段，无需再次调用付费 API。

### 决策复核结果

复核矩阵如下，行是模型决策，列是人工复核决策：

| 模型决策 | 人工 KEEP | 人工 REVIEW | 人工 DROP | 合计 |
| --- | ---: | ---: | ---: | ---: |
| KEEP | 31 | 0 | 2 | 33 |
| REVIEW | 2 | 6 | 0 | 8 |
| DROP | 1 | 1 | 7 | 9 |
| 合计 | **34** | **7** | **9** | **50** |

主要指标：

- 精确决策一致：`44/50`，即 **88.0%**；
- “保留（KEEP+REVIEW）/过滤（DROP）”一致：`46/50`，即 **92.0%**；
- 模型 KEEP 中 `31/33` 可维持 KEEP，直接接受率为 **93.9%**；
- 模型 REVIEW 中 `6/8` 维持 REVIEW，另 2 条可直接 KEEP，没有应 DROP 的记录；
- 模型 DROP 中 `7/9` 可维持 DROP，1 条应 KEEP、1 条应 REVIEW，即 `2/9` 不宜直接过滤。

人工复核标签的完整索引如下：

- KEEP（34）：50000, 50001, 50002, 50004, 50005, 50006, 50007, 50008, 50009, 50010, 50011, 50013, 50014, 50015, 50017, 50018, 50019, 50020, 50021, 50022, 50024, 50025, 50026, 50030, 50031, 50032, 50033, 50039, 50040, 50042, 50044, 50045, 50047, 50049。
- REVIEW（7）：50003, 50012, 50029, 50035, 50036, 50038, 50048。
- DROP（9）：50016, 50023, 50027, 50028, 50034, 50037, 50041, 50043, 50046。

### 6 条决策分歧

#### 模型过于保守

- `50025`，REVIEW -> KEEP：多篇系统综述给出了农药暴露与 Parkinson's disease 风险升高的统计结果。农药暴露应建为 `Etiology`，可支持 `contributes_to -> Disease`，不需要强行解释成确定因果。
- `50047`，REVIEW -> KEEP：摘要直接报告氡暴露与妊娠期糖尿病、高血压等结局的关联；虽然证据稀少并保留 `may`，仍支持带不确定性的 `Etiology.contributes_to -> Disease`。

#### 模型漏召回

- `50038`，DROP -> REVIEW：摘要报告内分泌干扰物、甲状腺激素与 ADHD 等神经认知障碍的关联，但具体化学物、方向和断言强度不够集中。存在合理的 `Etiology.contributes_to` 候选，至少应交给 REVIEW。
- `50039`，DROP -> KEEP：摘要汇总早期空气污染暴露与 ASD 发病风险的关联，并讨论易感人群修饰因素，直接支持 `air pollution exposure (Etiology) contributes_to ASD (Disease)`。

#### 模型过度保留

- `50043`，KEEP -> DROP：文章只泛泛讨论纳米生物传感器及其医疗应用。模型仅凭“systematic literature review”构造 `Evidence.study_type`，没有找到独立的临床 schema 事实；研究类型元数据不应单独触发 KEEP。
- `50046`，KEEP -> DROP：模型把用于研究偏倚评价的 Newcastle-Ottawa Scale 当成临床 `Assessment Scale`。摘要中的绿地关联证据为低或极低质量，也没有形成允许的保护关系，故应 DROP。

### 决策正确但候选事实仍需修正

严格 JSON/schema 验证只能发现格式和类型组合错误，不能保证候选事实语义正确。本批还有以下代表性问题：

- `50031` 的 KEEP 决策正确，但不应只抽取 `Evidence.study_type`；更有价值的事实是高温或热浪作为 `Etiology` 增加精神障碍就诊或死亡风险。
- `50044` 的 KEEP 决策正确，但 Newcastle-Ottawa Scale 不是临床量表；应抽取极端天气事件 `contributes_to` PTSD、抑郁、焦虑等疾病。
- `50049` 的 KEEP 决策正确，但模型把细颗粒物、慢性噪声等环境危险因素标成 `Risk`，并反向构造 `Disease associated_with_risk Risk`。按 v3 原始定义，它们应是 `Etiology`，方向应为 `Etiology contributes_to Disease`；同时其两条证据还含 `...`。
- `50006` 的文章应 KEEP，但“头痛和日间嗜睡在 PRM 与 placebo 中处于相同水平”，用它建立 PRM 通用 `side_effects` 属性偏强；该文另有更明确的获批用途和治疗层级事实可用。
- `50010`、`50030` 的关系在全文上下文中成立，但模型选择的 `evidence_quote` 没有同时覆盖量表或症状及其疾病目标，证据自包含性不足。

### v3 试跑结论

1. **决策层总体可用，但 DROP 仍不能直接视为不可逆结果。** 50 条中有 2 条模型 DROP 应保留；样本很小，`2/9` 只能作为风险信号，不能外推为全语料比例。
2. **v3 的主要新问题是 `Etiology` 与 `Risk` 混淆。** 环境暴露或危险因素增加疾病发生概率时，应使用 `Etiology.contributes_to -> Disease`；`Risk` 更接近自杀、自伤等风险结局。
3. **研究方法工具被误当成临床工具。** Newcastle-Ottawa Scale 不应映射为 `Assessment Scale`。临床量表和研究质量评价工具需要在 prompt 中明确分界。
4. **`Evidence.study_type` 容易造成无临床事实文章被保留。** generic systematic review/RCT 标签不应绕过“可复用临床意义”门槛。
5. **5 条验证失败都可本地修复。** 当前最直接的技术改进是禁止证据中的省略号，并在候选关系证据中同时覆盖 source、target 和断言词；不需要为这 5 条重新付费。

因此，v3 prompt 下一轮最值得补充的不是更多关系名称，而是三条短边界：`Etiology` 与 `Risk` 的区别、临床量表与研究质量工具的区别、`Evidence.study_type` 不能单独触发 KEEP。完成这些边界修订后，再用相同或扩展样本复测会比直接扩大生产调用更稳妥。
