# Reports

`reports/` 与同级 `diagnostics/` 属于同一个诊断批次。

这里不保存新的重型输入包，而是为该批次下的不同报告类型建立各自的实例目录。每个实例直接读取同级 `../diagnostics/` 下已经存在的诊断资产。

当前实例：

- `legal_diagnostic_report/`
  - 法务系统巡检与排查类 LaTeX 报告实例
