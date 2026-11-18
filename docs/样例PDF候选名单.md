# 工艺知识库样例资料候选名单（PDF 与开放网页）

> 调研日期：2026-11-18。用于 Process-craft-rag 的解析、混合检索、引用溯源和人工评估测试，不作为真实生产指导。

## 1. 筛选口径与结论

本名单中的“开放”指具有 Creative Commons 许可、明确的公有领域声明或官方再利用说明，而不只是能够公开下载。优先级同时考虑：

1. 与机械加工、工艺规划、材料、检验、质量或安全的相关性。
2. PDF 是否已有可提取文本层，能否保留正文和页码。
3. 许可是否清楚，是否允许在教学、研究和系统演示中使用及保留来源。
4. 多份资料组合后能否覆盖不同文档类型和题型。

本轮共保留 9 份 PDF 候选：

- **A 级 7 份**：已核验 PDF 可下载、正文可提取，并找到较明确的开放许可或公有领域依据，可优先选择。
- **B 级 2 份**：已核验 PDF 可下载、正文可提取，但只确认“批准公开发布”，再分发和改编许可仍需复核。

目前 A/B 级 PDF 候选均为英文，能够测试英文文档解析及中文问题的跨语检索，但**不能替代中文工艺 PDF**；正式评估仍需补充至少 1 份获授权的中文文本型资料。第 7—8 节补充了中文开放网页及非 PDF 资料，可作为后续 HTML 数据源候选，但不改变首轮 PDF 验收范围。

## 2. A 级：优先候选

