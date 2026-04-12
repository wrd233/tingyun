# Report Output Terms

本文件用于统一术语；当前定义以 [final-deliverable-and-report-expression.md](/Users/wangrundong/work/mywork/docs/reporting/final-deliverable-and-report-expression.md) 与 [adapter-design-and-intermediate-artifacts.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-design-and-intermediate-artifacts.md) 为准。

仓库中的报告相关术语统一如下：

1. `pack`
   - adapter 返回的结构化对象
2. `writer input`
   - 面向写作者或模型的单入口写作输入
3. `export view`
   - pack 中声明的固定导出视图
4. `materialized report pack`
   - client 将 export view 物化到本地目录后的结果
5. `sample bundle`
   - 长期保留的样例报告包
6. `final report`
   - 最终交付给人的报告正文

这些术语表示不同层次的对象，不应互相替代。
