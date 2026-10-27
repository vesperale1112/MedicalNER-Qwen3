# v3.1.0 补选文章、覆盖证据与标注网页更新

日期：2026-10-27。Schema：`schemas/v3.1.0/schema1026.xlsx`，16类实体、60行关系定义。

从最终 rescreen 的 88,676 条 KEEP 记录中补选 **20篇**，与原20篇合计 **40篇**。新增20篇均通过index关联原文，10篇PubMed、10篇Embase；其中含病例、共识和试验亚组的会议摘要，以保留诊断、沟通和监测场景。索引、非空DOI与标题均不与原批次重复。

逐篇摘要核对得到：**16/16类实体有候选素材；60行关系中 51 行有明确候选、6 行需确认、3 行存在缺口。未达到全部关系的明确覆盖。**

这里的覆盖是“每行至少一个端点合法的候选实例”。同名关系在不同起点的行分开计数；逆向关系可能共用一段证据。全部关系还可展开为 103 个允许的类型三元组，本表提供了其中 51 个明确实例，其余分支没有声称全部覆盖。属性字段的全面覆盖不在本次指标内。

“明确候选”仍需医学生按统一规范标注。全文没有阅读；本次检索是对最终KEEP池作定向候选检索，再逐篇阅读所选摘要，不是对88,676篇逐关系穷举。缺口仅表示本次40篇摘要未有充分证据，不能说整个文章池不存在。

## 交付文件

- `../pages/kg_annotation_20.html`：更新后的单个离线HTML，双击即可使用；文件名沿用，内容为原20篇＋新增20篇。
- `../kg_article_supplement_v3.1.0.json`：新增20篇的完整标题、摘要、来源、DOI、KEEP理由、研究设计和入选理由。
- `coverage.json`：本说明的结构化证据表，含逐行原文引文、端点类型、待确认理由和三份旧标注使用统计。

## 使用方式

1. 打开更新后的HTML，点击“导入进度”，选择自己上次的JSON。三位标注人会按姓名分别保存；新增文章从空白开始。
2. 用左侧批次筛选选择“原20篇·修订”或“新增文章”；状态筛选可查看待复核或含弃用项的文章。
3. 已弃用关系在关系列表和图谱中标出，旧属性在节点和属性编辑器中标出。原名称、属性值和证据保留，不自动将旧关系改名、反向或改成另一种医学含义。
4. 修订完旧标注并清除弃用项后，重新标记本篇完成。旧版的“已完成”导入后会改为“标注中”，原状态保存在annotation.previous_status；不冒充已按新schema复核。
5. 导出全部JSON会包含40篇，并注明schema.version=3.1.0、每篇schema_reviewed及schema_issues。图谱仍位于records[*].output.entities / output.relations；实体ID仍仅在单篇内有效。

网页保留旧localStorage键及旧行键，以兼容同一浏览器中的旧进度。文件移到其他位置或换浏览器时，仍应使用导入/导出；不要依赖本地浏览器跨路径共享进度。导入同一姓名同一篇已有标注会提示覆盖。三份旧JSON和原20篇筛选JSON未改动。

## Schema处理

- 新增Assessment Dimension；按新版定义区分量表evaluates→Disease/Symptom和measures→Assessment Dimension。
- 关系表TreatmentPlan、Communication分别统一为节点表Treatment Plan、Communication Strategy；原表写法仍可查阅。Relation列代码保持原样，包括`supports_Diagnostic Criterion_of`。
- 保留v3.0.0所有旧关系定义及旧属性。“已弃用”按起点类别、关系代码、终点类别判定，不仅比较名字；属性也按各节点的新字段判断。
- 新建关系默认只使用新版定义；旧关系在编辑已有标注时仍可打开、保留证据和修订。Schema参考页有新版定义、旧版兼容表和新版原表，并可下载新版Excel。

## 新增20篇

