# 开题调研与 UML 概要设计

## 1. 调研结论

### 1.1 工艺知识数字化需求

工艺规划连接设计信息与制造执行，涉及加工方法、设备、工装、参数、测量及质量要求。NISTIR 7734 通过活动模型分析加工与测量工艺规划中的数据交换，说明工艺知识具有多环节、多来源和强上下文特征[1]。国内《“十四五”智能制造发展规划》强调以工艺、装备为核心，以数据为基础，构建知识驱动的智能制造系统[2]。因此，本项目不把目标简化为通用聊天，而是围绕企业文档建立可检索、可核查的工艺知识服务。

### 1.2 RAG 技术进展

Lewis 等提出的 RAG 将参数化语言模型与非参数化检索记忆结合，为知识更新和来源追踪提供了基础路径[3]。后续综述将 RAG 归纳为由朴素检索—生成向高级检索优化、模块化编排演进，并强调检索、生成与评估的协同[4]。这说明工程重点不只是接入大模型 API，还包括文档处理、检索质量、上下文组织和可复现评估。

稠密检索利用向量语义匹配提高同义表达和跨语言查询的召回能力[5]；BM25 保留术语、型号、数值等词法匹配优势[6]。RRF 按不同检索结果中的排名进行融合，避免直接比较异构分数[7]。重排序进一步对较小候选集进行精细相关性判断，但会增加时延，需通过候选规模和阈值控制成本。

### 1.3 现有方案的不足与本项目切入点

通用大模型无法自动获得企业内部工艺知识，且回答来源难核查；单一向量检索容易遗漏精确术语或型号；只返回检索片段又不能形成连续问答与结构化加工指令。项目采用“PDF 页级解析—稠密与稀疏混合召回—RRF 融合—重排序—受控生成—引用校验”的完整链路，以人工审核和证据不足拒答作为工艺安全边界。

## 2. 需求摘要

系统用户包括工艺人员、知识库管理员和评估人员。P0 功能包括：

1. PDF 上传、校验、异步解析、分块、索引、状态查询、失败重试与删除。
2. 稠密与 BM25 双路召回、RRF 融合、重排序和上下文预算控制。
3. 知识问答、加工指令草案、多轮问题改写及历史隔离。
4. 文档名、页码和原文片段组成的引用快照及原文定位。
5. 多文档测试集、检索诊断、人工评分和结果导出。

核心约束：仅 READY 文档参与检索；引用必须来自实际注入的上下文；缺失材料、公差或设备信息时标为“待确认”；输出仅供工艺人员审核，不直接生成机床控制指令。

## 3. 概要设计

系统采用前后端分离的单体后端和单后台 Worker，避免在轻量项目中引入微服务复杂度。表现层使用 Vue 3；服务层使用 FastAPI；SQLite 保存权威元数据；Qdrant 保存向量索引；BM25 保存词法索引；本地受控目录保存 PDF；大模型通过服务端 API 调用。

离线索引与在线问答解耦。离线索引在暂存版本中完成解析、嵌入和两路索引构建，通过一致性校验后原子发布。在线问答固定活动版本，完成问题改写、双路召回、融合、重排序、受控生成和引用快照保存。

## 4. UML 模型

- [系统用例图](uml/01-系统用例图.puml)：描述角色、系统边界及 include 关系。
- [系统构件图](uml/02-系统构件图.puml)：描述分层构件、依赖及基础设施。
- [核心领域类图](uml/03-核心领域类图.puml)：描述类属性、职责、关联和多重性。
- [在线问答时序图](uml/04-在线问答时序图.puml)：描述对象交互顺序、并行召回与备选路径。
- [文档处理活动图](uml/05-文档处理活动图.puml)：描述活动、决策、并行索引与终止状态。

## 5. 可行性验证计划

采用迭代式开发：先打通单文档端到端链路，再扩展多文档与评估。准备不少于 3 份授权文本型 PDF 和不少于 30 道测试题，对比仅稠密、仅 BM25、混合召回和混合召回加重排序四种配置。软件测试与人工评估分离，人工从正确性、完整性、引用正确性、表达和多轮一致性按 0–2 分评分；建议目标为有效回答率不低于 80%、引用可核查率 100%、无依据关键参数率 0。

## 参考文献

[1] Zhao F, Proctor F M, Horst J A. A Machining and Measurement Process Planning Activity Model for Manufacturing System Interoperability Analysis: NISTIR 7734[R]. NIST, 2010. https://www.nist.gov/publications/machining-and-measurement-process-planning-activity-model-manufacturing-system

[2] 工业和信息化部等八部门. “十四五”智能制造发展规划[Z]. 2021. https://wap.miit.gov.cn/jgsj/ghs/zlygh/art/2022/art_c201cab037444d5c94921a53614332f9.html

[3] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]. NeurIPS, 2020: 9459–9474. https://arxiv.org/abs/2005.11401

[4] Gao Y, Xiong Y, Gao X, et al. Retrieval-Augmented Generation for Large Language Models: A Survey[J]. arXiv:2312.10997, 2023. https://arxiv.org/abs/2312.10997

[5] Karpukhin V, Oguz B, Min S, et al. Dense Passage Retrieval for Open-Domain Question Answering[C]. EMNLP, 2020: 6769–6781. https://aclanthology.org/2020.emnlp-main.550/

[6] Robertson S, Zaragoza H. The Probabilistic Relevance Framework: BM25 and Beyond[J]. Foundations and Trends in Information Retrieval, 2009, 3(4): 333–389.

[7] Cormack G V, Clarke C L A, Buettcher S. Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods[C]. SIGIR, 2009: 758–759. https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf

[8] Chen J, Xiao S, Zhang P, et al. BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation[C]. Findings of ACL, 2024: 2318–2335. https://arxiv.org/abs/2402.03216