| 编号 | 文档 | 主要内容 | 语言/规模 | 许可依据 | 文本核验与注意事项 |
| --- | --- | --- | --- | --- | --- |
| A1 | [Manufacturing Processes 4-5](https://openoregon.pressbooks.pub/manufacturingprocesses45/open/download?type=pdf) | 铣床、车床、钻床、带锯、平面磨床、热处理、硬度测试、CNC；含操作步骤、转速进给和安全规则 | 英文；长篇，目录正文至 227 页以后 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，第三方内容例外；[教材介绍](https://open.umn.edu/opentextbooks/textbooks/645) | 已提取目录、正文和页码。与加工指令最匹配，适合作为核心工艺文档；需保留各章来源及例外声明 |
| A2 | [SPC and Lean Manufacturing](https://pressbooks.palni.org/spcleanmanufacturing/open/download?type=pdf) | 精益生产、质量工具、统计过程控制、过程稳定性与过程能力、控制图 | 英文；约 90 页 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，第三方内容例外；[书籍主页](https://pressbooks.palni.org/spcleanmanufacturing/) | 已提取正文和页码。适合质量与工艺综合题；部分 H5P 交互内容在 PDF 中缺失，可测试空内容处理 |
| A3 | [OSHA 3170: Safeguarding Equipment and Protecting Employees from Amputations](https://osha.gov/sites/default/files/publications/OSHA3170.pdf) | 机械危险、防护装置、上锁挂牌，以及钻床、铣床、磨床等设备的专项安全措施 | 英文；约 60 页 | PDF 明确声明公有领域，可复制且无需许可，建议署名 | 已提取正文、表格文字和页码。适合作为独立安全规范来源；内容是美国安全指南，不代替当地法规 |
| A4 | [NIST AMS 400-1: On-Machine Measurement Use Cases and Information for Machining Operations](https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.400-1.pdf) | 机内测量、加工前/中/后测量、刀具和工件校准、夹具测量、过程监控、SPC 与质量追溯 | 英文；69 页 | NIST 出版物通常为美国公有领域，需署名；[出版页](https://www.nist.gov/publications/machine-measurement-use-cases-and-information-machining-operations-0) | 已提取正文、目录和页码。篇幅适合首次迭代，步骤和术语丰富；图示较多，应抽查跨页文本 |
| A5 | [NISTIR 7734: A Machining and Measurement Process Planning Activity Model for Manufacturing System Interoperability Analysis](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7734.pdf) | 加工与测量工艺规划活动模型、信息输入输出、工艺数据交换和互操作 | 英文；56 页 | NIST 出版物通常为美国公有领域，需署名；[出版页](https://www.nist.gov/publications/machining-and-measurement-process-planning-activity-model-manufacturing-system) | 本地 PyMuPDF 实测 56 页、提取约 5.2 万字符，38 页含较多文本；其余多为模型图，适合图文混排和页码溯源测试 |
| A6 | [NISTIR 8127: End-to-End Quality Information Framework (QIF) Technology Survey](https://nvlpubs.nist.gov/nistpubs/ir/2016/NIST.IR.8127.pdf) | 尺寸与几何公差、测量不确定度、检验规划、质量结果和 QIF 信息模型 | 英文；正文约 25 页 | NIST 出版物通常为美国公有领域，需署名；[出版页](https://www.nist.gov/publications/end-end-quality-information-framework-qif-technology-survey) | 已提取正文和页码。适合短文档冒烟测试；部分第三方图片标注“Used with Permission”，不要脱离原许可单独再利用 |
| A7 | [Introduction to Mechanical Design and Manufacturing](https://uark.pressbooks.pub/mechanicaldesign/open/download?type=pdf) | 机械设计、可制造性设计、GD&T、配合与公差、铸造、成形、机加工、连接和塑料工艺 | 英文；长篇 | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)，第三方内容例外；[书籍主页](https://uark.pressbooks.pub/mechanicaldesign/) | 已提取正文和页码。覆盖面广，适合设计与制造综合题；含非商业限制，企业或商业部署前须确认使用边界 |

NIST 的通用许可依据见 [NIST Research Library FAQ](https://www.nist.gov/nist-research-library/library-faqs)：NIST 出版物一般在美国属于公有领域，复制无需许可，但应注明来源。第三方图片、表格或引文仍应逐项保留原有权利声明。

## 3. B 级：公开发布，许可待复核

| 编号 | 文档 | 主要内容 | 文本核验 | 使用限制与建议 |
| --- | --- | --- | --- | --- |
| B1 | [DOE-HDBK-1016/1-93: Engineering Symbology, Prints, and Drawings, Volume 1](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1016-93_VOL1.pdf) | 工程图标题栏、修订记录、比例、尺寸、公差、流程图和制造图基础 | 已提取正文、页码和图表文字 | PDF 仅明确“Approved for public release; distribution is unlimited”，不能直接视为开放许可。作为图纸理解候选，确认再利用条款后再纳入开放演示包 |
| B2 | [DOE-HDBK-1017/1-93: Material Science, Volume 1](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1017-93_VOL1.pdf) | 金属结构、晶体与合金、材料性能、缺陷、304 不锈钢等工程材料 | 已提取正文、表格和页码 | 同样只确认公开发布。资料较早且有历史 OCR 错字，适合清洗与引用核查测试；核实许可前不作为默认开放语料 |

## 4. 推荐使用组合

### 4.1 第一次迭代：单文档链路

优先选择 **A4 NIST AMS 400-1**：

- 69 页，符合首轮“100 页以内文本型 PDF”的验证范围。
- 同时包含定义、操作活动、测量要求、设备与工艺术语，可设计事实抽取、流程和引用题。
- NIST 来源稳定，出版信息和再利用依据较清楚。

若更重视加工操作和参数表达，可选择 **A1 Manufacturing Processes 4-5**，但其篇幅较长，首次联调应记录完整入库耗时，不宜只挑少量有利页面。若制作开放许可允许的章节节选，必须保存原书署名、章节范围、原页码与派生文件说明。

### 4.2 多文档端到端演示

建议先采用以下 4 份，覆盖不同来源和内容类型：

1. **A1 Manufacturing Processes 4-5**：加工步骤、设备、转速进给和操作安全。
2. **A4 NIST AMS 400-1**：机内测量、校准、检验与质量追溯。
3. **A3 OSHA 3170**：独立安全规范，用于跨文档安全综合题。
4. **A2 SPC and Lean Manufacturing**：质量控制、SPC 和精益生产。

可构造的评估题包括：

- 单文档事实抽取：某设备的组成、操作目的或测量术语。
- 精确术语与数值：刀具偏置、公差、测量类型和工艺参数。
- 跨页流程：加工前准备、加工中测量、加工后检验。
- 多文档综合：结合加工教材与 OSHA 资料回答某工序的质量和安全注意事项。
- 无答案问题：询问资料未提供的具体零件图号、公差或企业内部设备条件，验证拒答。

### 4.3 后续扩展

- 加入 **A5 NISTIR 7734**，测试图示较多、部分页面文本稀疏的文档。
- 加入 **A7 Introduction to Mechanical Design and Manufacturing**，扩展设计、公差和制造工艺综合题；仅限符合非商业许可的场景。
- 中文资料到位后，建立中文单文档、中文跨文档及中英混合三组测试，分别报告结果，不与英文语料指标混为一谈。

## 5. 下载、入库与署名要求

选定文件后，应在数据清单中记录：

- 文档 ID、标题、作者/机构、原始来源页和 PDF 直链。
- 获取日期、许可名称、许可原文位置及第三方内容例外。
- 文件 SHA-256、文件大小、PDF 物理页数、语言、文本页比例和解析器版本。
- 是否节选或转换；若有，记录派生过程及原页码映射。
- 计划覆盖的题型、关联测试题和已知解析问题。

其他要求：

1. 不把候选名单等同于自动获得批量再分发权；公开演示包只纳入许可已确认的文件。
2. CC 许可资料保留作者、来源、许可链接及修改说明；`CC BY-NC` 不用于未经授权的商业场景。
3. 对 NIST 资料使用建议署名：“Reprinted courtesy of the National Institute of Standards and Technology, U.S. Department of Commerce. Not copyrightable in the United States.”
4. 原始 PDF 与清洗文本分开保存；引用页码始终使用 PDF 物理页码，不用提取文本的页脚编号代替。
5. 安全和工艺资料可能过时或只适用于特定地区、设备与教学场景；系统输出必须继续保留人工审核提示。
6. 不将来源不明的“免费电子书”、无许可课程资料或搜索引擎抓到的 PDF 纳入候选。

## 6. 核验方法与暂未纳入项

- 文本核验通过直接读取 PDF 导出内容进行，检查标题、目录、连续正文及页码是否可提取；NISTIR 7734 另使用本地 PyMuPDF 对全部页面统计。
- 2026-11-18 再次逐项请求下载地址：A1—A7、B1—B2 均重新取得 PDF 正文；A3 改用不带 `www` 的 OSHA 官方地址后可下载。Support for CNC 的 PDF 导出持续返回 HTTP 500，已从 PDF 候选删除，仅保留可正常获取的 N2 HTML 版本。
- 本次未将全部候选 PDF 保存进仓库，临时下载文件仅用于验证，避免在选定前引入大文件和许可不明的副本。
- MIT OpenCourseWare 的部分制造课程资料可作后续线索，但搜索到的部分讲义明确标注“内容不包含在 Creative Commons 许可内”，因此未直接列入 A 级。
- DOE 两份手册只确认公开发布，不将“政府网站发布”自动解释为公有领域。
- 候选链接可能更新；正式下载时应再次检查 HTTP 状态、文件类型、许可页和 SHA-256，不能只依赖本名单中的历史核验结果。


## 7. 中文资料补充调研

### 7.1 结论

本轮找到了许可明确的中文开放课程和中文 HTML 技术文档，但**尚未找到同时满足“中文、工艺相关、PDF 文本层可用、开放许可明确”四项条件的优选 PDF**。因此，中文检索测试可以先用开放 HTML 补充，中文 PDF 仍建议通过校内课程资料授权、企业脱敏资料授权或项目自编并经工艺人员审核的样例解决。

大陆高校公开课程、文档分享网站和政府网站上的资料数量较多，但“公开访问”通常不等于允许批量抓取、再分发或改编，不能直接放入开放演示包。

### 7.2 已找到的中文开放资料

| 编号 | 资料与形式 | 内容与文本可用性 | 许可 | 推荐程度与限制 |
| --- | --- | --- | --- | --- |
| ZH1 | [LinuxCNC 中文 HTML 文档](https://www.linuxcnc.org/docs/master/html/zh_CN/index.html) | 数控加工中心、车床、坐标系、刀具补偿、G/M/O 代码、HAL 和机床配置；中文目录和大量正文可提取，但部分页面仍为英文 | [GNU FDL 1.1 或更高版本](https://www.linuxcnc.org/docs/master/html/zh_CN/common/overleaf.html)，英文许可文本为准 | **优先用于中文 CNC 术语、代码和精确检索测试**。当前中文入口对应 2.10 预发布文档，入库须固定版本和抓取日期，并标记未翻译页面 |
| ZH2 | [臺大開放式課程：機械製造](https://ocw.aca.ntu.edu.tw/courses/101S211)，HTML、视频及讲义资源 | 楊宏智教授，21 讲；覆盖铸造、成形、金属切削、材料去除、磨削与光整、连接、塑料和复合材料。课程说明为繁体中文，讲次标题含英文 | [CC BY-NC-SA 3.0 台湾](https://creativecommons.org/licenses/by-nc-sa/3.0/tw/)，另有注明者除外；[版权声明](https://ocw.aca.ntu.edu.tw/about/copyright) | **适合中文制造术语和课程大纲，暂不作为完整中文正文库**。资源下载页本次返回 403，讲义须另行下载并核对文件级许可；非商业及相同方式共享要求必须保留 |
| ZH3 | 中文维基百科条目：[切削加工](https://zh.wikipedia.org/zh-cn/%E5%88%87%E5%89%8A%E5%8A%A0%E5%B7%A5)、[铣床](https://zh.wikipedia.org/zh-cn/%E9%93%A3%E5%BA%8A)、[钻孔](https://zh.wikipedia.org/zh-cn/%E9%92%BB%E5%AD%94)、[放电加工](https://zh.wikipedia.org/zh-cn/%E6%94%BE%E9%9B%BB%E5%8A%A0%E5%B7%A5) | 简体中文 HTML，含定义、工艺分类、部分精度和表面粗糙度数据及参考文献 | CC BY-SA 4.0，附加条款及图片许可另计 | **仅用于中文分词、语义召回和引用格式冒烟测试**。内容可编辑且深度不一，关键参数须回查条目参考文献，不作为高可信工艺依据 |

ZH1 的英文 stable 2.9 中文入口仍有较多未翻译内容，master 中文版本翻译较多但属于预发布文档。实际使用时应保存静态快照、上游版本、原文 URL、段落语言和 SHA-256，不能在一次评估运行中自动跟随上游更新。

### 7.3 中文公开资料中暂不纳入的项目

| 资料 | 发现的问题 | 当前结论 |
| --- | --- | --- |
| [西北工业大学《机械制造基础》—中国大学 MOOC](https://www.icourse163.org/learn/NWPU-1001813005) | 简体中文大纲完整，覆盖材料、成形、切削、机床、结构工艺性和工艺规程，但页面未发现 CC 或其他允许批量再利用的许可 | 可作人工学习和寻找授权对象的线索，不自动抓取课程附件、视频或题库，不进入开放演示包 |
| [清华大学开放式课程《生产计划与管制》](https://ocw.nthu.edu.tw/courses/136?lang=cn) | 繁体中文课程大纲可读取，内容覆盖 MRP、排程、产能和精益生产；检索到的讲义带“©Copyright 林則孟”，原 PDF 直链本次又返回 404 | 不按开放 PDF 处理；只有取得对应讲义明确授权后才入库 |
| [《机械制造企业安全生产标准化规范》—应急管理部](https://www.mem.gov.cn/gk/gwgg/agwzlfl/gg_01/201306/W020171101558475662856.pdf) | 官方公开 PDF，但未找到开放许可；实际文本提取出现大面积乱码和替换字符 | 不用于当前文本型 PDF 主链路。若后续确有需要，先确认许可，再作为 OCR/编码修复专项样本 |
| FreeCAD CAM 中文 Wiki | 搜索可见中文 CAM 工作台、刀具路径和 G-code 内容，但许可页及正文本次受到反自动化验证阻挡 | 暂列为线索，不标记为已核验开放资源；待人工浏览确认许可、版本和正文后再评估 |
| 百度文库、文档之家、CSDN、来源不明毕业设计及商业教材扫描件 | 授权主体和文件来源不清，常含第三方教材或论文 | 不下载、不入库、不进入候选演示包 |

### 7.4 中文资料的落地建议

1. **短期中文功能验证**：选取 ZH1 的坐标系、刀具补偿和车床章节，配合 ZH3 少量条目，验证中文分词、型号保留、中英文混合查询和引用定位。
2. **正式中文 PDF 验证**：优先向课程教师、实验中心或企业资料所有者申请书面授权，明确允许解析、向量化、展示原文片段及是否允许随演示包再分发。
3. **必要时自编样例**：可编写轴类、套筒类等虚拟零件的中文工艺规程，由工艺人员审核后采用项目选择的开放许可发布；必须标记为“项目自编样例”，不能冒充真实企业文档或与外部真实资料混合报告指标。
4. **分开报告结果**：简体中文、繁体中文、英文和中英混合语料分别统计解析成功率、召回和引用质量，避免中文语料不足时只报告英文结果。

## 8. 开放的非 PDF 资料

### 8.1 英文开放 HTML 候选

以下来源均有稳定的章节 HTML，可作为 PDF 之外的独立数据适配器输入，也能在 PDF 导出不可用时替代同一教材的网页版本。

| 编号 | 资料 | 许可与状态 | 已核验内容 | 推荐用途 |
| --- | --- | --- | --- | --- |
| N1 | [Manufacturing Processes 4-5 — Pressbooks HTML](https://openoregon.pressbooks.pub/manufacturingprocesses45/) | CC BY 4.0，第三方内容例外 | [Speeds, Feeds, and Tapping](https://openoregon.pressbooks.pub/manufacturingprocesses45/chapter/unit-two-cutting-speed/) 可提取操作步骤、参数表、公式和单元测试题 | 与 A1 同源，适合测试 HTML 标题层级、表格和步骤分块；不要将 PDF 与 HTML 版本当成两份不同知识重复入库 |
| N2 | [Support for CNC — Pressbooks HTML](https://mhcc.pressbooks.pub/supportcnc/) | CC BY 4.0，第三方内容例外；2026-03-25 已归档，不再更新 | [G54—G59 坐标系](https://mhcc.pressbooks.pub/supportcnc/chapter/g54-g59-an-introduction/) 可提取正文、代码、图片署名和补充练习 | **优先的 HTML 适配器样本**。归档版本较稳定，适合 CNC 精确代码、工件坐标系和刀具偏置查询；PDF 导出不可用，因此仅保留可获取的 HTML 版本 |
| N3 | [SPC and Lean Manufacturing — Pressbooks HTML](https://pressbooks.palni.org/spcleanmanufacturing/) | CC BY 4.0，第三方内容例外 | 章节含定义、公式、质量工具、SPC 和 H5P 占位内容 | 与 A2 同源，适合测试交互元素过滤、公式与质量控制内容分块 |
| N4 | [Introduction to Mechanical Design and Manufacturing — Pressbooks HTML](https://uark.pressbooks.pub/mechanicaldesign/) | CC BY-NC 4.0，第三方内容例外 | 设计、GD&T、公差、铸造、成形、机加工和连接章节可按标题提取 | 非商业场景下扩展设计与制造综合题；与 A7 同源，需去重 |

ZH1 LinuxCNC、ZH2 台大开放课程和 ZH3 中文维基条目同样属于非 PDF 候选，不重复编号。

### 8.2 HTML 入库与引用规则

非 PDF 资料不能套用“PDF 物理页码”的引用模型，建议增加以下来源字段：

- `source_type = html`、原始 URL、页面标题、站点/作者、许可、语言和抓取时间。
- 上游版本或归档状态、页面最后更新时间（若有）、内容 SHA-256 和采集器版本。
- 章节标题路径、HTML 锚点、段落/列表/表格序号和原文片段。
- 对代码块、表格、公式和步骤列表保留结构，不把导航栏、 cookie 提示、分享按钮和脚本当成正文。

引用展示可使用“文档名 + 章节 + 标题锚点 + 原文片段”，打开来源时定位到对应 URL 锚点；**不得虚构页码**。如果同时保存了原始 HTML 快照，应在历史引用中记录快照版本，避免上游修改后无法复查。

采集时还应遵守以下边界：

1. 优先使用作者提供的整书导出、公开 API 或明确的章节清单，不无限制递归抓取整个网站。
2. 固定允许抓取的域名和路径，遵守网站使用条款、robots 约束和访问频率限制。
3. 视频页面只有标题或简介时，只能把这些文字作为正文；视频转写、字幕授权和 ASR 是独立扩展，不默认纳入。
4. 同一作品的 PDF、HTML 和其他格式通过作品内容标识及来源关系去重，评估时只选一个主版本，防止重复块抬高召回。
5. HTML 解析属于可选扩展，不应阻塞 I1 的 PDF 核心链路；可在核心闭环稳定后，用 N2 和 ZH1 各做一条真实端到端适配器验证。

### 8.3 更新后的推荐顺序

1. **I1 主验收不变**：继续使用 A4 NIST AMS 400-1 完成文本型 PDF 核心链路。
2. **中文检索预验证**：在检索单元测试中加入 ZH1 和 ZH3 的固定快照，不必等待 HTML 产品功能全部完成。
3. **HTML 适配器验证**：核心 PDF 链路稳定后，优先选择 N2 Support for CNC，再增加 ZH1 LinuxCNC，分别验证英文和中文网页的解析、分块、检索与引用。
4. **正式中文 PDF 仍单列任务**：继续寻找授权资料，不用开放网页的存在宣称中文 PDF 需求已经满足。