| 网页序号 | 原始index | 主题 / 材料 | 研究设计 |
|---|---:|---|---|
| 21 | 98091 | [CANMAT 2023 成人抑郁障碍指南更新](https://doi.org/10.1177/07067437241245384) | 临床指南更新 |
| 22 | 57744 | [围产期情绪与焦虑障碍的识别、筛查和治疗指南](https://doi.org/10.1016/j.jogc.2024.102696) | 临床指南 |
| 23 | 54297 | [做作性障碍的客观检查线索与非对抗性沟通](https://doi.org/10.1016/j.jaclp.2022.10.010) | 病例报告及文献讨论（会议摘要） |
| 24 | 54260 | [严重精神症状且无法言语患者的决策能力评估](https://doi.org/10.1016/j.jaclp.2022.03.053) | 病例报告及评估方法讨论（会议摘要） |
| 25 | 107246 | [恶性紧张症与血清素综合征的鉴别病例](https://doi.org/10.1192/j.eurpsy.2023.1626) | 病例报告及文献回顾（会议摘要） |
| 26 | 157314 | [脑电图区分躯体病因与精神病因紧张症的诊断准确性综述](https://doi.org/10.1016/j.eclinm.2022.101808) | 诊断试验系统综述与荟萃分析 |
| 27 | 107223 | [锂与呋塞米相互作用导致中毒的病例](https://doi.org/10.1192/j.eurpsy.2023.1464) | 病例报告及文献回顾（会议摘要） |
| 28 | 241700 | [哺乳期锂暴露与母婴结局的系统综述](https://doi.org/10.3389/fphar.2019.01005) | 系统综述 |
| 29 | 88037 | [分裂型人格障碍向精神病性障碍的转归](https://doi.org/10.1111/eip.12396) | 随机对照试验亚组结果（会议摘要） |
| 30 | 50653 | [精神科多饮的诊断标准与严重程度量表开发](https://doi.org/10.1016/j.euroneuro.2019.09.634) | 系统文献回顾与专家Delphi共识（会议摘要） |
| 31 | 252351 | [共同决策及生活质量、自尊等量表结局](https://doi.org/10.7759/cureus.87069) | 系统综述 |
| 32 | 190928 | [童年创伤、物质使用与精神分裂症谱系障碍](https://doi.org/10.1080/20008198.2020.1748342) | 系统综述 |
| 33 | 177523 | [MDMA辅助心理治疗的二期随机试验](https://doi.org/10.1016/s2215-0366(18)30135-4) | 二期随机双盲剂量反应临床试验 |
| 34 | 128282 | [ACP成人抑郁障碍急性期治疗指南](https://doi.org/10.7326/l23-0246) | 临床指南 |
| 35 | 130960 | [用量表结果调整抗抑郁治疗的随机试验](https://doi.org/10.1001/jamanetworkopen.2025.29427) | 随机对照临床试验 |
| 36 | 242894 | [初级保健中的自杀风险评估及处理综述](https://doi.org/10.3389/fpsyt.2024.1440738) | 系统综述 |
| 37 | 164994 | [电休克相关认知损害及美金刚、褪黑素对照](https://doi.org/10.1016/j.jocn.2020.02.011) | 随机对照临床试验 |
| 38 | 145588 | [合并射血分数降低心衰的中枢性睡眠呼吸暂停治疗](https://doi.org/10.1007/s11325-021-02512-y) | 网络荟萃分析 |
| 39 | 167942 | [精神共病与帕金森病不良结局的系统综述](https://doi.org/10.1016/j.lanepe.2024.100870) | 系统综述与荟萃分析 |
| 40 | 95596 | [脑深部刺激后的认知安全监测](https://doi.org/10.1159/000520618) | 系统综述与病例系列 |

## 实体类型核对

| 类型 | 新增文章index | 摘要原文片段 |
|---|---:|---|
| Disease | 107246 | malignant catatonia |
| Symptom | 107223 | sleepy, disoriented |
| Diagnostic Criterion | 50653 | the following 5 items were chosen to be included in the diagnostic criteria |
| Assessment | 54260 | systematically assessed through a series of yes/no questions |
| Patient | 107223 | 73 year-old man |
| Medication | 107223 | lithium-furosemide interaction |
| Treatment | 164994 | electroconvulsive therapy (ECT) |
| Treatment Plan | 177523 | MDMA plus psychotherapy |
| Examination | 157314 | electroencephalogram (EEG) |
| Assessment Scale | 252351 | World Health Organization Quality-of-Life Scale Abbreviated Version (WHOQOL-BREF) |
| Etiology | 190928 | genetic susceptibility |
| Risk | 54260 | suicidality |
| Communication Strategy | 54297 | avoidance of confrontation |
| Guideline | 98091 | CANMAT 2023 updated guidelines |
| Evidence | 54297 | Eastwood, S., Bisson, J.I. Management of factitious disorders: a systematic review. |
| Assessment Dimension | 252351 | quality of life |

## 关系逐行核对

Excel行号指新版“关系表”的真实行号，包含第1行表头。引文和具体端点见coverage.json；此处列核对结论。

| Excel行 | 起点 | Relation | 当前Target | 状态 | index | 说明 |
|---:|---|---|---|---|---:|---|
| 2 | Disease | `subtype_of` | Disease | 明确候选 | 107246 | 原文明示亚型。 |
| 3 | Disease | `differentiates_from` | Disease | 明确候选 | 107246 | 须保留文章给出的鉴别依据，不将两种诊断合并。 |
| 4 | Disease | `co_occurs_with` | Disease | 明确候选 | 167942 | 精神共病背景明确；不是把所有疾病并列提及当作共病。 |
| 5 | Disease | `predisposes_to` | Disease | 明确候选 | 88037 | 结论为初步结果及风险提示，不能改写成确定因果。 |
| 6 | Disease | `progresses_to` | Disease | 明确候选 | 88037 | 明确有基线疾病和随访诊断转归；仅为初步亚组分析。 |
| 7 | Disease | `relapses_to` | Disease | 需确认 | 705 | 原20篇有复发结局，但原文目标是躁狂症状；不能直接将Symptom改为Disease来满足relapses_to。疾病到疾病的定义需医学同学确认。 |
| 8 | Disease | `associated_with_poor_prognosis` | Disease | 明确候选 | 167942 | 是预后标志的关联；原文明确因果关系不清楚。 |
| 9 | Disease | `associated_with_risk` | Risk | 明确候选 | 57744 | 保留未治疗、妊娠期等限定。 |
| 10 | Disease | `commonly_affects` | Patient | 明确候选 | 57744 | 人群型Patient实例；不是根据试验入组年龄反推易感人群。 |
| 11 | Diagnostic Criterion | `required_for` | Disease | 明确候选 | 54297 | 诊断要求明示；节点可保留该要求的描述，不虚构criterion编号。 |
| 12 | Symptom | `is_symptom_of` | Disease | 明确候选 | 107246 | 病例中的症状与诊断联系。 |
| 13 | Symptom | `supports_Diagnostic Criterion_of` | Diagnostic Criterion | 明确候选 | 50653 | 专家共识拟定的标准；不能称为已充分验证的诊断金标准。 |
| 14 | Symptom | `suggests` | Disease | 需确认 | 107246 | 提示依赖复合症状时序；是否允许将这一条件整体作为Symptom节点需确认，不能把任一单症状视为特异性提示。 |
| 15 | Symptom | `argues_against` | Disease | 明确候选 | 107246 | 反对某诊断的证据，不等同于完全排除；必须保留停药后持续时间。 |
| 16 | Symptom | `precedes` | Symptom | 明确候选 | 107246 | 明示症状先后；只描述此病例。 |
| 17 | Symptom | `follows` | Symptom | 明确候选 | 107246 | 与precedes为同一证据的反向表达；覆盖数不代表独立研究数。 |
| 18 | Symptom | `relieved_by` | Medication / Treatment / Treatment Plan | 明确候选 | 164994 | 保留比较对象和作者谨慎措辞；不将褪黑素也标为有效。 |
| 19 | Symptom | `has_subsymptom` | Symptom | 需确认 | 107246 | 有症状并列及复合表现，但with不必然证明上位/下位症状；待确认has_subsymptom语义。 |
| 20 | Assessment | `assesses_for` | Disease / Symptom / Risk | 明确候选 | 54260 | 问诊过程作为Assessment，不将量表名称混作Assessment。 |
| 21 | Assessment | `asks_about` | Symptom | 明确候选 | 54260 | 具体问诊内容，不是把任何临床随访都当成询问症状。 |
| 22 | Assessment | `triggers_follow_up_question` | Assessment | 缺口 | — | 本次选文摘要未找到由某次问诊回答触发具体追问的明确链条；定期随访不等同于触发追问。 |
| 23 | Assessment | `triggers_scale` | Assessment Scale | 明确候选 | 57744 | 保留原摘要中Personalized Health Questionnaire-9的写法，不擅改原文；Assessment节点表示识别担忧的评估过程。 |
| 24 | Assessment | `triggers_examination` | Examination | 缺口 | — | 有检查、评估及病例工作流程，但未找到由某一Assessment明确触发某项Examination的摘要证据；不从发生顺序推断触发。 |
| 25 | Assessment | `informed_by_patient` | Patient | 明确候选 | 57744 | Patient为带病史的患者/人群，不将病史本身创建为新实体类型。 |
| 26 | Patient | `presents_with` | Symptom | 明确候选 | 107223 | 个案观察，不外推到所有服锂患者。 |
| 27 | Patient | `has_risk` | Risk | 明确候选 | 54260 | 当前自杀相关风险与既往自杀企图均有情境。 |
| 28 | Patient | `recommended` | Medication / Treatment / Treatment Plan | 明确候选 | 128282 | Patient人群实例；必须保留急性期、严重程度及条件推荐。 |
| 29 | Patient | `contraindicated_for` | Medication / Treatment / Treatment Plan | 明确候选 | 241700 | 与contraindicated_in为同一证据的反向表达；这是2019文献背景陈述，不代表当前用药指南，结论仍强调证据质量有限。 |
| 30 | Medication | `therapeutically_indicated_for` | Symptom / Disease | 明确候选 | 131854 | 原20篇；不能把联合口服药的获批背景改写为本文单药方案已经获批。 |
| 31 | Medication | `investigational_treatment_for` | Symptom / Disease | 明确候选 | 177523 | 二期试验语境；药物是辅助心理治疗使用，不据阳性结果宣称已形成临床适应证。 |
| 32 | Medication | `contraindicated_in` | Disease / Patient / Symptom | 明确候选 | 241700 | 保持2019年文章的背景和证据局限，不能作为现行临床建议。 |
| 33 | Medication | `interacts_with` | Medication | 明确候选 | 107223 | 两种具体药物和相互作用事件均明示。 |
| 34 | Medication | `causes_side_effect` | Symptom / Disease | 明确候选 | 107246 | 病例不耐受，不能推算发生率。 |
| 35 | Medication | `requires_monitoring_of` | Examination / Symptom / Risk | 明确候选 | 107223 | 原文明示监测要求。 |
| 36 | Treatment | `combined_with` | Treatment / Medication | 明确候选 | 177523 | 该关系从Treatment指向Medication，不从Medication擅造combined_with。 |
| 37 | Treatment | `therapeutically_indicated_for` | Symptom / Disease | 明确候选 | 128282 | 临床推荐与研究探索性使用分开。 |
| 38 | Treatment | `investigational_treatment_for` | Symptom / Disease | 需确认 | 95596 | 摘要称有效并汇总RCT，但没有明确将DBS定为试验性；不能只因为有RCT就标investigational_treatment_for。当前不计明确覆盖。 |
| 39 | Treatment | `contraindicated_in` | Disease / Patient / Symptom | 明确候选 | 145588 | 明确禁忌和特定合并病情；来自最终KEEP池中的睡眠医学文章。 |
| 40 | Treatment | `causes_side_effect` | Symptom / Disease | 明确候选 | 164994 | 非药物治疗相关不良作用；不能将无药物不良反应退出等同于无认知不良作用。 |
| 41 | Treatment | `requires_monitoring_of` | Examination / Symptom / Risk | 明确候选 | 95596 | 监测的是潜在认知副作用；不表示本文已经证实认知损害。 |
| 42 | Treatment Plan | `consists_of_medication` | Medication | 明确候选 | 177523 | 与consists_of_treatment共用方案组成证据。 |
| 43 | Treatment Plan | `consists_of_treatment` | Treatment | 明确候选 | 177523 | 明确药物辅助心理治疗的组成。 |
| 44 | Treatment Plan | `therapeutically_indicated_for` | Symptom / Disease | 明确候选 | 128282 | 保留条件推荐和低确定性证据。 |
| 45 | Treatment Plan | `investigational_treatment_for` | Symptom / Disease | 明确候选 | 177523 | 整体方案的二期试验，不将效果结果提升为临床推荐。 |
| 46 | Treatment Plan | `contraindicated_in` | Disease / Patient / Symptom | 缺口 | — | 找到单药及非药物治疗禁忌，但当前选文未有清楚针对整个Treatment Plan的禁忌；不将单药禁忌自动传播给任意含该药方案。 |
| 47 | Treatment Plan | `causes_side_effect` | Symptom / Disease | 明确候选 | 131836 | 原20篇；报告的是治疗期间不良事件，保留比较组，不能据此认定每一事件均为确定药物因果。 |
| 48 | Treatment Plan | `requires_monitoring_of` | Examination / Symptom / Risk | 明确候选 | 177523 | 整个试验方案的安全监测，不表示监测到的所有项目都是已发生副作用。 |
| 49 | Examination | `supports_diagnosis_of` | Disease | 明确候选 | 157314 | 支持躯体病因紧张症的鉴别，非单凭EEG确诊；必须保留该疾病亚型及诊断不确定性。 |
| 50 | Examination | `differentiates` | Disease | 明确候选 | 157314 | 原文的直接用途是病因鉴别，应结合其他检查。 |
| 51 | Assessment Scale | `evaluates` | Symptom / Disease | 明确候选 | 50653 | 多饮在精神科语境可作症状；若团队将其独立疾病化，需统一标签。 |
| 52 | Assessment Scale | `measures` | Assessment Dimension | 明确候选 | 252351 | 量表测量抽象维度；不再用旧measures连接Disease或Symptom。 |
| 53 | Etiology | `contributes_to` | Disease / Risk / Symptom | 明确候选 | 190928 | 保留may/suggest及多因素语境，不把童年创伤标为充分原因。 |
| 54 | Risk | `requires_action` | Treatment Plan / Treatment / Medication | 明确候选 | 242894 | 风险管理策略及个体化方案，不能把风险本身等同于精神疾病诊断。 |
| 55 | Communication Strategy | `recommended_for` | Disease / Patient | 明确候选 | 98091 | Communication统一使用节点表中的Communication Strategy。 |
| 56 | Communication Strategy | `avoid_with` | Disease / Patient | 明确候选 | 54297 | 病例中使用的策略，原文同时说明该障碍的管理证据有限。 |
| 57 | Guideline | `recommends` | Medication / Treatment / Treatment Plan / Assessment / Examination / Assessment Scale / Communication Strategy | 明确候选 | 128282 | 其他指南及推荐对象也在选文中；一行覆盖不代表全部Target分支都覆盖。 |
| 58 | Guideline | `based_on` | Evidence | 需确认 | 128282 | 依托证据的文字很明确，但摘要没有命名该系统综述或给出PMID/DOI；是否允许匿名证据集合节点需团队确认，当前不计明确覆盖。 |
| 59 | Guideline | `updated_from` | Guideline | 明确候选 | 98091 | 新版指向旧版；不是任意两份不同组织指南之间的更新关系。 |
| 60 | Evidence | `recommended_by` | Guideline | 需确认 | 128282 | 与based_on为同一信息的逆向候选；摘要未给具体文献身份，且需按中文“被指南引用”解释recommended_by，不能理解为指南推荐一篇文章用于治疗。 |
| 61 | Assessment Dimension | `associated_with` | Disease | 明确候选 | 252351 | 疾病相关的抽象功能/情绪维度，不将所有心理词汇自动视为具体症状。 |

## 旧标注使用情况

以下是结构上的schema兼容统计，不是医学正确率；没有自动把废弃关系映射为新关系。

| 标注人 | 节点 | 关系 | 新版不再允许的关系 | 已弃用属性实例 |
|---|---:|---:|---:|---:|
| DHY | 186 | 146 | 66 | 0 |
| 尤雅 | 165 | 124 | 46 | 0 |
| 标注员 | 156 | 142 | 58 | 54 |

三份旧标注合并，按原代码与实际端点直接匹配新版，只使用了60行中的15行；旧图谱出现13类节点。这个数字不包括将旧代码重新解释为新版代码的推测。

## 验证

- `python benchmarks/tools/kg_annotation/build_page.py` 重建单文件页面。
- `node --check benchmarks/tools/kg_annotation/app.js` 及内嵌脚本语法检查。
- `node benchmarks/tools/kg_annotation/test_compatibility.cjs`：用三份真实文件检查所有节点、属性、关系代码、端点、证据及备注的导入/导出；检查measures新旧端点区别、旧浏览器行键、姓名隔离及新增文章空白状态。
- 页面静态核对：40篇、16类实体、60行新版关系，旧版82行保留；无外部脚本、样式或加载资源，HTML ID唯一；所有覆盖引文是所引用摘要的连续原文片段。
- 未进行浏览器界面和鼠标交互测试；以上数据兼容测试在Node VM中运行，不等同于浏览器端测试。
