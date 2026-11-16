# 测试汇总

已记录 6140 / 6140 个任务；包含失败结果，完成不等于通过。完整参数见 plan.json，环境见 environment.json。

三档 CPU、三个版本和各次重复在同一份报告中分组，不混合统计。下表性能数值为中位数 [最小值, 最大值]；summary.csv 保留每次结果，cases.csv 保留样本数、范围及状态计数。

吞吐只计测量窗口内的首次成功回复，p99 仅针对成功请求；非成功回复及收尾缺决定包含收尾观察。没有成功样本时 p99 留空，不填零；缺决定不直接等于永久失败。

| 测试组 | 已完成 / 计划 | passed | measured | 其他结果 |
| --- | ---: | ---: | ---: | ---: |
| native | 20 / 20 | 19 | 0 | 1 |
| correctness | 1080 / 1080 | 1065 | 0 | 15 |
| performance | 4545 / 4545 | 0 | 4545 | 0 |
| history | 495 / 495 | 105 | 360 | 30 |

## native

| 场景 | CPU | 版本 | 完成 / 计划；状态次数 | 吞吐（条/秒） | 成功 p99（毫秒） | 非成功回复（条） | 收尾缺决定（条） |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| forge-known-history-regressions | native | v003 | 5/5; passed=5 | — | — | — | — |
| original-suites | native | baseline | 5/5; passed=5 | — | — | — | — |
| original-suites | native | v000 | 5/5; passed=5 | — | — | — | — |
| original-suites | native | v003 | 5/5; observed_failure=1, passed=4 | — | — | — | — |

## correctness

| 场景 | CPU | 版本 | 完成 / 计划；状态次数 | 吞吐（条/秒） | 成功 p99（毫秒） | 非成功回复（条） | 收尾缺决定（条） |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| cancellation | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| cancellation | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| cancellation | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| cancellation | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| cancellation | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| cancellation | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| cancellation | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| cancellation | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| cancellation | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| concurrent_history | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| coordinator-crash | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-1 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-1 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-1 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-1 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-1 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-1 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-1 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-1 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-1 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-3 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-3 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-3 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-3 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-3 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-3 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-3 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-3 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-3 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-4 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-4 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-4 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-4 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-4 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-4 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| crash-4 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| crash-4 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| crash-4 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| duplicates | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| duplicates | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| duplicates | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| duplicates | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| duplicates | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| duplicates | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| duplicates | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| duplicates | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| duplicates | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| finite_loss | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| finite_loss | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| finite_loss | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| finite_loss | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| finite_loss | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| finite_loss | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| finite_loss | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| finite_loss | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| finite_loss | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| invalid_input | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| invalid_input | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| invalid_input | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| invalid_input | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| invalid_input | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| invalid_input | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| invalid_input | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| invalid_input | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| invalid_input | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s17 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s3 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| jitter-s91 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s17 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s3 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-balanced-s91 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s17 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s3 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-random-s91 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s17 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s3 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| mixed-single-s91 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| no-quorum | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| no-quorum | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| no-quorum | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| no-quorum | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| no-quorum | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| no-quorum | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| no-quorum | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| no-quorum | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| no-quorum | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| overload | 1c1t-g1 | baseline | 5/5; observed_failure=5 | — | — | — | — |
| overload | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| overload | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| overload | 2c2t-g2 | baseline | 5/5; observed_failure=5 | — | — | — | — |
| overload | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| overload | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| overload | 2c4t-g4 | baseline | 5/5; observed_failure=5 | — | — | — | — |
| overload | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| overload | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| semantics | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| semantics | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| semantics | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| semantics | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| semantics | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| semantics | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| semantics | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| semantics | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| semantics | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |

## performance

| 场景 | CPU | 版本 | 完成 / 计划；状态次数 | 吞吐（条/秒） | 成功 p99（毫秒） | 非成功回复（条） | 收尾缺决定（条） |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| crash-1-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 296.17 [293.66, 307.30] | 348.14 [312.80, 362.84] | 0 | 0 |
| crash-1-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,064.30 [1,055.43, 1,082.53] | 149.19 [141.32, 155.89] | 0 | 0 |
| crash-1-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,026.27 [986.50, 1,037.60] | 166.54 [161.20, 204.03] | 0 | 0 |
| crash-1-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 192.53 [191.10, 194.53] | 393.32 [384.85, 398.83] | 0 | 0 |
| crash-1-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,359.02 [1,341.36, 1,366.99] | 115.91 [101.43, 118.00] | 0 | 0 |
| crash-1-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,337.63 [1,315.76, 1,352.53] | 143.33 [126.26, 148.20] | 0 | 0 |
| crash-1-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 102.67 [101.93, 104.07] | 705.48 [696.35, 716.49] | 0 | 0 |
| crash-1-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,341.43 [2,263.30, 2,420.41] | 73.03 [58.51, 82.60] | 0 | 0 |
| crash-1-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,265.66 [2,236.49, 2,361.49] | 79.57 [71.35, 85.51] | 0 | 0 |
| crash-1-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 414.43 [411.86, 415.76] | 211.66 [209.37, 213.54] | 0 | 0 |
| crash-1-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,063.76 [1,053.00, 1,088.82] | 148.78 [142.70, 153.14] | 0 | 0 |
| crash-1-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,024.90 [1,016.40, 1,057.33] | 160.36 [154.51, 172.31] | 0 | 0 |
| crash-1-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 584.35 [582.93, 595.46] | 147.49 [143.09, 150.92] | 0 | 0 |
| crash-1-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,357.22 [1,355.43, 1,362.03] | 108.59 [106.23, 115.03] | 0 | 0 |
| crash-1-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,332.69 [1,292.09, 1,355.56] | 147.22 [132.98, 158.66] | 0 | 0 |
| crash-1-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 912.63 [903.93, 914.69] | 100.05 [99.50, 100.72] | 0 | 0 |
| crash-1-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,315.73 [2,245.03, 2,375.08] | 75.51 [60.46, 79.31] | 0 | 0 |
| crash-1-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,310.86 [2,218.46, 2,316.39] | 68.31 [55.98, 81.32] | 0 | 0 |
| crash-2-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 253.29 [248.09, 256.43] | 296.73 [285.66, 310.09] | 0 | 0 |
| crash-2-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 231.09 [227.63, 231.13] | 314.73 [313.90, 316.76] | 0 | 0 |
| crash-2-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 251.76 [251.72, 253.53] | 278.27 [275.61, 278.61] | 0 | 0 |
| crash-2-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 149.16 [77.97, 185.97] | 3,452.10 [437.06, 4,181.68] | 0 | 0 |
| crash-2-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 231.13 [231.13, 231.13] | 311.58 [311.23, 311.87] | 0 | 0 |
| crash-2-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 261.60 [251.76, 275.20] | 266.85 [265.50, 272.49] | 0 | 0 |
| crash-2-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 12.07 [11.30, 12.57] | 8,047.02 [7,878.83, 8,143.19] | 0 | 0 |
| crash-2-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 229.93 [226.60, 231.13] | 309.33 [309.17, 311.63] | 0 | 0 |
| crash-2-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 273.07 [253.86, 277.36] | 263.57 [261.69, 266.98] | 0 | 0 |
| crash-2-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 267.17 [264.76, 267.60] | 271.42 [269.73, 279.12] | 0 | 0 |
| crash-2-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 229.89 [229.13, 231.13] | 316.45 [315.74, 317.95] | 0 | 0 |
| crash-2-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 252.40 [251.72, 253.73] | 282.74 [281.88, 284.56] | 0 | 0 |
| crash-2-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 271.23 [269.53, 271.96] | 270.41 [261.21, 278.62] | 0 | 0 |
| crash-2-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 231.13 [215.49, 231.13] | 312.97 [311.59, 314.45] | 0 | 0 |
| crash-2-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 268.83 [251.83, 279.53] | 274.35 [273.60, 278.04] | 0 | 0 |
| crash-2-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 272.06 [270.76, 272.37] | 256.35 [252.20, 257.43] | 0 | 0 |
| crash-2-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 231.13 [229.49, 231.30] | 311.02 [310.91, 311.31] | 0 | 0 |
| crash-2-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 268.13 [251.73, 275.20] | 268.31 [266.67, 269.26] | 0 | 0 |
| crash-4-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 120.23 [115.20, 123.07] | 600.13 [587.96, 601.44] | 0 | 0 |
| crash-4-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 119.60 [119.53, 120.57] | 611.89 [610.02, 624.44] | 0 | 0 |
| crash-4-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 125.86 [125.86, 125.86] | 533.64 [530.27, 535.81] | 0 | 0 |
| crash-4-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 15.07 [14.93, 16.20] | 6,096.83 [6,036.82, 6,548.32] | 0 | 0 |
| crash-4-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 119.53 [118.10, 120.10] | 622.25 [615.83, 629.04] | 0 | 0 |
| crash-4-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 125.86 [125.86, 125.87] | 533.12 [531.87, 537.65] | 0 | 0 |
| crash-4-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 6.47 [6.40, 6.63] | 12,229.60 [12,006.36, 12,523.67] | 0 | 0 |
| crash-4-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 119.60 [119.50, 121.66] | 623.54 [611.77, 629.58] | 0 | 0 |
| crash-4-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 125.87 [125.86, 125.87] | 518.74 [516.58, 520.02] | 0 | 0 |
| crash-4-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 129.23 [126.73, 130.36] | 555.49 [540.70, 567.73] | 0 | 0 |
| crash-4-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 121.20 [119.46, 121.60] | 625.79 [613.44, 631.72] | 0 | 0 |
| crash-4-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 125.86 [125.86, 125.86] | 546.14 [536.33, 546.79] | 0 | 0 |
| crash-4-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 133.86 [133.03, 135.40] | 523.84 [519.22, 541.55] | 0 | 0 |
| crash-4-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 119.50 [118.40, 119.76] | 620.70 [614.85, 626.45] | 0 | 0 |
| crash-4-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 125.86 [125.86, 125.87] | 540.02 [537.44, 542.48] | 0 | 0 |
| crash-4-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 135.30 [134.33, 135.83] | 506.39 [505.14, 509.97] | 0 | 0 |
| crash-4-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 119.53 [119.43, 119.67] | 618.65 [613.56, 629.17] | 0 | 0 |
| crash-4-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 125.86 [125.86, 125.87] | 523.55 [522.37, 523.83] | 0 | 0 |
| hot-balanced-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 0.00 [0.00, 0.03] | 6.91 [6.91, 6.91] | 587 | 320 |
| hot-balanced-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 2.13 [0.07, 3.23] | 363.70 [30.37, 377.26] | 1961 | 315 |
| hot-balanced-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 54.56 [41.40, 128.36] | 12,640.85 [5,702.54, 14,911.79] | 1780 | 19 |
| hot-balanced-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 34.40 [21.60, 43.83] | 14,431.26 [14,292.79, 14,717.77] | 1127 | 0 |
| hot-balanced-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 0.03 [0.03, 0.10] | 33.35 [4.07, 14,436.52] | 2324 | 179 |
| hot-balanced-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 130.87 [71.83, 162.86] | 12,673.31 [8,143.71, 14,601.06] | 832 | 0 |
| hot-balanced-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 154.96 [135.27, 173.20] | 2,948.93 [1,856.89, 7,597.32] | 0 | 0 |
| hot-balanced-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 0.07 [0.00, 0.23] | 256.79 [4.74, 335.59] | 1667 | 291 |
| hot-balanced-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 85.67 [17.77, 93.77] | 13,093.93 [4,092.82, 14,907.52] | 2064 | 1 |
| hot-balanced-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 2.20 [2.17, 2.60] | 1,665.79 [580.82, 8,255.26] | 667 | 305 |
| hot-balanced-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 0.03 [0.03, 2.17] | 33.80 [4.00, 380.68] | 2012 | 233 |
| hot-balanced-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 73.90 [23.90, 143.33] | 7,347.66 [4,600.19, 14,330.42] | 2056 | 7 |
| hot-balanced-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 311.39 [300.23, 320.63] | 368.33 [348.72, 376.82] | 0 | 0 |
| hot-balanced-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 17.83 [14.97, 30.93] | 14,798.01 [13,256.69, 14,878.60] | 1247 | 0 |
| hot-balanced-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 152.03 [104.26, 217.80] | 11,803.67 [3,457.63, 14,467.21] | 402 | 0 |
| hot-balanced-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 296.03 [292.59, 305.00] | 314.08 [306.66, 328.22] | 0 | 0 |
| hot-balanced-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 0.10 [0.00, 9.80] | 262.91 [5.47, 3,408.14] | 2264 | 189 |
| hot-balanced-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 103.77 [31.10, 153.66] | 11,460.87 [6,961.95, 14,596.10] | 803 | 0 |
| hot-random-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 0.03 [0.00, 2.20] | 1,237.83 [10.29, 2,847.36] | 594 | 312 |
| hot-random-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 0.17 [0.03, 2.20] | 357.81 [4.37, 415.33] | 1934 | 267 |
| hot-random-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 56.00 [21.33, 191.39] | 7,989.55 [372.13, 14,603.70] | 2422 | 31 |
| hot-random-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 21.20 [19.10, 32.50] | 14,224.74 [13,816.51, 14,811.49] | 1251 | 0 |
| hot-random-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 0.20 [0.17, 2.27] | 317.88 [263.41, 413.23] | 2286 | 147 |
| hot-random-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 169.86 [63.03, 198.40] | 11,124.71 [3,908.82, 14,553.34] | 653 | 0 |
| hot-random-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 136.36 [133.26, 136.50] | 6,679.89 [5,415.42, 7,279.55] | 0 | 0 |
| hot-random-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 0.10 [0.03, 4.40] | 248.38 [3.77, 744.10] | 1788 | 305 |
| hot-random-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 53.77 [26.93, 101.66] | 12,994.95 [10,312.44, 14,807.25] | 1149 | 0 |
| hot-random-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 2.17 [0.03, 2.20] | 812.77 [5.30, 2,191.34] | 683 | 299 |
| hot-random-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 2.13 [0.07, 2.17] | 352.35 [27.86, 373.26] | 2051 | 234 |
| hot-random-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 32.83 [22.93, 105.56] | 13,596.76 [9,768.46, 14,795.14] | 2159 | 0 |
| hot-random-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 316.46 [307.87, 321.53] | 322.90 [301.75, 346.09] | 0 | 0 |
| hot-random-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 34.80 [29.43, 39.23] | 14,696.01 [13,325.83, 14,851.44] | 262 | 0 |
| hot-random-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 161.20 [98.56, 206.10] | 10,816.25 [3,104.67, 13,434.43] | 393 | 0 |
| hot-random-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 334.77 [325.80, 344.43] | 305.74 [293.96, 326.57] | 0 | 0 |
| hot-random-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 0.03 [0.03, 10.80] | 32.16 [4.80, 7,507.18] | 2358 | 125 |
| hot-random-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 78.26 [42.63, 160.83] | 10,738.54 [3,580.57, 14,931.75] | 1156 | 0 |
| hot-single-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 3.57 [1.40, 3.60] | 12,825.68 [742.95, 13,184.83] | 518 | 115 |
| hot-single-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 438.00 [408.17, 445.97] | 193.39 [169.29, 205.68] | 0 | 0 |
| hot-single-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 227.59 [139.67, 264.49] | 607.46 [517.60, 1,047.67] | 0 | 0 |
| hot-single-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 7.13 [3.87, 9.40] | 14,532.66 [8,579.73, 14,823.72] | 206 | 44 |
| hot-single-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 765.76 [760.86, 773.11] | 118.83 [113.95, 121.39] | 0 | 0 |
| hot-single-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 726.59 [713.60, 734.12] | 125.86 [123.89, 132.43] | 0 | 0 |
| hot-single-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 3.50 [2.33, 3.53] | 13,188.90 [10,200.96, 14,756.03] | 427 | 0 |
| hot-single-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,030.83 [1,027.83, 1,031.79] | 84.32 [83.95, 85.35] | 0 | 0 |
| hot-single-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,013.20 [1,011.53, 1,014.59] | 85.52 [84.85, 86.04] | 0 | 0 |
| hot-single-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 5.27 [3.20, 7.60] | 14,113.33 [3,708.98, 14,646.55] | 769 | 38 |
| hot-single-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 437.46 [429.75, 443.16] | 190.85 [181.40, 195.76] | 0 | 0 |
| hot-single-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 250.43 [196.00, 284.80] | 948.37 [529.37, 1,179.50] | 0 | 0 |
| hot-single-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 112.10 [105.03, 112.40] | 2,197.80 [2,078.79, 2,902.30] | 0 | 0 |
| hot-single-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 772.33 [763.83, 784.83] | 119.25 [117.65, 133.92] | 0 | 0 |
| hot-single-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 724.00 [691.23, 743.25] | 125.85 [121.23, 139.07] | 0 | 0 |
| hot-single-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 84.13 [82.00, 93.93] | 3,827.26 [1,331.48, 5,597.28] | 0 | 0 |
| hot-single-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,025.10 [1,023.13, 1,025.63] | 88.68 [87.34, 108.89] | 0 | 0 |
| hot-single-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,008.30 [1,001.43, 1,012.93] | 88.68 [87.43, 91.60] | 0 | 0 |
| independent-balanced-n1-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 89.30 [87.06, 92.03] | 17.16 [16.39, 17.50] | 0 | 0 |
| independent-balanced-n1-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 571.53 [569.40, 585.23] | 3.83 [3.71, 3.90] | 0 | 0 |
| independent-balanced-n1-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 524.93 [524.23, 536.53] | 4.15 [4.09, 4.39] | 0 | 0 |
| independent-balanced-n1-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 93.36 [89.43, 100.67] | 16.05 [15.67, 16.85] | 0 | 0 |
| independent-balanced-n1-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 701.70 [682.49, 727.66] | 2.90 [2.72, 2.98] | 0 | 0 |
| independent-balanced-n1-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 617.30 [608.54, 679.70] | 3.25 [3.02, 3.39] | 0 | 0 |
| independent-balanced-n1-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 87.13 [87.07, 87.60] | 16.27 [15.88, 16.29] | 0 | 0 |
| independent-balanced-n1-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 447.36 [444.03, 451.43] | 3.60 [3.55, 3.72] | 0 | 0 |
| independent-balanced-n1-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 425.65 [423.46, 431.07] | 3.82 [3.68, 3.90] | 0 | 0 |
| independent-balanced-n1-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 88.26 [87.13, 97.00] | 16.47 [15.84, 17.34] | 0 | 0 |
| independent-balanced-n1-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 577.39 [572.10, 585.35] | 3.82 [3.69, 3.89] | 0 | 0 |
| independent-balanced-n1-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 517.73 [511.83, 534.06] | 4.32 [4.27, 4.37] | 0 | 0 |
| independent-balanced-n1-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 107.23 [95.73, 112.17] | 14.36 [14.15, 14.68] | 0 | 0 |
| independent-balanced-n1-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 659.50 [647.37, 742.03] | 3.08 [2.75, 3.21] | 0 | 0 |
| independent-balanced-n1-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 683.20 [662.30, 688.46] | 3.05 [2.99, 3.08] | 0 | 0 |
| independent-balanced-n1-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 99.60 [87.57, 114.70] | 13.97 [13.71, 15.26] | 0 | 0 |
| independent-balanced-n1-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 459.85 [455.86, 485.66] | 3.73 [3.51, 3.77] | 0 | 0 |
| independent-balanced-n1-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 436.69 [436.10, 445.33] | 3.94 [3.86, 4.04] | 0 | 0 |
| independent-balanced-n1-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 88.10 [87.10, 98.47] | 16.55 [16.17, 17.25] | 0 | 0 |
| independent-balanced-n1-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 574.46 [565.59, 591.30] | 3.85 [3.60, 3.99] | 0 | 0 |
| independent-balanced-n1-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 516.53 [494.99, 523.43] | 4.47 [4.29, 4.60] | 0 | 0 |
| independent-balanced-n1-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 108.46 [97.17, 114.53] | 14.08 [13.71, 14.26] | 0 | 0 |
| independent-balanced-n1-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 655.80 [647.16, 734.16] | 3.21 [2.86, 3.27] | 0 | 0 |
| independent-balanced-n1-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 678.90 [646.96, 691.50] | 3.07 [2.96, 3.14] | 0 | 0 |
| independent-balanced-n1-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 115.67 [99.96, 116.46] | 13.33 [12.77, 13.65] | 0 | 0 |
| independent-balanced-n1-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 455.39 [442.93, 459.60] | 3.79 [3.70, 3.93] | 0 | 0 |
| independent-balanced-n1-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 433.46 [427.56, 434.07] | 4.02 [3.87, 4.06] | 0 | 0 |
| independent-balanced-n1-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 86.77 [86.36, 93.27] | 18.31 [17.92, 18.42] | 0 | 0 |
| independent-balanced-n1-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 575.03 [560.13, 589.89] | 3.91 [3.75, 3.99] | 0 | 0 |
| independent-balanced-n1-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 492.86 [486.13, 522.13] | 4.68 [4.48, 4.88] | 0 | 0 |
| independent-balanced-n1-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 108.16 [99.00, 111.90] | 14.28 [14.03, 14.47] | 0 | 0 |
| independent-balanced-n1-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 642.53 [628.79, 657.23] | 3.25 [3.24, 3.42] | 0 | 0 |
| independent-balanced-n1-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 671.90 [615.63, 700.02] | 3.15 [3.03, 3.57] | 0 | 0 |
| independent-balanced-n1-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 102.60 [99.80, 116.40] | 13.51 [13.33, 13.77] | 0 | 0 |
| independent-balanced-n1-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 452.03 [444.96, 457.36] | 3.81 [3.75, 4.06] | 0 | 0 |
| independent-balanced-n1-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 432.66 [430.90, 436.15] | 4.03 [3.98, 4.10] | 0 | 0 |
| independent-balanced-n16-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 445.39 [440.66, 450.85] | 175.41 [139.22, 202.92] | 0 | 0 |
| independent-balanced-n16-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,191.63 [1,159.56, 1,229.30] | 73.84 [62.55, 76.58] | 0 | 0 |
| independent-balanced-n16-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,143.70 [1,128.44, 1,162.46] | 76.91 [67.46, 80.11] | 0 | 0 |
| independent-balanced-n16-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 264.63 [251.23, 274.96] | 377.84 [360.72, 391.86] | 0 | 0 |
| independent-balanced-n16-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,477.38 [1,473.43, 1,495.20] | 34.84 [33.71, 36.29] | 0 | 0 |
| independent-balanced-n16-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,471.43 [1,464.23, 1,482.89] | 34.10 [32.24, 35.53] | 0 | 0 |
| independent-balanced-n16-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 159.13 [155.90, 167.93] | 686.70 [679.58, 691.13] | 0 | 0 |
| independent-balanced-n16-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,507.04 [2,379.52, 2,612.91] | 21.73 [19.64, 40.82] | 0 | 0 |
| independent-balanced-n16-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,496.74 [2,442.02, 2,603.32] | 24.16 [14.71, 39.64] | 0 | 0 |
| independent-balanced-n16-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 599.76 [586.99, 602.31] | 97.18 [69.85, 102.65] | 0 | 0 |
| independent-balanced-n16-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,205.13 [1,134.43, 1,250.00] | 66.74 [56.48, 82.62] | 0 | 0 |
| independent-balanced-n16-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,125.02 [1,098.30, 1,176.28] | 75.86 [68.81, 83.26] | 0 | 0 |
| independent-balanced-n16-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 723.90 [708.76, 732.85] | 48.56 [45.02, 49.87] | 0 | 0 |
| independent-balanced-n16-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,508.46 [1,503.30, 1,512.96] | 35.02 [32.99, 36.69] | 0 | 0 |
| independent-balanced-n16-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,482.29 [1,475.26, 1,484.77] | 36.15 [33.64, 39.59] | 0 | 0 |
| independent-balanced-n16-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 904.83 [867.67, 927.46] | 51.79 [31.58, 72.39] | 0 | 0 |
| independent-balanced-n16-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,540.66 [2,348.93, 2,552.39] | 26.43 [20.28, 43.45] | 0 | 0 |
| independent-balanced-n16-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,440.40 [2,353.92, 2,573.99] | 24.29 [17.08, 38.94] | 0 | 0 |
| independent-balanced-n16-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 616.66 [612.35, 620.03] | 66.59 [65.04, 72.22] | 0 | 0 |
| independent-balanced-n16-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,197.60 [1,184.96, 1,230.26] | 59.80 [56.01, 75.15] | 0 | 0 |
| independent-balanced-n16-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,145.10 [1,115.03, 1,199.96] | 75.46 [69.02, 80.07] | 0 | 0 |
| independent-balanced-n16-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 833.53 [827.06, 843.65] | 43.13 [40.60, 45.83] | 0 | 0 |
| independent-balanced-n16-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,505.99 [1,486.29, 1,511.62] | 35.61 [32.94, 37.53] | 0 | 0 |
| independent-balanced-n16-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,482.26 [1,463.49, 1,487.19] | 35.89 [34.97, 36.80] | 0 | 0 |
| independent-balanced-n16-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 1,235.00 [1,233.13, 1,251.06] | 28.88 [28.23, 30.87] | 0 | 0 |
| independent-balanced-n16-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,448.79 [2,418.89, 2,501.86] | 40.90 [23.68, 41.64] | 0 | 0 |
| independent-balanced-n16-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,424.95 [2,404.00, 2,551.05] | 25.53 [18.57, 42.82] | 0 | 0 |
| independent-balanced-n16-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 621.03 [608.59, 633.22] | 66.42 [65.16, 69.81] | 0 | 0 |
| independent-balanced-n16-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,162.09 [1,156.79, 1,204.80] | 70.75 [69.20, 80.09] | 0 | 0 |
| independent-balanced-n16-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,118.32 [1,098.63, 1,163.80] | 76.99 [62.64, 80.46] | 0 | 0 |
| independent-balanced-n16-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 931.95 [926.58, 933.83] | 40.78 [39.62, 42.18] | 0 | 0 |
| independent-balanced-n16-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,505.39 [1,493.56, 1,508.06] | 36.10 [33.93, 39.16] | 0 | 0 |
| independent-balanced-n16-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,476.43 [1,467.29, 1,484.76] | 35.99 [33.67, 40.06] | 0 | 0 |
| independent-balanced-n16-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 1,297.26 [1,292.53, 1,313.60] | 34.61 [33.46, 36.54] | 0 | 0 |
| independent-balanced-n16-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,493.55 [2,393.71, 2,627.59] | 25.63 [16.05, 38.43] | 0 | 0 |
| independent-balanced-n16-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,430.16 [2,326.35, 2,433.63] | 42.31 [26.28, 43.18] | 0 | 0 |
| independent-balanced-n256-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 11.43 [11.07, 11.90] | 14,292.72 [14,247.00, 14,811.60] | 1713 | 1279 |
| independent-balanced-n256-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 553.75 [478.76, 581.83] | 1,929.99 [1,603.47, 4,799.27] | 0 | 0 |
| independent-balanced-n256-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 214.23 [196.53, 218.46] | 12,769.52 [11,244.71, 14,130.79] | 738 | 0 |
| independent-balanced-n256-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 16.13 [15.70, 16.40] | 14,206.33 [13,931.58, 14,565.26] | 1770 | 881 |
| independent-balanced-n256-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,071.00 [838.10, 1,209.83] | 1,159.92 [920.52, 1,692.18] | 0 | 0 |
| independent-balanced-n256-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 719.60 [674.96, 737.56] | 842.90 [784.02, 1,609.13] | 0 | 0 |
| independent-balanced-n256-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 13.73 [13.50, 13.83] | 14,446.37 [13,891.15, 14,499.79] | 1497 | 712 |
| independent-balanced-n256-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,956.73 [1,938.46, 1,958.46] | 957.22 [908.27, 992.51] | 0 | 0 |
| independent-balanced-n256-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,640.96 [1,607.66, 1,816.69] | 984.56 [709.10, 1,662.37] | 0 | 0 |
| independent-balanced-n256-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 24.27 [23.83, 25.13] | 14,545.16 [14,292.92, 14,679.24] | 810 | 0 |
| independent-balanced-n256-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 544.76 [525.59, 555.13] | 2,545.03 [2,027.24, 4,350.13] | 0 | 0 |
| independent-balanced-n256-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 187.19 [153.93, 207.33] | 12,696.04 [9,521.37, 14,104.61] | 1106 | 0 |
| independent-balanced-n256-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 83.40 [70.67, 91.56] | 12,665.57 [12,006.79, 14,004.55] | 600 | 0 |
| independent-balanced-n256-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,013.00 [772.80, 1,039.16] | 1,410.81 [744.99, 1,438.03] | 0 | 0 |
| independent-balanced-n256-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 726.70 [710.43, 737.73] | 872.13 [819.08, 1,389.86] | 0 | 0 |
| independent-balanced-n256-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 49.03 [43.70, 54.77] | 12,157.97 [7,968.55, 12,817.50] | 746 | 19 |
| independent-balanced-n256-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,940.43 [1,890.42, 1,970.66] | 934.15 [887.94, 1,008.32] | 0 | 0 |
| independent-balanced-n256-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,088.03 [1,060.40, 1,621.66] | 784.58 [724.15, 813.97] | 0 | 0 |
| independent-balanced-n256-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 37.97 [37.00, 39.63] | 12,590.49 [11,650.80, 13,386.85] | 582 | 0 |
| independent-balanced-n256-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 507.06 [496.16, 565.95] | 2,899.10 [2,396.24, 4,568.30] | 0 | 0 |
| independent-balanced-n256-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 210.80 [188.00, 264.02] | 12,433.99 [9,538.17, 14,243.58] | 258 | 0 |
| independent-balanced-n256-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 144.06 [139.46, 154.37] | 10,492.66 [10,250.01, 10,723.80] | 334 | 0 |
| independent-balanced-n256-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 841.98 [767.62, 1,204.52] | 1,230.48 [748.95, 2,199.99] | 0 | 0 |
| independent-balanced-n256-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 730.45 [705.56, 739.63] | 876.34 [833.28, 1,498.19] | 0 | 0 |
| independent-balanced-n256-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 149.40 [101.03, 180.33] | 12,251.68 [11,839.07, 13,725.96] | 299 | 64 |
| independent-balanced-n256-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,952.79 [1,872.38, 1,976.06] | 923.23 [893.24, 1,020.50] | 0 | 0 |
| independent-balanced-n256-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,090.80 [1,059.20, 1,802.75] | 803.08 [532.07, 1,031.75] | 0 | 0 |
| independent-balanced-n256-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 38.53 [35.70, 44.50] | 13,916.85 [11,671.21, 14,020.05] | 719 | 7 |
| independent-balanced-n256-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 510.26 [501.23, 537.52] | 2,967.70 [2,275.32, 4,520.34] | 0 | 0 |
| independent-balanced-n256-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 169.73 [148.33, 176.60] | 11,921.78 [9,422.91, 13,852.51] | 1241 | 0 |
| independent-balanced-n256-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 150.56 [90.20, 186.77] | 13,544.67 [13,219.67, 14,290.20] | 278 | 75 |
| independent-balanced-n256-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 893.03 [784.10, 1,104.48] | 1,743.89 [706.42, 2,214.69] | 0 | 0 |
| independent-balanced-n256-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 719.72 [707.43, 736.53] | 942.51 [906.32, 1,194.81] | 0 | 0 |
| independent-balanced-n256-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 95.60 [81.90, 139.06] | 13,627.65 [10,830.35, 13,986.07] | 176 | 0 |
| independent-balanced-n256-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,921.16 [1,691.39, 1,950.53] | 953.87 [890.27, 1,146.03] | 0 | 0 |
| independent-balanced-n256-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,791.33 [1,066.59, 1,803.49] | 988.15 [823.04, 1,063.51] | 0 | 0 |
| independent-balanced-n4-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 378.86 [373.69, 385.70] | 24.57 [23.71, 24.84] | 0 | 0 |
| independent-balanced-n4-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,118.60 [1,103.72, 1,184.40] | 21.01 [17.48, 21.57] | 0 | 0 |
| independent-balanced-n4-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,061.86 [1,043.60, 1,102.60] | 22.52 [21.86, 25.48] | 0 | 0 |
| independent-balanced-n4-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 253.67 [248.49, 260.76] | 26.81 [25.80, 26.98] | 0 | 0 |
| independent-balanced-n4-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,415.53 [1,403.65, 1,472.61] | 11.36 [10.99, 11.63] | 0 | 0 |
| independent-balanced-n4-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,425.98 [1,411.32, 1,442.76] | 11.48 [11.21, 11.81] | 0 | 0 |
| independent-balanced-n4-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 183.29 [182.59, 184.49] | 32.44 [31.50, 32.76] | 0 | 0 |
| independent-balanced-n4-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,109.41 [2,094.69, 2,145.12] | 5.80 [5.65, 6.22] | 0 | 0 |
| independent-balanced-n4-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,061.38 [2,045.49, 2,095.02] | 6.06 [5.35, 6.31] | 0 | 0 |
| independent-balanced-n4-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 496.20 [454.46, 503.90] | 19.24 [18.05, 20.39] | 0 | 0 |
| independent-balanced-n4-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,104.76 [1,092.80, 1,117.76] | 21.78 [20.07, 24.50] | 0 | 0 |
| independent-balanced-n4-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,084.00 [1,050.41, 1,090.39] | 22.25 [21.48, 24.67] | 0 | 0 |
| independent-balanced-n4-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 448.80 [434.22, 458.83] | 15.82 [15.42, 15.83] | 0 | 0 |
| independent-balanced-n4-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,459.76 [1,416.22, 1,482.90] | 11.38 [10.75, 12.26] | 0 | 0 |
| independent-balanced-n4-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,412.96 [1,385.39, 1,454.89] | 11.71 [11.29, 12.29] | 0 | 0 |
| independent-balanced-n4-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 421.78 [412.26, 436.36] | 15.52 [15.25, 15.65] | 0 | 0 |
| independent-balanced-n4-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,132.53 [2,087.89, 2,245.96] | 6.16 [5.70, 6.74] | 0 | 0 |
| independent-balanced-n4-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,072.73 [2,040.03, 2,088.89] | 6.27 [5.96, 6.51] | 0 | 0 |
| independent-balanced-n4-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 506.17 [403.06, 528.56] | 17.89 [17.79, 18.82] | 0 | 0 |
| independent-balanced-n4-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,114.80 [1,070.63, 1,157.66] | 21.30 [17.54, 21.99] | 0 | 0 |
| independent-balanced-n4-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,062.73 [1,010.20, 1,073.40] | 23.98 [22.45, 27.56] | 0 | 0 |
| independent-balanced-n4-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 604.90 [497.11, 637.30] | 14.07 [13.86, 15.05] | 0 | 0 |
| independent-balanced-n4-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,454.36 [1,436.89, 1,455.98] | 11.71 [11.35, 12.01] | 0 | 0 |
| independent-balanced-n4-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,426.13 [1,412.13, 1,430.96] | 11.79 [11.58, 12.29] | 0 | 0 |
| independent-balanced-n4-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 616.85 [509.10, 664.80] | 13.26 [12.36, 14.34] | 0 | 0 |
| independent-balanced-n4-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,136.46 [2,084.66, 2,141.72] | 5.76 [5.54, 6.69] | 0 | 0 |
| independent-balanced-n4-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,065.93 [2,030.19, 2,081.91] | 6.59 [5.87, 7.21] | 0 | 0 |
| independent-balanced-n4-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 444.12 [384.17, 490.93] | 22.76 [22.14, 22.90] | 0 | 0 |
| independent-balanced-n4-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,097.86 [937.76, 1,182.10] | 21.91 [16.99, 26.88] | 0 | 0 |
| independent-balanced-n4-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,051.81 [915.66, 1,073.70] | 24.70 [22.97, 25.83] | 0 | 0 |
| independent-balanced-n4-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 541.60 [506.42, 657.03] | 15.75 [14.40, 17.93] | 0 | 0 |
| independent-balanced-n4-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,447.40 [1,237.50, 1,464.30] | 11.73 [11.45, 15.72] | 0 | 0 |
| independent-balanced-n4-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,426.86 [1,322.36, 1,445.63] | 11.76 [11.28, 14.07] | 0 | 0 |
| independent-balanced-n4-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 584.36 [489.40, 670.02] | 13.93 [12.78, 15.17] | 0 | 0 |
| independent-balanced-n4-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,098.79 [2,090.36, 2,175.96] | 6.39 [5.53, 6.46] | 0 | 0 |
| independent-balanced-n4-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,057.33 [2,050.83, 2,101.74] | 6.20 [5.78, 6.94] | 0 | 0 |
| independent-balanced-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 140.40 [108.03, 165.03] | 10,210.84 [8,357.15, 10,426.84] | 0 | 0 |
| independent-balanced-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 731.26 [665.91, 824.73] | 719.32 [703.51, 878.07] | 0 | 0 |
| independent-balanced-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 403.56 [301.36, 473.39] | 2,819.41 [1,384.48, 3,838.45] | 0 | 0 |
| independent-balanced-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 160.30 [155.23, 181.50] | 3,125.50 [2,396.68, 7,141.91] | 0 | 0 |
| independent-balanced-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,489.29 [1,474.16, 1,505.16] | 127.43 [99.59, 192.27] | 0 | 0 |
| independent-balanced-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,201.83 [1,008.33, 1,260.86] | 389.20 [371.17, 478.16] | 0 | 0 |
| independent-balanced-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 106.96 [69.93, 110.90] | 1,349.22 [996.72, 9,396.84] | 0 | 0 |
| independent-balanced-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,312.90 [2,301.09, 2,327.01] | 106.30 [96.90, 190.06] | 0 | 0 |
| independent-balanced-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,237.19 [2,044.13, 2,286.61] | 180.38 [86.13, 237.36] | 0 | 0 |
| independent-balanced-n64-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 207.66 [202.76, 212.67] | 5,112.15 [4,196.13, 5,592.18] | 0 | 0 |
| independent-balanced-n64-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 728.06 [663.75, 1,130.40] | 721.74 [155.15, 831.02] | 0 | 0 |
| independent-balanced-n64-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 408.78 [387.93, 426.19] | 1,815.52 [1,635.03, 3,211.32] | 0 | 0 |
| independent-balanced-n64-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 152.27 [137.06, 190.20] | 6,077.46 [5,473.56, 6,985.68] | 0 | 0 |
| independent-balanced-n64-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,531.59 [1,399.21, 1,541.43] | 108.94 [97.79, 313.85] | 0 | 0 |
| independent-balanced-n64-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,207.73 [1,183.33, 1,240.92] | 419.02 [377.47, 470.26] | 0 | 0 |
| independent-balanced-n64-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 140.87 [121.00, 199.33] | 8,249.71 [7,757.51, 8,362.04] | 0 | 0 |
| independent-balanced-n64-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,304.89 [2,287.62, 2,332.93] | 117.46 [82.19, 200.42] | 0 | 0 |
| independent-balanced-n64-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,012.38 [1,882.25, 2,318.18] | 242.05 [124.15, 248.60] | 0 | 0 |
| independent-balanced-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 177.39 [154.93, 206.86] | 4,005.52 [3,829.67, 4,280.96] | 0 | 0 |
| independent-balanced-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 703.98 [654.59, 784.99] | 820.70 [698.83, 955.22] | 0 | 0 |
| independent-balanced-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 404.09 [300.76, 438.13] | 1,863.77 [1,570.47, 3,259.14] | 0 | 0 |
| independent-balanced-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 336.33 [313.37, 385.22] | 2,717.70 [2,221.13, 3,137.37] | 0 | 0 |
| independent-balanced-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,507.12 [1,499.36, 1,523.06] | 170.88 [116.46, 266.52] | 0 | 0 |
| independent-balanced-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,260.36 [1,089.86, 1,309.09] | 375.93 [363.22, 478.02] | 0 | 0 |
| independent-balanced-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 215.27 [181.26, 221.93] | 3,547.04 [3,512.15, 4,321.15] | 0 | 0 |
| independent-balanced-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,303.79 [2,294.44, 2,337.14] | 150.54 [82.76, 194.52] | 0 | 0 |
| independent-balanced-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,997.73 [1,891.26, 2,275.97] | 242.34 [96.71, 248.79] | 0 | 0 |
| independent-balanced-n64-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 230.17 [167.83, 279.36] | 3,623.95 [2,059.25, 11,961.16] | 32 | 0 |
| independent-balanced-n64-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 701.03 [648.92, 768.93] | 750.10 [721.08, 951.51] | 0 | 0 |
| independent-balanced-n64-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 403.19 [306.19, 433.96] | 2,863.03 [1,628.31, 4,054.57] | 0 | 0 |
| independent-balanced-n64-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 409.72 [407.46, 428.80] | 2,496.53 [2,378.32, 2,802.46] | 0 | 0 |
| independent-balanced-n64-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,489.72 [1,306.99, 1,543.89] | 121.81 [98.78, 333.99] | 0 | 0 |
| independent-balanced-n64-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,222.02 [1,194.66, 1,293.48] | 385.62 [364.96, 443.78] | 0 | 0 |
| independent-balanced-n64-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 637.00 [629.96, 661.00] | 854.09 [826.60, 863.58] | 0 | 0 |
| independent-balanced-n64-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,316.15 [2,300.09, 2,336.36] | 84.66 [78.60, 169.96] | 0 | 0 |
| independent-balanced-n64-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,255.39 [2,214.13, 2,319.32] | 150.62 [79.44, 167.65] | 0 | 0 |
| independent-random-n1-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 98.93 [97.70, 100.00] | 16.40 [15.84, 16.98] | 0 | 0 |
| independent-random-n1-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 574.63 [569.53, 579.23] | 3.79 [3.74, 3.94] | 0 | 0 |
| independent-random-n1-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 528.80 [522.76, 530.46] | 4.17 [4.13, 4.24] | 0 | 0 |
| independent-random-n1-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 100.50 [100.03, 101.10] | 15.83 [15.62, 16.27] | 0 | 0 |
| independent-random-n1-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 689.03 [670.66, 710.63] | 2.92 [2.87, 2.99] | 0 | 0 |
| independent-random-n1-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 594.45 [582.90, 626.09] | 3.32 [3.11, 3.51] | 0 | 0 |
| independent-random-n1-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 91.46 [89.53, 94.86] | 16.73 [15.96, 17.25] | 0 | 0 |
| independent-random-n1-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 468.82 [463.39, 470.02] | 3.59 [3.51, 3.69] | 0 | 0 |
| independent-random-n1-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 444.95 [441.56, 448.06] | 3.82 [3.78, 3.93] | 0 | 0 |
| independent-random-n1-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 101.70 [99.96, 108.46] | 15.36 [15.21, 15.91] | 0 | 0 |
| independent-random-n1-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 583.16 [581.23, 595.16] | 3.74 [3.71, 3.93] | 0 | 0 |
| independent-random-n1-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 534.86 [532.46, 544.86] | 4.06 [4.02, 4.17] | 0 | 0 |
| independent-random-n1-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 109.73 [108.93, 114.80] | 14.50 [14.42, 14.68] | 0 | 0 |
| independent-random-n1-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 676.06 [662.36, 711.93] | 3.02 [2.88, 3.17] | 0 | 0 |
| independent-random-n1-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 594.60 [585.23, 670.67] | 3.51 [3.06, 3.54] | 0 | 0 |
| independent-random-n1-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 110.67 [105.70, 112.03] | 14.38 [14.11, 14.59] | 0 | 0 |
| independent-random-n1-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 479.36 [473.13, 485.67] | 3.75 [3.51, 3.77] | 0 | 0 |
| independent-random-n1-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 456.22 [449.86, 461.23] | 3.92 [3.83, 3.97] | 0 | 0 |
| independent-random-n1-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 102.30 [100.93, 102.86] | 16.70 [16.42, 17.40] | 0 | 0 |
| independent-random-n1-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 579.63 [561.03, 603.86] | 3.88 [3.58, 3.98] | 0 | 0 |
| independent-random-n1-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 526.36 [513.30, 555.46] | 4.21 [4.05, 4.37] | 0 | 0 |
| independent-random-n1-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 116.33 [112.26, 120.30] | 13.83 [13.73, 14.05] | 0 | 0 |
| independent-random-n1-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 636.63 [615.80, 712.36] | 3.27 [2.91, 3.40] | 0 | 0 |
| independent-random-n1-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 628.76 [622.83, 766.86] | 3.25 [2.77, 3.35] | 0 | 0 |
| independent-random-n1-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 115.10 [112.96, 117.33] | 13.57 [13.34, 13.76] | 0 | 0 |
| independent-random-n1-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 472.06 [467.52, 477.19] | 3.84 [3.64, 3.87] | 0 | 0 |
| independent-random-n1-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 452.83 [451.22, 551.85] | 3.99 [3.54, 4.05] | 0 | 0 |
| independent-random-n1-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 94.60 [93.43, 95.23] | 18.14 [17.77, 18.73] | 0 | 0 |
| independent-random-n1-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 569.73 [555.93, 591.43] | 3.86 [3.78, 4.12] | 0 | 0 |
| independent-random-n1-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 529.83 [525.86, 531.86] | 4.28 [4.23, 4.45] | 0 | 0 |
| independent-random-n1-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 113.26 [101.36, 122.90] | 13.93 [13.75, 14.16] | 0 | 0 |
| independent-random-n1-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 632.30 [606.20, 647.06] | 3.36 [3.27, 3.42] | 0 | 0 |
| independent-random-n1-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 638.36 [635.29, 653.56] | 3.25 [3.17, 3.36] | 0 | 0 |
| independent-random-n1-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 113.36 [107.87, 119.80] | 13.54 [13.40, 13.66] | 0 | 0 |
| independent-random-n1-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 475.46 [468.93, 710.20] | 3.69 [2.83, 3.85] | 0 | 0 |
| independent-random-n1-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 453.23 [449.10, 543.40] | 4.04 [3.75, 4.14] | 0 | 0 |
| independent-random-n16-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 432.49 [430.93, 434.03] | 113.55 [88.96, 159.53] | 0 | 0 |
| independent-random-n16-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,132.16 [1,121.29, 1,175.97] | 68.41 [64.87, 75.52] | 0 | 0 |
| independent-random-n16-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,107.84 [1,095.30, 1,117.30] | 67.80 [66.23, 75.58] | 0 | 0 |
| independent-random-n16-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 314.87 [277.03, 319.16] | 157.63 [95.01, 299.28] | 0 | 0 |
| independent-random-n16-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,471.26 [1,464.76, 1,475.44] | 34.13 [32.84, 36.04] | 0 | 0 |
| independent-random-n16-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,439.88 [1,438.76, 1,450.03] | 33.27 [32.44, 35.27] | 0 | 0 |
| independent-random-n16-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 163.03 [161.50, 178.36] | 640.27 [242.03, 660.55] | 0 | 0 |
| independent-random-n16-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,401.66 [2,377.32, 2,555.43] | 25.82 [18.16, 32.30] | 0 | 0 |
| independent-random-n16-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,443.13 [2,402.02, 2,458.14] | 29.59 [19.95, 36.70] | 0 | 0 |
| independent-random-n16-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 569.99 [568.75, 578.43] | 72.57 [67.11, 83.74] | 0 | 0 |
| independent-random-n16-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,133.83 [1,119.29, 1,171.06] | 69.88 [59.79, 74.72] | 0 | 0 |
| independent-random-n16-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,108.59 [1,093.41, 1,143.56] | 75.09 [60.66, 81.36] | 0 | 0 |
| independent-random-n16-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 689.80 [658.76, 699.73] | 44.83 [44.73, 55.47] | 0 | 0 |
| independent-random-n16-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,482.33 [1,473.19, 1,483.66] | 35.37 [33.84, 36.45] | 0 | 0 |
| independent-random-n16-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,460.06 [1,448.16, 1,478.93] | 35.95 [34.27, 37.12] | 0 | 0 |
| independent-random-n16-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 863.26 [845.42, 880.90] | 33.06 [32.51, 33.08] | 0 | 0 |
| independent-random-n16-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,401.29 [2,332.29, 2,503.34] | 30.21 [20.62, 34.86] | 0 | 0 |
| independent-random-n16-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,368.46 [2,291.30, 2,443.90] | 26.55 [21.64, 39.57] | 0 | 0 |
| independent-random-n16-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 597.23 [596.30, 604.80] | 65.00 [63.65, 66.37] | 0 | 0 |
| independent-random-n16-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,149.16 [1,123.66, 1,162.86] | 74.38 [56.36, 79.14] | 0 | 0 |
| independent-random-n16-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,109.56 [1,105.97, 1,132.80] | 70.98 [68.95, 76.48] | 0 | 0 |
| independent-random-n16-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 809.52 [803.86, 815.86] | 42.14 [41.70, 44.74] | 0 | 0 |
| independent-random-n16-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,482.43 [1,470.03, 1,489.19] | 36.22 [35.09, 37.19] | 0 | 0 |
| independent-random-n16-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,462.13 [1,460.13, 1,467.29] | 35.98 [34.71, 36.45] | 0 | 0 |
| independent-random-n16-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 1,203.60 [1,200.06, 1,213.58] | 30.90 [30.37, 32.05] | 0 | 0 |
| independent-random-n16-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,408.45 [2,353.21, 2,415.73] | 32.20 [22.75, 38.66] | 0 | 0 |
| independent-random-n16-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,339.09 [2,311.02, 2,414.12] | 29.84 [21.96, 36.54] | 0 | 0 |
| independent-random-n16-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 603.05 [594.96, 616.22] | 69.26 [68.13, 70.88] | 0 | 0 |
| independent-random-n16-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,144.72 [1,133.33, 1,160.23] | 69.27 [64.30, 77.83] | 0 | 0 |
| independent-random-n16-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,107.39 [1,084.13, 1,140.05] | 73.68 [69.52, 81.15] | 0 | 0 |
| independent-random-n16-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 906.86 [895.82, 915.57] | 43.65 [40.97, 43.72] | 0 | 0 |
| independent-random-n16-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,484.73 [1,471.90, 1,493.43] | 35.50 [34.98, 36.02] | 0 | 0 |
| independent-random-n16-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,463.56 [1,455.19, 1,474.83] | 35.49 [34.77, 36.34] | 0 | 0 |
| independent-random-n16-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 1,265.99 [1,257.09, 1,270.70] | 35.83 [34.88, 36.27] | 0 | 0 |
| independent-random-n16-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,397.51 [2,315.49, 2,408.00] | 26.78 [23.23, 40.57] | 0 | 0 |
| independent-random-n16-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,366.69 [2,360.96, 2,448.22] | 25.31 [20.68, 26.46] | 0 | 0 |
| independent-random-n256-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 9.80 [9.60, 10.27] | 14,794.65 [14,688.70, 14,888.56] | 1657 | 1241 |
| independent-random-n256-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 551.96 [468.95, 595.22] | 3,810.98 [1,653.75, 5,180.44] | 0 | 0 |
| independent-random-n256-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 206.63 [158.33, 226.43] | 13,490.80 [11,745.80, 14,192.58] | 683 | 0 |
| independent-random-n256-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 15.23 [14.73, 15.93] | 14,584.90 [13,912.38, 14,721.65] | 1675 | 808 |
| independent-random-n256-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 795.86 [780.13, 1,209.59] | 777.13 [709.05, 1,532.65] | 0 | 0 |
| independent-random-n256-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 712.40 [692.72, 718.09] | 878.85 [815.06, 1,661.64] | 0 | 0 |
| independent-random-n256-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 13.30 [13.00, 13.50] | 14,249.39 [14,159.90, 14,666.89] | 1445 | 744 |
| independent-random-n256-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,861.78 [1,550.00, 1,946.62] | 999.77 [579.63, 1,071.33] | 0 | 0 |
| independent-random-n256-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,790.89 [1,082.75, 1,818.26] | 1,047.03 [879.81, 1,351.29] | 0 | 0 |
| independent-random-n256-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 20.37 [19.07, 24.70] | 14,823.83 [14,388.97, 14,906.56] | 1138 | 204 |
| independent-random-n256-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 535.66 [505.98, 569.23] | 3,106.23 [2,034.52, 4,518.96] | 0 | 0 |
| independent-random-n256-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 197.56 [138.00, 214.03] | 13,172.70 [10,480.16, 14,195.26] | 788 | 0 |
| independent-random-n256-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 78.43 [70.30, 88.17] | 12,428.74 [11,099.84, 13,662.08] | 804 | 33 |
| independent-random-n256-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,233.53 [788.65, 1,252.82] | 1,463.85 [751.87, 1,607.06] | 0 | 0 |
| independent-random-n256-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 714.76 [689.73, 719.50] | 924.71 [851.30, 1,094.56] | 0 | 0 |
| independent-random-n256-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 47.43 [46.56, 49.69] | 12,219.49 [9,838.80, 13,372.16] | 603 | 0 |
| independent-random-n256-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,914.07 [1,858.19, 1,949.11] | 974.12 [952.00, 1,018.56] | 0 | 0 |
| independent-random-n256-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,606.56 [1,007.70, 1,798.88] | 917.04 [597.45, 1,196.11] | 0 | 0 |
| independent-random-n256-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 36.87 [34.40, 37.20] | 12,483.02 [11,961.52, 13,676.54] | 615 | 0 |
| independent-random-n256-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 535.06 [512.38, 549.66] | 3,965.01 [2,720.06, 4,705.41] | 0 | 0 |
| independent-random-n256-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 177.23 [153.13, 217.80] | 12,732.29 [10,716.46, 14,252.19] | 639 | 0 |
| independent-random-n256-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 138.43 [136.57, 141.80] | 10,806.82 [10,545.43, 11,696.04] | 347 | 0 |
| independent-random-n256-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 972.26 [815.72, 1,205.30] | 1,577.70 [1,138.89, 2,230.58] | 0 | 0 |
| independent-random-n256-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 694.83 [672.39, 704.93] | 975.10 [943.76, 1,705.85] | 0 | 0 |
| independent-random-n256-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 145.36 [92.10, 149.73] | 12,957.01 [12,818.94, 14,570.32] | 265 | 0 |
| independent-random-n256-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,878.37 [1,534.92, 1,908.66] | 1,001.01 [627.20, 1,062.97] | 0 | 0 |
| independent-random-n256-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,778.31 [1,041.36, 1,817.15] | 1,014.60 [787.22, 1,237.99] | 0 | 0 |
| independent-random-n256-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 37.07 [35.97, 44.30] | 13,670.32 [12,324.98, 14,384.83] | 726 | 30 |
| independent-random-n256-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 496.59 [479.96, 541.02] | 4,141.09 [2,039.96, 5,092.15] | 0 | 0 |
| independent-random-n256-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 156.33 [127.90, 213.23] | 12,926.80 [9,836.57, 14,066.65] | 994 | 0 |
| independent-random-n256-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 96.66 [75.73, 176.00] | 13,973.61 [13,018.86, 14,670.18] | 285 | 0 |
| independent-random-n256-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 802.83 [738.59, 1,131.36] | 1,199.67 [825.16, 1,967.23] | 0 | 0 |
| independent-random-n256-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 688.80 [642.56, 719.26] | 1,044.19 [885.39, 1,469.52] | 0 | 0 |
| independent-random-n256-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 107.13 [91.66, 149.67] | 12,876.39 [10,647.56, 14,333.18] | 453 | 64 |
| independent-random-n256-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,920.54 [1,885.99, 1,946.62] | 958.15 [925.25, 1,038.79] | 0 | 0 |
| independent-random-n256-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,694.93 [1,079.29, 1,807.98] | 1,019.44 [957.63, 1,760.87] | 0 | 0 |
| independent-random-n4-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 351.37 [341.66, 353.63] | 25.62 [24.57, 26.63] | 0 | 0 |
| independent-random-n4-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,035.20 [1,019.95, 1,072.03] | 19.77 [18.11, 22.94] | 0 | 0 |
| independent-random-n4-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,020.23 [985.29, 1,044.53] | 21.26 [19.51, 24.06] | 0 | 0 |
| independent-random-n4-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 238.46 [234.43, 250.00] | 29.55 [28.25, 30.17] | 0 | 0 |
| independent-random-n4-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,387.06 [1,372.33, 1,423.86] | 10.30 [10.14, 10.66] | 0 | 0 |
| independent-random-n4-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,340.39 [1,333.10, 1,392.89] | 10.12 [9.98, 10.28] | 0 | 0 |
| independent-random-n4-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 174.96 [174.50, 181.27] | 37.64 [36.30, 38.70] | 0 | 0 |
| independent-random-n4-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,044.04 [1,992.27, 2,060.30] | 5.80 [5.41, 6.22] | 0 | 0 |
| independent-random-n4-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,005.00 [1,976.29, 2,017.52] | 5.74 [5.57, 6.07] | 0 | 0 |
| independent-random-n4-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 430.68 [419.56, 434.76] | 18.72 [18.56, 19.30] | 0 | 0 |
| independent-random-n4-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,041.19 [1,030.66, 1,061.93] | 19.76 [18.98, 21.53] | 0 | 0 |
| independent-random-n4-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,006.93 [995.72, 1,020.96] | 21.17 [19.33, 21.68] | 0 | 0 |
| independent-random-n4-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 397.83 [394.15, 408.09] | 17.49 [17.27, 17.97] | 0 | 0 |
| independent-random-n4-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,406.79 [1,396.93, 1,413.99] | 10.30 [10.21, 10.71] | 0 | 0 |
| independent-random-n4-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,389.33 [1,374.71, 1,412.99] | 10.28 [10.12, 10.81] | 0 | 0 |
| independent-random-n4-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 403.56 [403.09, 404.80] | 16.95 [16.81, 16.99] | 0 | 0 |
| independent-random-n4-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,037.02 [1,997.04, 2,078.03] | 5.77 [5.67, 6.23] | 0 | 0 |
| independent-random-n4-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,990.89 [1,971.58, 2,007.66] | 6.14 [5.63, 6.33] | 0 | 0 |
| independent-random-n4-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 440.99 [414.05, 453.03] | 18.33 [17.92, 18.67] | 0 | 0 |
| independent-random-n4-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,040.46 [1,017.60, 1,058.75] | 20.14 [19.06, 23.19] | 0 | 0 |
| independent-random-n4-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,013.16 [996.86, 1,026.76] | 20.32 [19.62, 21.81] | 0 | 0 |
| independent-random-n4-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 462.22 [460.49, 482.76] | 15.49 [15.25, 15.66] | 0 | 0 |
| independent-random-n4-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,411.46 [1,399.16, 1,423.89] | 10.38 [10.12, 10.71] | 0 | 0 |
| independent-random-n4-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,385.08 [1,371.20, 1,397.58] | 10.63 [10.47, 11.19] | 0 | 0 |
| independent-random-n4-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 466.53 [439.33, 487.03] | 14.62 [14.44, 14.75] | 0 | 0 |
| independent-random-n4-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,023.53 [2,017.96, 2,056.23] | 5.97 [5.57, 6.19] | 0 | 0 |
| independent-random-n4-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,980.73 [1,963.85, 2,033.33] | 6.01 [5.83, 6.35] | 0 | 0 |
| independent-random-n4-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 410.40 [379.05, 412.26] | 22.55 [22.49, 23.59] | 0 | 0 |
| independent-random-n4-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,052.25 [1,028.20, 1,062.70] | 19.75 [18.72, 23.04] | 0 | 0 |
| independent-random-n4-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 995.90 [986.12, 1,001.93] | 21.76 [21.40, 22.68] | 0 | 0 |
| independent-random-n4-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 438.59 [412.16, 457.28] | 17.11 [16.80, 17.75] | 0 | 0 |
| independent-random-n4-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,409.79 [1,400.19, 1,416.66] | 10.45 [10.14, 10.88] | 0 | 0 |
| independent-random-n4-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,378.36 [1,367.23, 1,406.33] | 10.64 [10.43, 10.97] | 0 | 0 |
| independent-random-n4-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 472.27 [461.23, 488.31] | 15.63 [15.20, 15.77] | 0 | 0 |
| independent-random-n4-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,028.46 [2,014.16, 2,056.13] | 5.91 [5.25, 6.28] | 0 | 0 |
| independent-random-n4-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,979.29 [1,963.28, 2,006.50] | 6.22 [5.73, 6.29] | 0 | 0 |
| independent-random-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 127.03 [115.10, 145.63] | 11,300.70 [10,009.02, 11,718.22] | 0 | 0 |
| independent-random-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 706.23 [626.57, 1,120.33] | 787.66 [188.26, 876.00] | 0 | 0 |
| independent-random-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 419.33 [392.06, 452.29] | 3,188.08 [1,382.34, 3,826.89] | 0 | 0 |
| independent-random-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 179.00 [161.86, 213.93] | 1,980.69 [521.81, 6,196.94] | 0 | 0 |
| independent-random-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,473.64 [1,333.96, 1,485.89] | 138.22 [118.35, 322.60] | 0 | 0 |
| independent-random-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,313.53 [1,155.23, 1,364.59] | 301.07 [292.16, 463.84] | 0 | 0 |
| independent-random-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 79.06 [68.00, 96.20] | 8,666.40 [1,890.65, 10,547.67] | 0 | 0 |
| independent-random-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,302.52 [2,280.01, 2,325.36] | 173.43 [95.90, 193.34] | 0 | 0 |
| independent-random-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,247.09 [2,223.74, 2,291.18] | 152.73 [83.66, 172.29] | 0 | 0 |
| independent-random-n64-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 201.23 [166.53, 221.19] | 5,514.92 [3,511.51, 5,858.38] | 0 | 0 |
| independent-random-n64-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 717.37 [672.16, 732.50] | 747.39 [712.87, 826.98] | 0 | 0 |
| independent-random-n64-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 382.50 [365.99, 428.35] | 3,058.22 [1,553.50, 3,545.82] | 0 | 0 |
| independent-random-n64-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 142.60 [137.73, 237.62] | 5,814.71 [5,325.35, 6,537.56] | 0 | 0 |
| independent-random-n64-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,515.79 [1,308.86, 1,534.50] | 113.27 [110.42, 323.70] | 0 | 0 |
| independent-random-n64-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,302.56 [1,020.89, 1,317.76] | 337.76 [291.62, 497.33] | 0 | 0 |
| independent-random-n64-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 122.26 [117.73, 123.26] | 8,438.78 [8,361.62, 8,499.84] | 0 | 0 |
| independent-random-n64-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,271.66 [2,258.92, 2,309.65] | 92.44 [82.01, 150.73] | 0 | 0 |
| independent-random-n64-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,230.69 [1,862.96, 2,274.96] | 157.18 [88.67, 247.17] | 0 | 0 |
| independent-random-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 202.13 [152.70, 312.73] | 3,403.87 [3,030.30, 4,340.50] | 0 | 0 |
| independent-random-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 692.29 [679.12, 756.89] | 736.36 [708.92, 761.30] | 0 | 0 |
| independent-random-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 373.46 [343.23, 380.69] | 2,789.75 [1,917.74, 3,940.79] | 0 | 0 |
| independent-random-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 338.70 [311.47, 391.13] | 2,483.64 [2,092.20, 2,645.15] | 0 | 0 |
| independent-random-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,510.01 [1,415.63, 1,522.98] | 107.31 [106.26, 300.05] | 0 | 0 |
| independent-random-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,224.46 [1,096.36, 1,358.99] | 438.59 [354.86, 488.17] | 0 | 0 |
| independent-random-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 217.39 [185.26, 234.69] | 3,644.71 [3,492.94, 4,222.98] | 0 | 0 |
| independent-random-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,316.29 [2,298.08, 2,338.52] | 82.29 [67.88, 110.28] | 0 | 0 |
| independent-random-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,274.29 [2,162.49, 2,336.39] | 86.69 [76.36, 208.47] | 0 | 0 |
| independent-random-n64-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 184.29 [161.16, 272.26] | 3,915.01 [3,252.09, 4,220.61] | 0 | 0 |
| independent-random-n64-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 722.46 [675.32, 742.26] | 738.27 [730.70, 939.86] | 0 | 0 |
| independent-random-n64-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 381.30 [333.92, 514.46] | 2,855.20 [1,743.72, 2,958.55] | 0 | 0 |
| independent-random-n64-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 456.16 [411.50, 514.09] | 1,191.79 [817.77, 1,969.69] | 0 | 0 |
| independent-random-n64-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,506.02 [1,468.36, 1,516.99] | 116.56 [105.41, 223.46] | 0 | 0 |
| independent-random-n64-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,280.83 [1,147.20, 1,319.94] | 361.49 [291.34, 480.96] | 0 | 0 |
| independent-random-n64-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 640.93 [631.03, 644.01] | 846.62 [807.79, 920.76] | 0 | 0 |
| independent-random-n64-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,274.26 [2,261.56, 2,351.86] | 111.26 [93.99, 132.64] | 0 | 0 |
| independent-random-n64-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,239.15 [2,215.96, 2,293.34] | 126.41 [82.57, 174.73] | 0 | 0 |
| independent-single-n1-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 98.86 [98.80, 99.03] | 14.68 [14.66, 15.14] | 0 | 0 |
| independent-single-n1-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 790.56 [771.85, 791.68] | 3.28 [3.27, 3.42] | 0 | 0 |
| independent-single-n1-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 765.86 [746.43, 767.05] | 3.53 [3.44, 3.55] | 0 | 0 |
| independent-single-n1-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 99.63 [99.33, 99.73] | 14.31 [14.12, 14.51] | 0 | 0 |
| independent-single-n1-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 760.19 [755.13, 784.73] | 2.55 [2.54, 2.61] | 0 | 0 |
| independent-single-n1-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 757.17 [746.76, 767.76] | 2.66 [2.57, 2.68] | 0 | 0 |
| independent-single-n1-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 99.50 [99.43, 99.53] | 14.05 [13.99, 14.18] | 0 | 0 |
| independent-single-n1-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,048.13 [1,021.16, 1,053.66] | 1.94 [1.86, 2.11] | 0 | 0 |
| independent-single-n1-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 990.90 [974.00, 996.03] | 2.07 [2.04, 2.21] | 0 | 0 |
| independent-single-n1-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 99.13 [99.00, 99.33] | 14.26 [13.82, 14.73] | 0 | 0 |
| independent-single-n1-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 784.40 [766.43, 791.55] | 3.34 [3.29, 3.44] | 0 | 0 |
| independent-single-n1-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 759.35 [747.44, 761.59] | 3.48 [3.41, 3.56] | 0 | 0 |
| independent-single-n1-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 99.93 [99.86, 99.97] | 12.76 [12.68, 13.00] | 0 | 0 |
| independent-single-n1-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 736.23 [730.62, 760.93] | 2.69 [2.65, 2.79] | 0 | 0 |
| independent-single-n1-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 731.20 [716.80, 757.00] | 2.69 [2.68, 2.78] | 0 | 0 |
| independent-single-n1-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 99.97 [99.90, 100.00] | 12.47 [12.41, 12.62] | 0 | 0 |
| independent-single-n1-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,042.66 [1,027.66, 1,045.80] | 2.05 [1.98, 2.11] | 0 | 0 |
| independent-single-n1-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,007.86 [991.69, 1,014.15] | 2.07 [2.06, 2.17] | 0 | 0 |
| independent-single-n1-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 98.53 [98.40, 98.63] | 15.06 [15.00, 15.26] | 0 | 0 |
| independent-single-n1-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 787.66 [768.03, 789.13] | 3.37 [3.28, 3.43] | 0 | 0 |
| independent-single-n1-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 762.93 [757.83, 764.80] | 3.55 [3.48, 3.56] | 0 | 0 |
| independent-single-n1-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 99.97 [99.86, 100.00] | 12.82 [12.66, 12.88] | 0 | 0 |
| independent-single-n1-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 729.70 [720.69, 745.90] | 2.70 [2.64, 2.77] | 0 | 0 |
| independent-single-n1-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 736.16 [700.33, 759.60] | 2.73 [2.65, 2.87] | 0 | 0 |
| independent-single-n1-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 99.97 [99.96, 100.00] | 11.83 [11.70, 11.99] | 0 | 0 |
| independent-single-n1-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,022.43 [1,016.02, 1,043.10] | 2.08 [2.00, 2.18] | 0 | 0 |
| independent-single-n1-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,006.13 [995.80, 1,009.46] | 2.08 [2.04, 2.19] | 0 | 0 |
| independent-single-n1-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 98.03 [97.86, 98.07] | 16.94 [16.16, 18.25] | 0 | 0 |
| independent-single-n1-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 786.89 [769.30, 789.39] | 3.35 [3.29, 3.40] | 0 | 0 |
| independent-single-n1-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 760.56 [756.93, 764.62] | 3.52 [3.46, 3.64] | 0 | 0 |
| independent-single-n1-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 99.93 [99.86, 99.97] | 12.74 [12.60, 12.79] | 0 | 0 |
| independent-single-n1-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 737.12 [725.16, 746.56] | 2.70 [2.69, 2.81] | 0 | 0 |
| independent-single-n1-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 709.08 [698.36, 718.60] | 2.82 [2.76, 2.90] | 0 | 0 |
| independent-single-n1-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 100.00 [100.00, 100.00] | 11.94 [11.83, 12.18] | 0 | 0 |
| independent-single-n1-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,048.06 [1,014.54, 1,055.66] | 2.02 [1.99, 2.08] | 0 | 0 |
| independent-single-n1-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 981.66 [975.30, 1,004.60] | 2.19 [2.14, 2.26] | 0 | 0 |
| independent-single-n16-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 63.37 [63.03, 63.53] | 270.73 [270.22, 274.61] | 0 | 0 |
| independent-single-n16-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 724.66 [723.30, 725.60] | 42.42 [41.75, 42.79] | 0 | 0 |
| independent-single-n16-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 707.13 [704.75, 707.37] | 44.37 [43.32, 44.81] | 0 | 0 |
| independent-single-n16-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 63.60 [63.57, 63.66] | 262.07 [261.50, 263.89] | 0 | 0 |
| independent-single-n16-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,058.99 [1,042.81, 1,071.63] | 25.98 [25.65, 26.84] | 0 | 0 |
| independent-single-n16-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,014.13 [1,010.86, 1,029.88] | 26.70 [26.25, 27.63] | 0 | 0 |
| independent-single-n16-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 43.73 [43.60, 43.83] | 381.55 [381.08, 384.95] | 0 | 0 |
| independent-single-n16-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,541.16 [1,536.43, 1,547.40] | 18.11 [17.83, 18.22] | 0 | 0 |
| independent-single-n16-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,507.83 [1,502.49, 1,510.80] | 18.41 [18.14, 18.96] | 0 | 0 |
| independent-single-n16-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 245.72 [245.23, 246.59] | 85.60 [84.84, 88.00] | 0 | 0 |
| independent-single-n16-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 723.36 [721.52, 724.76] | 42.66 [42.22, 43.11] | 0 | 0 |
| independent-single-n16-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 702.79 [701.10, 705.85] | 44.45 [44.21, 45.34] | 0 | 0 |
| independent-single-n16-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 142.10 [140.53, 143.17] | 127.13 [125.40, 128.20] | 0 | 0 |
| independent-single-n16-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,021.76 [997.06, 1,087.19] | 26.65 [26.14, 26.97] | 0 | 0 |
| independent-single-n16-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,051.17 [1,025.56, 1,067.20] | 26.54 [26.29, 27.44] | 0 | 0 |
| independent-single-n16-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 88.03 [87.87, 88.10] | 190.69 [190.00, 191.08] | 0 | 0 |
| independent-single-n16-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,537.83 [1,532.16, 1,540.74] | 18.23 [17.94, 18.58] | 0 | 0 |
| independent-single-n16-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,507.13 [1,494.65, 1,512.46] | 18.65 [18.03, 18.77] | 0 | 0 |
| independent-single-n16-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 331.00 [328.89, 333.93] | 73.69 [73.36, 75.14] | 0 | 0 |
| independent-single-n16-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 724.33 [722.50, 725.00] | 41.78 [41.42, 43.13] | 0 | 0 |
| independent-single-n16-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 703.36 [701.90, 705.79] | 44.37 [44.01, 44.58] | 0 | 0 |
| independent-single-n16-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 422.40 [419.33, 427.88] | 52.80 [50.80, 53.27] | 0 | 0 |
| independent-single-n16-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,073.23 [1,032.46, 1,082.32] | 25.64 [25.43, 26.74] | 0 | 0 |
| independent-single-n16-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,049.76 [1,032.23, 1,075.98] | 26.31 [25.75, 27.68] | 0 | 0 |
| independent-single-n16-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 228.10 [227.23, 229.30] | 79.72 [78.96, 79.96] | 0 | 0 |
| independent-single-n16-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,539.53 [1,534.22, 1,546.73] | 17.84 [17.67, 18.20] | 0 | 0 |
| independent-single-n16-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,498.84 [1,491.83, 1,503.93] | 18.54 [18.42, 18.71] | 0 | 0 |
| independent-single-n16-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 348.72 [347.67, 349.66] | 80.33 [76.80, 82.34] | 0 | 0 |
| independent-single-n16-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 723.10 [720.93, 724.36] | 42.50 [41.93, 42.97] | 0 | 0 |
| independent-single-n16-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 701.96 [700.72, 703.08] | 44.68 [43.91, 44.98] | 0 | 0 |
| independent-single-n16-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 522.13 [519.56, 532.12] | 47.49 [46.25, 48.65] | 0 | 0 |
| independent-single-n16-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,051.63 [1,050.23, 1,075.96] | 26.04 [25.90, 26.26] | 0 | 0 |
| independent-single-n16-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,056.69 [1,021.44, 1,072.13] | 26.24 [25.96, 27.26] | 0 | 0 |
| independent-single-n16-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 798.30 [790.76, 801.93] | 34.07 [34.01, 34.37] | 0 | 0 |
| independent-single-n16-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,536.93 [1,535.09, 1,539.36] | 18.10 [17.77, 18.20] | 0 | 0 |
| independent-single-n16-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,500.79 [1,497.43, 1,504.26] | 18.63 [18.31, 18.79] | 0 | 0 |
| independent-single-n256-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 1.40 [1.37, 1.47] | 814.36 [802.16, 863.26] | 1374 | 320 |
| independent-single-n256-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 425.37 [421.30, 435.20] | 1,061.20 [760.65, 1,085.74] | 0 | 0 |
| independent-single-n256-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 142.13 [138.06, 147.83] | 2,048.45 [2,043.27, 2,385.28] | 0 | 0 |
| independent-single-n256-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 4.23 [3.70, 4.53] | 14,756.85 [14,390.50, 14,994.74] | 1489 | 320 |
| independent-single-n256-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 763.43 [750.12, 767.22] | 395.01 [386.33, 407.76] | 0 | 0 |
| independent-single-n256-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 717.23 [691.29, 741.36] | 477.84 [424.61, 493.70] | 0 | 0 |
| independent-single-n256-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 1.37 [1.33, 3.50] | 830.66 [816.09, 10,420.73] | 1565 | 320 |
| independent-single-n256-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,032.50 [1,031.69, 1,038.03] | 277.70 [274.43, 286.65] | 0 | 0 |
| independent-single-n256-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,018.40 [1,017.20, 1,021.16] | 280.96 [276.03, 283.89] | 0 | 0 |
| independent-single-n256-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 3.23 [2.10, 6.23] | 15,013.57 [13,245.97, 15,085.13] | 1966 | 300 |
| independent-single-n256-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 423.03 [396.70, 436.10] | 779.66 [776.93, 1,098.40] | 0 | 0 |
| independent-single-n256-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 144.76 [138.33, 219.90] | 2,443.46 [2,025.22, 2,589.52] | 0 | 0 |
| independent-single-n256-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 18.30 [10.17, 24.27] | 14,864.89 [14,572.14, 14,896.46] | 597 | 14 |
| independent-single-n256-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 762.30 [748.06, 769.70] | 399.17 [384.30, 401.27] | 0 | 0 |
| independent-single-n256-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 706.45 [690.83, 730.94] | 495.11 [447.57, 519.17] | 0 | 0 |
| independent-single-n256-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 6.27 [4.10, 6.47] | 14,373.11 [11,947.79, 14,900.72] | 2051 | 309 |
| independent-single-n256-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,029.97 [1,029.33, 1,030.60] | 275.01 [272.57, 277.99] | 0 | 0 |
| independent-single-n256-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,011.82 [1,010.50, 1,017.26] | 282.22 [276.56, 288.03] | 0 | 0 |
| independent-single-n256-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 50.60 [28.93, 51.33] | 7,697.57 [7,222.32, 14,003.38] | 51 | 0 |
| independent-single-n256-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 425.93 [386.36, 437.03] | 1,043.94 [767.11, 1,692.89] | 0 | 0 |
| independent-single-n256-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 138.63 [134.36, 144.90] | 2,345.42 [2,064.88, 3,109.59] | 0 | 0 |
| independent-single-n256-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 63.07 [62.56, 64.27] | 5,368.07 [5,276.38, 5,490.00] | 0 | 0 |
| independent-single-n256-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 759.50 [747.43, 766.76] | 403.22 [389.30, 407.50] | 0 | 0 |
| independent-single-n256-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 708.06 [697.96, 712.40] | 475.47 [466.78, 488.93] | 0 | 0 |
| independent-single-n256-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 41.00 [37.53, 44.00] | 10,748.84 [8,002.94, 11,291.07] | 0 | 0 |
| independent-single-n256-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,029.96 [1,029.53, 1,031.09] | 276.93 [274.25, 279.00] | 0 | 0 |
| independent-single-n256-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,011.85 [1,007.98, 1,015.33] | 277.44 [274.27, 286.88] | 0 | 0 |
| independent-single-n256-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 77.07 [76.53, 77.36] | 5,447.77 [5,324.15, 5,567.40] | 0 | 0 |
| independent-single-n256-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 425.97 [407.83, 436.25] | 808.27 [774.91, 1,119.57] | 0 | 0 |
| independent-single-n256-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 143.06 [136.76, 146.60] | 2,131.29 [2,065.23, 2,471.48] | 0 | 0 |
| independent-single-n256-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 118.53 [117.80, 119.66] | 2,306.76 [2,265.82, 2,318.55] | 0 | 0 |
| independent-single-n256-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 765.20 [741.96, 768.80] | 393.55 [388.52, 421.27] | 0 | 0 |
| independent-single-n256-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 715.30 [694.03, 727.12] | 471.89 [456.44, 524.38] | 0 | 0 |
| independent-single-n256-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 104.03 [103.56, 104.83] | 2,549.26 [2,540.08, 2,573.64] | 0 | 0 |
| independent-single-n256-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,028.96 [1,026.56, 1,031.71] | 277.42 [273.56, 282.13] | 0 | 0 |
| independent-single-n256-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,011.90 [1,006.87, 1,014.43] | 281.31 [278.00, 285.81] | 0 | 0 |
| independent-single-n4-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 259.36 [254.56, 263.63] | 28.34 [27.63, 28.78] | 0 | 0 |
| independent-single-n4-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 807.93 [792.85, 811.93] | 10.91 [10.71, 10.94] | 0 | 0 |
| independent-single-n4-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 789.79 [773.13, 790.00] | 11.49 [11.32, 11.53] | 0 | 0 |
| independent-single-n4-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 154.63 [151.66, 155.50] | 35.81 [35.47, 36.15] | 0 | 0 |
| independent-single-n4-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,133.43 [1,086.56, 1,146.13] | 7.09 [6.97, 7.34] | 0 | 0 |
| independent-single-n4-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,058.43 [1,019.43, 1,119.46] | 7.63 [7.25, 7.72] | 0 | 0 |
| independent-single-n4-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 101.73 [101.53, 102.23] | 45.98 [45.77, 46.25] | 0 | 0 |
| independent-single-n4-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,614.48 [1,606.53, 1,635.69] | 4.87 [4.77, 4.91] | 0 | 0 |
| independent-single-n4-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,580.46 [1,568.83, 1,590.96] | 4.98 [4.94, 5.11] | 0 | 0 |
| independent-single-n4-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 360.99 [359.76, 362.76] | 20.75 [20.38, 21.08] | 0 | 0 |
| independent-single-n4-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 806.12 [799.15, 808.46] | 10.85 [10.63, 11.20] | 0 | 0 |
| independent-single-n4-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 784.72 [781.65, 789.82] | 11.45 [11.19, 11.56] | 0 | 0 |
| independent-single-n4-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 369.93 [353.37, 378.43] | 17.91 [17.11, 19.00] | 0 | 0 |
| independent-single-n4-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,126.96 [1,111.56, 1,155.06] | 7.11 [7.01, 7.21] | 0 | 0 |
| independent-single-n4-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,116.23 [1,094.63, 1,140.83] | 7.25 [7.17, 7.34] | 0 | 0 |
| independent-single-n4-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 290.20 [287.47, 290.97] | 21.72 [21.62, 21.84] | 0 | 0 |
| independent-single-n4-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,610.83 [1,604.09, 1,619.21] | 4.90 [4.76, 4.99] | 0 | 0 |
| independent-single-n4-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,573.80 [1,569.37, 1,580.66] | 5.07 [4.97, 5.14] | 0 | 0 |
| independent-single-n4-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 371.52 [371.03, 373.40] | 18.98 [18.83, 19.10] | 0 | 0 |
| independent-single-n4-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 803.32 [802.86, 805.79] | 10.68 [10.57, 10.89] | 0 | 0 |
| independent-single-n4-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 781.74 [779.73, 786.49] | 11.41 [11.28, 11.66] | 0 | 0 |
| independent-single-n4-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 392.06 [390.93, 392.63] | 16.40 [16.10, 16.54] | 0 | 0 |
| independent-single-n4-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,121.30 [1,097.72, 1,164.93] | 7.17 [7.06, 7.25] | 0 | 0 |
| independent-single-n4-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,107.63 [1,075.76, 1,127.31] | 7.36 [7.13, 7.53] | 0 | 0 |
| independent-single-n4-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 398.70 [398.12, 398.96] | 14.70 [14.35, 14.75] | 0 | 0 |
| independent-single-n4-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,611.69 [1,604.59, 1,615.58] | 4.95 [4.86, 5.03] | 0 | 0 |
| independent-single-n4-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,572.67 [1,567.18, 1,577.49] | 5.08 [5.04, 5.10] | 0 | 0 |
| independent-single-n4-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 364.56 [363.73, 365.40] | 20.64 [20.11, 21.43] | 0 | 0 |
| independent-single-n4-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 806.96 [801.76, 808.52] | 10.79 [10.58, 11.03] | 0 | 0 |
| independent-single-n4-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 784.86 [782.33, 786.00] | 11.46 [11.30, 11.53] | 0 | 0 |
| independent-single-n4-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 389.73 [388.80, 390.70] | 16.93 [16.55, 17.44] | 0 | 0 |
| independent-single-n4-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,111.63 [1,068.63, 1,149.52] | 7.21 [7.02, 7.53] | 0 | 0 |
| independent-single-n4-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,105.66 [1,081.83, 1,109.18] | 7.26 [7.19, 7.41] | 0 | 0 |
| independent-single-n4-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 395.96 [395.32, 396.55] | 16.23 [15.95, 16.49] | 0 | 0 |
| independent-single-n4-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,615.99 [1,599.45, 1,620.09] | 4.89 [4.88, 4.99] | 0 | 0 |
| independent-single-n4-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,571.06 [1,563.79, 1,576.64] | 5.05 [4.97, 5.08] | 0 | 0 |
| independent-single-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 2.83 [1.43, 3.07] | 12,031.42 [833.38, 14,698.26] | 424 | 101 |
| independent-single-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 439.76 [429.82, 448.17] | 189.73 [178.99, 198.86] | 0 | 0 |
| independent-single-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 141.99 [137.70, 215.16] | 568.17 [529.12, 716.12] | 0 | 0 |
| independent-single-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 4.77 [4.40, 5.13] | 14,024.83 [13,496.22, 14,956.51] | 304 | 126 |
| independent-single-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 778.76 [770.63, 788.30] | 117.24 [113.22, 119.94] | 0 | 0 |
| independent-single-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 734.26 [720.30, 743.36] | 125.14 [122.19, 130.65] | 0 | 0 |
| independent-single-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 1.87 [1.73, 3.50] | 809.10 [804.83, 9,390.35] | 513 | 315 |
| independent-single-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,034.31 [1,033.56, 1,035.86] | 87.15 [85.45, 88.14] | 0 | 0 |
| independent-single-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,020.89 [1,019.13, 1,023.83] | 88.91 [87.32, 89.31] | 0 | 0 |
| independent-single-n64-p2 | 1c1t-g1 | baseline | 5/5; measured=5 | 9.83 [5.67, 10.07] | 9,558.47 [7,682.20, 14,836.28] | 112 | 0 |
| independent-single-n64-p2 | 1c1t-g1 | v000 | 5/5; measured=5 | 433.60 [400.20, 446.26] | 195.98 [182.20, 272.83] | 0 | 0 |
| independent-single-n64-p2 | 1c1t-g1 | v003 | 5/5; measured=5 | 145.70 [138.63, 243.67] | 553.59 [530.53, 591.59] | 0 | 0 |
| independent-single-n64-p2 | 2c2t-g2 | baseline | 5/5; measured=5 | 16.63 [13.70, 20.30] | 7,826.63 [6,810.81, 8,424.15] | 0 | 0 |
| independent-single-n64-p2 | 2c2t-g2 | v000 | 5/5; measured=5 | 787.42 [774.00, 791.41] | 117.43 [115.36, 119.30] | 0 | 0 |
| independent-single-n64-p2 | 2c2t-g2 | v003 | 5/5; measured=5 | 736.10 [720.43, 751.53] | 126.01 [122.30, 137.25] | 0 | 0 |
| independent-single-n64-p2 | 2c4t-g4 | baseline | 5/5; measured=5 | 10.03 [9.60, 13.20] | 9,619.54 [8,449.10, 10,817.68] | 0 | 0 |
| independent-single-n64-p2 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,035.30 [1,031.73, 1,038.93] | 88.10 [87.52, 90.06] | 0 | 0 |
| independent-single-n64-p2 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,016.33 [1,014.62, 1,019.73] | 88.53 [86.14, 90.58] | 0 | 0 |
| independent-single-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 47.27 [37.10, 50.83] | 4,486.05 [4,060.06, 5,236.68] | 0 | 0 |
| independent-single-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 442.43 [418.40, 443.43] | 192.55 [187.12, 203.57] | 0 | 0 |
| independent-single-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 146.73 [141.73, 244.76] | 530.08 [404.33, 597.22] | 0 | 0 |
| independent-single-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 62.03 [61.73, 64.30] | 2,797.54 [2,508.31, 3,064.90] | 0 | 0 |
| independent-single-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 773.90 [770.86, 777.76] | 117.71 [116.49, 117.80] | 0 | 0 |
| independent-single-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 731.70 [721.59, 748.22] | 128.04 [124.40, 129.41] | 0 | 0 |
| independent-single-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 39.97 [33.47, 42.77] | 4,652.61 [3,412.18, 5,350.72] | 0 | 0 |
| independent-single-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,032.59 [1,031.51, 1,036.06] | 86.81 [84.12, 87.88] | 0 | 0 |
| independent-single-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,016.30 [1,011.96, 1,019.69] | 89.81 [86.78, 91.08] | 0 | 0 |
| independent-single-n64-p8 | 1c1t-g1 | baseline | 5/5; measured=5 | 79.33 [78.43, 79.83] | 3,354.06 [2,999.08, 3,375.58] | 0 | 0 |
| independent-single-n64-p8 | 1c1t-g1 | v000 | 5/5; measured=5 | 429.10 [414.93, 432.19] | 197.03 [196.53, 200.54] | 0 | 0 |
| independent-single-n64-p8 | 1c1t-g1 | v003 | 5/5; measured=5 | 144.89 [133.90, 225.93] | 540.97 [526.33, 786.59] | 0 | 0 |
| independent-single-n64-p8 | 2c2t-g2 | baseline | 5/5; measured=5 | 120.36 [119.63, 121.00] | 596.79 [588.40, 599.64] | 0 | 0 |
| independent-single-n64-p8 | 2c2t-g2 | v000 | 5/5; measured=5 | 781.43 [773.08, 788.16] | 117.03 [114.48, 121.40] | 0 | 0 |
| independent-single-n64-p8 | 2c2t-g2 | v003 | 5/5; measured=5 | 744.16 [725.76, 764.63] | 123.43 [121.16, 137.54] | 0 | 0 |
| independent-single-n64-p8 | 2c4t-g4 | baseline | 5/5; measured=5 | 105.43 [105.06, 105.77] | 652.01 [645.89, 666.64] | 0 | 0 |
| independent-single-n64-p8 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,031.26 [1,029.43, 1,032.56] | 86.94 [86.51, 88.37] | 0 | 0 |
| independent-single-n64-p8 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,014.22 [1,012.89, 1,015.80] | 88.69 [87.68, 90.49] | 0 | 0 |
| members-5 | 1c1t-g1 | baseline | 5/5; measured=5 | 269.39 [199.26, 342.03] | 2,273.31 [2,133.73, 3,310.75] | 64 | 50 |
| members-5 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,275.63 [1,187.86, 1,421.22] | 311.21 [149.76, 332.84] | 0 | 0 |
| members-5 | 1c1t-g1 | v003 | 5/5; measured=5 | 972.03 [905.10, 1,406.22] | 377.02 [148.98, 441.45] | 0 | 0 |
| members-5 | 2c2t-g2 | baseline | 5/5; measured=5 | 471.47 [458.63, 473.77] | 844.21 [813.50, 1,707.71] | 0 | 0 |
| members-5 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,644.90 [1,638.57, 1,651.16] | 178.86 [155.19, 191.42] | 0 | 0 |
| members-5 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,421.57 [1,418.55, 1,468.78] | 233.01 [231.54, 236.33] | 0 | 0 |
| members-5 | 2c4t-g4 | baseline | 5/5; measured=5 | 186.10 [185.39, 197.03] | 2,903.61 [2,351.63, 2,968.82] | 0 | 0 |
| members-5 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,816.95 [2,805.82, 2,829.63] | 101.81 [97.14, 112.23] | 0 | 0 |
| members-5 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,650.29 [2,572.30, 2,703.06] | 134.07 [130.78, 135.11] | 0 | 0 |
| members-9 | 1c1t-g1 | baseline | 5/5; measured=5 | 217.54 [190.30, 244.73] | 3,172.67 [2,470.48, 3,963.15] | 0 | 0 |
| members-9 | 1c1t-g1 | v000 | 5/5; measured=5 | 327.43 [265.49, 393.33] | 3,139.99 [2,814.07, 3,963.92] | 0 | 0 |
| members-9 | 1c1t-g1 | v003 | 5/5; measured=5 | 230.72 [184.77, 279.93] | 4,924.96 [4,893.05, 5,122.88] | 0 | 0 |
| members-9 | 2c2t-g2 | baseline | 5/5; measured=5 | 366.29 [326.60, 396.66] | 2,130.43 [1,492.12, 2,326.14] | 0 | 0 |
| members-9 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,308.40 [620.44, 1,337.49] | 115.72 [112.41, 1,073.18] | 0 | 0 |
| members-9 | 2c2t-g2 | v003 | 5/5; measured=5 | 938.10 [581.70, 1,070.86] | 836.17 [762.75, 1,281.07] | 0 | 0 |
| members-9 | 2c4t-g4 | baseline | 5/5; measured=5 | 280.00 [216.30, 313.83] | 4,153.37 [3,906.78, 4,618.86] | 0 | 0 |
| members-9 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,719.59 [947.25, 1,863.99] | 313.52 [107.76, 666.10] | 0 | 0 |
| members-9 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,658.82 [1,238.39, 1,860.33] | 315.59 [112.04, 520.29] | 0 | 0 |
| mixed-balanced-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 85.60 [80.20, 124.53] | 11,603.91 [10,864.64, 14,517.84] | 78 | 0 |
| mixed-balanced-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 449.13 [442.03, 475.33] | 1,263.85 [1,216.50, 1,330.45] | 0 | 0 |
| mixed-balanced-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 248.09 [231.16, 254.66] | 3,035.70 [2,886.51, 3,269.78] | 0 | 0 |
| mixed-balanced-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 139.93 [136.16, 152.26] | 6,959.57 [6,119.94, 10,035.69] | 0 | 0 |
| mixed-balanced-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 911.80 [903.00, 913.63] | 517.64 [501.46, 539.83] | 0 | 0 |
| mixed-balanced-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 938.90 [838.45, 960.73] | 559.80 [539.26, 662.39] | 0 | 0 |
| mixed-balanced-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 52.10 [45.30, 68.73] | 7,770.36 [5,741.90, 9,084.13] | 0 | 0 |
| mixed-balanced-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,488.40 [1,464.90, 1,505.84] | 496.95 [494.70, 516.60] | 0 | 0 |
| mixed-balanced-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,464.42 [1,459.22, 1,466.96] | 334.13 [324.66, 337.94] | 0 | 0 |
| mixed-balanced-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 201.20 [176.66, 207.16] | 8,171.39 [5,787.31, 10,439.82] | 0 | 0 |
| mixed-balanced-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 435.95 [426.53, 449.00] | 1,288.27 [1,242.39, 1,364.50] | 0 | 0 |
| mixed-balanced-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 237.10 [222.93, 255.09] | 3,038.39 [2,906.56, 3,306.80] | 0 | 0 |
| mixed-balanced-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 241.87 [234.40, 248.69] | 5,887.97 [4,691.39, 8,643.67] | 19 | 0 |
| mixed-balanced-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 916.53 [907.46, 919.18] | 516.00 [509.07, 529.78] | 0 | 0 |
| mixed-balanced-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 918.00 [882.03, 952.13] | 597.91 [536.93, 613.48] | 0 | 0 |
| mixed-balanced-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 286.96 [264.63, 317.53] | 6,101.77 [4,345.17, 7,198.50] | 0 | 0 |
| mixed-balanced-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,470.84 [1,435.26, 1,488.13] | 508.19 [495.57, 520.41] | 0 | 0 |
| mixed-balanced-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,445.48 [1,440.96, 1,453.44] | 338.28 [330.55, 345.22] | 0 | 0 |
| mixed-random-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 91.17 [83.00, 104.37] | 10,307.25 [9,202.55, 13,224.01] | 13 | 0 |
| mixed-random-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 449.76 [439.78, 473.05] | 1,278.38 [1,208.27, 1,394.49] | 0 | 0 |
| mixed-random-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 228.80 [219.43, 240.29] | 3,301.69 [3,056.91, 3,567.21] | 0 | 0 |
| mixed-random-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 140.97 [139.50, 153.76] | 5,402.05 [3,728.02, 6,690.08] | 0 | 0 |
| mixed-random-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 899.40 [888.24, 907.40] | 527.39 [516.66, 546.70] | 0 | 0 |
| mixed-random-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 911.82 [875.43, 928.33] | 624.84 [578.66, 713.43] | 0 | 0 |
| mixed-random-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 63.40 [39.03, 64.77] | 5,814.34 [5,640.00, 9,418.30] | 0 | 0 |
| mixed-random-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,481.63 [1,465.99, 1,487.75] | 496.40 [481.96, 515.59] | 0 | 0 |
| mixed-random-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,447.66 [1,443.92, 1,456.29] | 332.48 [330.84, 340.93] | 0 | 0 |
| mixed-random-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 217.36 [141.09, 227.43] | 5,443.72 [3,281.07, 7,460.29] | 54 | 0 |
| mixed-random-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 441.22 [426.16, 473.12] | 1,307.17 [1,280.80, 1,467.94] | 0 | 0 |
| mixed-random-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 237.10 [219.99, 261.96] | 3,103.18 [3,069.34, 3,236.62] | 0 | 0 |
| mixed-random-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 235.56 [233.66, 278.40] | 6,677.56 [4,545.76, 7,415.10] | 0 | 0 |
| mixed-random-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 900.06 [887.93, 917.71] | 532.89 [516.12, 550.84] | 0 | 0 |
| mixed-random-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 861.26 [823.10, 935.29] | 633.89 [571.67, 818.45] | 0 | 0 |
| mixed-random-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 304.79 [241.76, 313.76] | 3,614.75 [2,814.40, 4,559.15] | 0 | 0 |
| mixed-random-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,459.13 [1,434.13, 1,469.79] | 494.92 [489.69, 513.51] | 0 | 0 |
| mixed-random-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,436.06 [1,426.76, 1,440.06] | 341.95 [337.59, 352.43] | 0 | 0 |
| mixed-single-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 2.57 [1.50, 3.57] | 13,465.73 [831.28, 14,564.83] | 492 | 154 |
| mixed-single-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 441.69 [438.29, 446.20] | 191.88 [184.98, 192.16] | 0 | 0 |
| mixed-single-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 147.13 [138.50, 244.29] | 539.83 [421.29, 616.47] | 0 | 0 |
| mixed-single-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 4.97 [4.63, 6.83] | 13,927.35 [13,310.18, 14,832.36] | 234 | 67 |
| mixed-single-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 778.21 [768.42, 780.20] | 115.13 [112.09, 119.00] | 0 | 0 |
| mixed-single-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 747.36 [690.00, 749.46] | 124.10 [123.01, 149.82] | 0 | 0 |
| mixed-single-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 1.47 [1.37, 3.40] | 811.14 [796.19, 9,177.78] | 514 | 318 |
| mixed-single-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,036.33 [1,036.10, 1,038.43] | 84.73 [83.57, 85.05] | 0 | 0 |
| mixed-single-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,020.13 [1,018.70, 1,022.70] | 86.30 [85.52, 87.55] | 0 | 0 |
| mixed-single-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 42.96 [37.70, 48.07] | 4,597.67 [4,193.99, 12,425.35] | 0 | 0 |
| mixed-single-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 439.97 [401.43, 448.86] | 191.50 [169.59, 205.68] | 0 | 0 |
| mixed-single-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 143.86 [140.83, 155.83] | 541.02 [536.86, 550.08] | 0 | 0 |
| mixed-single-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 61.60 [59.56, 62.80] | 2,509.79 [2,468.62, 2,963.71] | 0 | 0 |
| mixed-single-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 774.15 [764.16, 781.42] | 116.91 [115.22, 119.03] | 0 | 0 |
| mixed-single-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 729.26 [718.76, 749.79] | 126.56 [120.97, 127.75] | 0 | 0 |
| mixed-single-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 42.16 [39.10, 43.30] | 3,902.80 [3,679.49, 4,897.93] | 0 | 0 |
| mixed-single-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,034.80 [1,033.36, 1,038.80] | 83.58 [82.24, 84.67] | 0 | 0 |
| mixed-single-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,017.49 [1,015.16, 1,019.83] | 85.05 [84.35, 86.11] | 0 | 0 |
| network-delay-1 | 1c1t-g1 | baseline | 5/5; measured=5 | 172.63 [172.43, 174.16] | 413.69 [410.41, 431.59] | 0 | 0 |
| network-delay-1 | 1c1t-g1 | v000 | 5/5; measured=5 | 185.46 [59.70, 187.86] | 533.44 [532.87, 787.51] | 72 | 57 |
| network-delay-1 | 1c1t-g1 | v003 | 5/5; measured=5 | 96.86 [42.93, 198.57] | 3,932.75 [541.38, 11,705.38] | 137 | 117 |
| network-delay-1 | 2c2t-g2 | baseline | 5/5; measured=5 | 204.56 [203.86, 205.97] | 415.84 [406.06, 419.57] | 0 | 0 |
| network-delay-1 | 2c2t-g2 | v000 | 5/5; measured=5 | 119.26 [112.20, 263.20] | 10,687.05 [581.01, 12,472.48] | 0 | 0 |
| network-delay-1 | 2c2t-g2 | v003 | 5/5; measured=5 | 199.99 [52.83, 247.23] | 895.86 [499.63, 4,316.62] | 75 | 58 |
| network-delay-1 | 2c4t-g4 | baseline | 5/5; measured=5 | 204.47 [203.43, 205.23] | 399.51 [384.27, 411.85] | 0 | 0 |
| network-delay-1 | 2c4t-g4 | v000 | 5/5; measured=5 | 115.23 [112.20, 250.76] | 9,857.20 [588.22, 11,472.62] | 0 | 0 |
| network-delay-1 | 2c4t-g4 | v003 | 5/5; measured=5 | 206.80 [102.76, 255.19] | 481.19 [462.60, 9,854.07] | 0 | 0 |
| network-delay-5 | 1c1t-g1 | baseline | 5/5; measured=5 | 13.87 [13.80, 13.93] | 11,970.49 [11,414.75, 12,504.73] | 248 | 0 |
| network-delay-5 | 1c1t-g1 | v000 | 5/5; measured=5 | 7.83 [7.70, 7.93] | 13,795.75 [8,403.27, 14,255.74] | 341 | 263 |
| network-delay-5 | 1c1t-g1 | v003 | 5/5; measured=5 | 7.27 [7.17, 7.30] | 12,371.18 [11,814.79, 14,529.83] | 383 | 289 |
| network-delay-5 | 2c2t-g2 | baseline | 5/5; measured=5 | 15.37 [15.10, 15.47] | 13,200.78 [12,757.84, 13,350.11] | 247 | 0 |
| network-delay-5 | 2c2t-g2 | v000 | 5/5; measured=5 | 7.90 [7.90, 8.03] | 11,542.40 [8,700.87, 12,909.16] | 371 | 245 |
| network-delay-5 | 2c2t-g2 | v003 | 5/5; measured=5 | 7.50 [7.37, 7.70] | 12,442.56 [9,533.81, 13,892.42] | 362 | 276 |
| network-delay-5 | 2c4t-g4 | baseline | 5/5; measured=5 | 14.97 [14.87, 15.10] | 13,090.44 [11,692.34, 13,779.35] | 248 | 0 |
| network-delay-5 | 2c4t-g4 | v000 | 5/5; measured=5 | 7.70 [7.67, 7.93] | 7,381.42 [7,265.24, 11,868.40] | 355 | 219 |
| network-delay-5 | 2c4t-g4 | v003 | 5/5; measured=5 | 7.27 [7.23, 7.67] | 10,430.31 [10,217.40, 12,254.06] | 377 | 281 |
| payload-1024-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 91.47 [71.13, 117.20] | 10,991.91 [9,887.10, 13,042.67] | 0 | 0 |
| payload-1024-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 468.76 [443.83, 524.56] | 1,251.92 [1,041.69, 1,365.53] | 0 | 0 |
| payload-1024-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 257.49 [244.33, 288.83] | 4,173.56 [3,981.26, 4,256.24] | 0 | 0 |
| payload-1024-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 142.27 [120.30, 146.83] | 544.89 [511.37, 1,312.82] | 0 | 0 |
| payload-1024-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,157.13 [1,088.85, 1,271.86] | 351.44 [142.35, 476.83] | 0 | 0 |
| payload-1024-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 890.93 [858.25, 959.12] | 590.83 [556.79, 622.60] | 0 | 0 |
| payload-1024-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 30.27 [29.53, 30.67] | 13,266.84 [13,060.95, 13,746.45] | 198 | 0 |
| payload-1024-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,819.69 [1,759.57, 1,893.53] | 256.32 [95.58, 276.22] | 0 | 0 |
| payload-1024-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,631.63 [1,382.33, 1,670.47] | 267.26 [263.78, 358.88] | 0 | 0 |
| payload-1024-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 161.13 [135.33, 225.09] | 4,333.81 [3,243.62, 7,060.29] | 63 | 0 |
| payload-1024-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 492.03 [435.55, 523.29] | 1,232.49 [1,172.49, 2,538.92] | 0 | 0 |
| payload-1024-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 239.63 [203.23, 277.82] | 3,734.15 [3,639.00, 4,214.21] | 0 | 0 |
| payload-1024-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 273.50 [272.99, 274.33] | 3,263.82 [2,627.04, 3,402.24] | 0 | 0 |
| payload-1024-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,236.40 [1,169.43, 1,296.23] | 352.02 [117.58, 362.85] | 0 | 0 |
| payload-1024-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 864.59 [848.66, 961.56] | 598.61 [549.84, 600.83] | 0 | 0 |
| payload-1024-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 163.06 [142.66, 233.07] | 4,938.47 [4,070.15, 5,150.99] | 0 | 0 |
| payload-1024-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,878.71 [1,835.39, 1,906.13] | 104.59 [94.19, 240.97] | 0 | 0 |
| payload-1024-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,628.99 [1,326.61, 1,668.09] | 269.10 [264.59, 376.73] | 0 | 0 |
| payload-16384-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 7.53 [7.33, 7.80] | 11,293.25 [10,783.03, 11,624.88] | 161 | 158 |
| payload-16384-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 97.40 [51.00, 163.90] | 2,275.88 [607.80, 11,364.29] | 148 | 77 |
| payload-16384-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 44.13 [37.73, 45.90] | 5,114.16 [2,737.14, 5,833.43] | 350 | 249 |
| payload-16384-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 8.60 [8.47, 8.93] | 10,869.52 [8,754.56, 11,653.77] | 167 | 1 |
| payload-16384-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 139.83 [137.73, 263.16] | 6,724.44 [567.86, 6,828.59] | 0 | 0 |
| payload-16384-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 150.93 [119.76, 184.43] | 6,595.97 [2,079.62, 6,935.84] | 0 | 0 |
| payload-16384-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 6.80 [6.80, 6.80] | 11,976.42 [11,872.56, 12,054.19] | 150 | 150 |
| payload-16384-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 154.46 [152.93, 162.80] | 10,677.73 [10,401.02, 11,134.57] | 0 | 0 |
| payload-16384-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 293.30 [150.46, 333.30] | 729.68 [505.27, 11,664.40] | 0 | 0 |
| payload-16384-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 28.13 [23.13, 30.23] | 12,695.04 [12,383.45, 13,386.89] | 78 | 0 |
| payload-16384-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 100.73 [58.20, 123.00] | 2,411.13 [2,011.20, 2,693.40] | 234 | 126 |
| payload-16384-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 41.77 [40.37, 43.73] | 3,761.34 [782.87, 5,211.05] | 341 | 257 |
| payload-16384-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 78.90 [58.33, 99.30] | 7,100.35 [5,716.98, 7,843.50] | 0 | 0 |
| payload-16384-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 132.10 [87.26, 248.60] | 6,778.74 [1,007.16, 12,511.13] | 0 | 0 |
| payload-16384-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 132.93 [120.93, 248.33] | 6,809.06 [482.82, 6,860.40] | 0 | 0 |
| payload-16384-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 83.20 [75.93, 92.27] | 7,747.68 [4,521.90, 8,014.33] | 0 | 0 |
| payload-16384-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 151.70 [89.30, 166.07] | 10,562.57 [6,847.70, 12,623.95] | 142 | 66 |
| payload-16384-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 150.43 [84.70, 329.30] | 11,134.24 [488.62, 11,588.83] | 64 | 60 |
| payload-65536-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 1.77 [1.50, 2.23] | 12,889.77 [1,550.50, 14,314.59] | 371 | 320 |
| payload-65536-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 8.50 [8.40, 8.53] | 14,153.01 [13,639.67, 14,543.22] | 356 | 250 |
| payload-65536-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 7.53 [7.43, 7.77] | 12,630.89 [10,413.88, 13,424.14] | 401 | 242 |
| payload-65536-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 2.70 [2.63, 2.83] | 14,590.41 [14,082.95, 14,919.40] | 381 | 206 |
| payload-65536-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 19.60 [19.37, 20.07] | 3,531.77 [2,468.72, 4,552.65] | 320 | 320 |
| payload-65536-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 17.97 [17.73, 18.20] | 5,416.85 [4,022.84, 6,361.27] | 320 | 320 |
| payload-65536-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 2.33 [2.10, 2.40] | 14,610.98 [14,508.52, 14,944.83] | 443 | 245 |
| payload-65536-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 21.23 [19.80, 21.47] | 2,426.79 [1,374.90, 2,877.88] | 321 | 311 |
| payload-65536-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 18.90 [18.90, 19.60] | 2,745.41 [2,279.17, 3,342.16] | 320 | 320 |
| payload-65536-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 7.53 [7.33, 7.70] | 10,962.73 [10,574.99, 11,863.83] | 136 | 0 |
| payload-65536-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 8.50 [8.33, 8.53] | 14,201.45 [13,791.80, 14,649.71] | 361 | 261 |
| payload-65536-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 7.50 [7.47, 7.57] | 11,231.14 [10,467.11, 12,584.05] | 389 | 217 |
| payload-65536-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 15.77 [15.00, 17.87] | 12,288.99 [11,770.66, 12,749.74] | 170 | 0 |
| payload-65536-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 19.83 [19.37, 20.70] | 4,978.26 [3,408.90, 5,781.31] | 319 | 319 |
| payload-65536-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 17.73 [16.33, 17.97] | 5,450.69 [4,138.03, 5,942.47] | 310 | 310 |
| payload-65536-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 21.27 [19.10, 21.47] | 12,619.12 [12,229.36, 13,494.98] | 156 | 0 |
| payload-65536-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 20.77 [20.30, 21.70] | 2,207.38 [2,019.89, 2,717.69] | 320 | 320 |
| payload-65536-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 18.90 [18.67, 19.37] | 2,751.86 [2,258.53, 3,089.55] | 320 | 320 |
| read-heavy-balanced-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 109.03 [75.43, 136.50] | 10,615.79 [8,430.85, 13,722.63] | 39 | 0 |
| read-heavy-balanced-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 444.73 [441.93, 456.69] | 1,287.68 [1,219.86, 1,321.09] | 0 | 0 |
| read-heavy-balanced-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 233.83 [228.43, 253.69] | 2,940.54 [2,878.54, 3,085.02] | 0 | 0 |
| read-heavy-balanced-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 137.83 [129.80, 168.26] | 7,723.38 [3,713.98, 8,024.09] | 0 | 0 |
| read-heavy-balanced-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 903.40 [897.19, 906.83] | 523.95 [517.17, 527.12] | 0 | 0 |
| read-heavy-balanced-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 919.51 [862.86, 965.76] | 589.95 [503.30, 667.71] | 0 | 0 |
| read-heavy-balanced-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 42.43 [41.70, 63.83] | 9,722.89 [9,335.76, 10,034.29] | 0 | 0 |
| read-heavy-balanced-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,501.47 [1,478.60, 1,517.15] | 499.71 [483.30, 515.63] | 0 | 0 |
| read-heavy-balanced-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,464.29 [1,460.43, 1,471.59] | 324.02 [321.85, 338.15] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 204.33 [179.90, 226.26] | 4,178.29 [3,357.39, 5,304.94] | 8 | 0 |
| read-heavy-balanced-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 444.60 [434.16, 447.43] | 1,309.18 [1,283.10, 1,338.75] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 241.39 [210.33, 263.16] | 2,961.26 [2,771.63, 3,443.31] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 351.33 [313.46, 355.60] | 2,705.20 [2,121.60, 3,081.65] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 924.89 [917.69, 928.86] | 525.02 [508.50, 531.69] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 877.97 [824.95, 986.52] | 629.40 [483.78, 663.84] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 248.96 [183.60, 363.42] | 3,556.64 [3,026.60, 4,356.10] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,485.85 [1,450.92, 1,498.74] | 502.60 [474.35, 533.02] | 0 | 0 |
| read-heavy-balanced-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,460.09 [1,446.88, 1,464.29] | 331.63 [327.39, 337.73] | 0 | 0 |
| read-heavy-random-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 113.23 [93.03, 135.63] | 12,696.06 [11,054.59, 13,966.53] | 0 | 0 |
| read-heavy-random-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 437.76 [434.56, 467.66] | 1,320.16 [1,268.03, 1,499.79] | 0 | 0 |
| read-heavy-random-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 236.46 [218.43, 269.92] | 3,039.22 [2,965.07, 3,224.75] | 0 | 0 |
| read-heavy-random-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 190.40 [184.30, 201.57] | 2,070.39 [1,748.92, 2,456.27] | 0 | 0 |
| read-heavy-random-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 901.93 [895.36, 905.15] | 513.26 [507.30, 527.53] | 0 | 0 |
| read-heavy-random-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 927.70 [886.63, 973.36] | 571.23 [469.71, 633.62] | 0 | 0 |
| read-heavy-random-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 60.07 [54.10, 62.60] | 8,848.14 [7,316.54, 11,639.53] | 0 | 0 |
| read-heavy-random-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,483.89 [1,467.39, 1,510.49] | 483.44 [479.69, 503.75] | 0 | 0 |
| read-heavy-random-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,446.87 [1,436.00, 1,453.25] | 333.04 [325.50, 335.88] | 0 | 0 |
| read-heavy-random-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 235.20 [203.63, 254.10] | 4,171.77 [2,819.18, 4,918.17] | 0 | 0 |
| read-heavy-random-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 438.63 [430.66, 459.77] | 1,328.14 [1,255.20, 1,473.83] | 0 | 0 |
| read-heavy-random-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 241.46 [225.56, 258.26] | 3,090.91 [3,059.57, 3,367.63] | 0 | 0 |
| read-heavy-random-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 305.30 [261.80, 343.28] | 3,295.29 [2,044.40, 6,817.45] | 0 | 0 |
| read-heavy-random-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 903.53 [889.95, 904.53] | 519.92 [506.36, 521.56] | 0 | 0 |
| read-heavy-random-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 959.63 [851.29, 973.44] | 504.03 [449.73, 670.34] | 0 | 0 |
| read-heavy-random-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 245.16 [193.87, 254.59] | 3,484.73 [3,295.78, 6,686.39] | 0 | 0 |
| read-heavy-random-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,451.36 [1,448.86, 1,471.46] | 493.65 [480.26, 495.25] | 0 | 0 |
| read-heavy-random-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,439.14 [1,428.76, 1,445.39] | 338.79 [329.00, 348.57] | 0 | 0 |
| read-heavy-single-n64-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 2.93 [1.43, 3.07] | 11,183.52 [790.33, 14,859.39] | 486 | 169 |
| read-heavy-single-n64-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 442.40 [435.46, 453.66] | 193.48 [172.06, 195.61] | 0 | 0 |
| read-heavy-single-n64-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 142.86 [140.56, 261.76] | 530.85 [489.44, 573.14] | 0 | 0 |
| read-heavy-single-n64-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 5.93 [5.30, 7.60] | 14,854.65 [14,400.04, 14,895.74] | 236 | 146 |
| read-heavy-single-n64-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 778.46 [770.27, 784.85] | 114.81 [114.45, 119.79] | 0 | 0 |
| read-heavy-single-n64-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 752.35 [735.88, 759.13] | 123.94 [119.92, 128.39] | 0 | 0 |
| read-heavy-single-n64-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 3.20 [1.40, 3.30] | 9,224.04 [798.77, 9,625.49] | 451 | 317 |
| read-heavy-single-n64-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,043.97 [1,041.36, 1,048.20] | 83.62 [82.75, 83.92] | 0 | 0 |
| read-heavy-single-n64-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,030.03 [1,027.06, 1,030.69] | 85.03 [83.74, 86.36] | 0 | 0 |
| read-heavy-single-n64-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 49.57 [43.67, 57.16] | 4,209.15 [3,185.60, 4,922.06] | 0 | 0 |
| read-heavy-single-n64-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 441.40 [426.63, 447.77] | 192.73 [187.60, 195.97] | 0 | 0 |
| read-heavy-single-n64-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 148.86 [141.30, 150.37] | 563.69 [526.14, 735.09] | 0 | 0 |
| read-heavy-single-n64-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 62.63 [61.13, 63.83] | 2,600.43 [2,555.85, 2,934.10] | 0 | 0 |
| read-heavy-single-n64-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 783.76 [768.60, 795.35] | 114.97 [114.08, 119.86] | 0 | 0 |
| read-heavy-single-n64-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 734.65 [696.43, 751.90] | 125.67 [120.65, 144.83] | 0 | 0 |
| read-heavy-single-n64-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 41.93 [39.10, 44.20] | 3,800.53 [3,360.43, 5,220.87] | 0 | 0 |
| read-heavy-single-n64-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 1,042.53 [1,039.99, 1,044.92] | 83.36 [82.64, 84.76] | 0 | 0 |
| read-heavy-single-n64-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,024.06 [1,022.53, 1,027.34] | 84.86 [83.30, 85.92] | 0 | 0 |
| slots-k1 | 1c1t-g1 | baseline | 5/5; measured=5 | 583.33 [581.78, 585.16] | 470.51 [425.30, 676.65] | 0 | 0 |
| slots-k1 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,192.62 [1,179.92, 1,216.99] | 322.45 [316.26, 354.55] | 0 | 0 |
| slots-k1 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,181.03 [1,147.16, 1,191.05] | 335.61 [328.69, 349.90] | 0 | 0 |
| slots-k1 | 2c2t-g2 | baseline | 5/5; measured=5 | 695.73 [694.29, 697.80] | 195.64 [161.18, 223.69] | 0 | 0 |
| slots-k1 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,530.52 [1,518.13, 1,543.49] | 200.51 [186.23, 236.05] | 0 | 0 |
| slots-k1 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,509.72 [1,501.56, 1,517.16] | 205.05 [188.57, 213.54] | 0 | 0 |
| slots-k1 | 2c4t-g4 | baseline | 5/5; measured=5 | 699.40 [699.36, 699.70] | 106.10 [103.38, 106.84] | 0 | 0 |
| slots-k1 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,471.19 [2,433.78, 2,481.66] | 131.04 [118.25, 139.33] | 0 | 0 |
| slots-k1 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,436.52 [2,418.83, 2,446.32] | 140.45 [134.50, 155.86] | 0 | 0 |
| slots-k256 | 1c1t-g1 | baseline | 5/5; measured=5 | 178.10 [174.43, 193.06] | 3,986.22 [3,870.36, 8,666.14] | 0 | 0 |
| slots-k256 | 1c1t-g1 | v000 | 5/5; measured=5 | 729.76 [684.06, 751.49] | 742.62 [707.71, 874.27] | 0 | 0 |
| slots-k256 | 1c1t-g1 | v003 | 5/5; measured=5 | 435.13 [311.02, 461.39] | 1,639.75 [1,333.25, 2,764.07] | 0 | 0 |
| slots-k256 | 2c2t-g2 | baseline | 5/5; measured=5 | 319.67 [303.53, 363.90] | 2,612.00 [2,175.38, 2,773.12] | 0 | 0 |
| slots-k256 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,522.09 [1,328.23, 1,526.83] | 108.61 [97.78, 324.34] | 0 | 0 |
| slots-k256 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,247.30 [1,077.65, 1,402.24] | 390.31 [324.28, 475.31] | 0 | 0 |
| slots-k256 | 2c4t-g4 | baseline | 5/5; measured=5 | 230.03 [182.30, 273.40] | 3,623.42 [3,481.30, 4,227.63] | 0 | 0 |
| slots-k256 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,303.15 [2,287.37, 2,384.81] | 115.61 [87.68, 150.50] | 0 | 0 |
| slots-k256 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,231.73 [1,906.31, 2,280.76] | 159.94 [99.19, 245.27] | 0 | 0 |
| slots-k8 | 1c1t-g1 | baseline | 5/5; measured=5 | 570.16 [567.43, 587.43] | 610.62 [576.16, 663.47] | 0 | 0 |
| slots-k8 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,184.03 [1,171.70, 1,206.77] | 187.99 [164.87, 290.25] | 0 | 0 |
| slots-k8 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,147.86 [1,141.73, 1,167.16] | 216.22 [177.67, 271.22] | 0 | 0 |
| slots-k8 | 2c2t-g2 | baseline | 5/5; measured=5 | 758.30 [743.33, 771.32] | 456.83 [449.27, 460.80] | 0 | 0 |
| slots-k8 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,522.65 [1,519.56, 1,550.56] | 180.66 [171.89, 198.15] | 0 | 0 |
| slots-k8 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,524.26 [1,499.96, 1,535.86] | 180.18 [162.51, 198.49] | 0 | 0 |
| slots-k8 | 2c4t-g4 | baseline | 5/5; measured=5 | 1,192.36 [1,171.69, 1,211.40] | 269.91 [261.56, 282.42] | 0 | 0 |
| slots-k8 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,401.05 [2,374.19, 2,417.60] | 107.78 [91.02, 147.02] | 0 | 0 |
| slots-k8 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,377.09 [2,356.06, 2,405.32] | 125.31 [96.83, 155.63] | 0 | 0 |
| trace-accept-p1 | 1c1t-g1 | baseline | 5/5; measured=5 | 117.23 [115.27, 118.53] | 332.23 [321.96, 340.19] | 0 | 0 |
| trace-accept-p1 | 1c1t-g1 | v000 | 5/5; measured=5 | 125.87 [125.86, 125.93] | 289.05 [282.09, 300.22] | 0 | 0 |
| trace-accept-p1 | 1c1t-g1 | v003 | 5/5; measured=5 | 125.86 [125.86, 125.87] | 281.54 [280.25, 282.38] | 0 | 0 |
| trace-accept-p1 | 2c2t-g2 | baseline | 5/5; measured=5 | 11.97 [10.23, 15.23] | 5,081.56 [4,912.44, 5,140.83] | 0 | 0 |
| trace-accept-p1 | 2c2t-g2 | v000 | 5/5; measured=5 | 126.20 [126.03, 126.93] | 276.74 [275.74, 280.22] | 0 | 0 |
| trace-accept-p1 | 2c2t-g2 | v003 | 5/5; measured=5 | 131.20 [130.50, 135.27] | 275.92 [273.74, 277.65] | 0 | 0 |
| trace-accept-p1 | 2c4t-g4 | baseline | 5/5; measured=5 | 5.07 [4.93, 5.17] | 8,516.26 [8,430.16, 8,575.41] | 0 | 0 |
| trace-accept-p1 | 2c4t-g4 | v000 | 5/5; measured=5 | 125.86 [125.86, 125.87] | 264.68 [262.86, 269.08] | 0 | 0 |
| trace-accept-p1 | 2c4t-g4 | v003 | 5/5; measured=5 | 125.90 [125.86, 134.40] | 264.97 [262.62, 269.19] | 0 | 0 |
| trace-accept-p4 | 1c1t-g1 | baseline | 5/5; measured=5 | 131.40 [131.00, 131.57] | 272.60 [271.51, 273.81] | 0 | 0 |
| trace-accept-p4 | 1c1t-g1 | v000 | 5/5; measured=5 | 125.86 [125.86, 125.87] | 284.74 [282.81, 286.43] | 0 | 0 |
| trace-accept-p4 | 1c1t-g1 | v003 | 5/5; measured=5 | 125.87 [125.86, 126.80] | 282.01 [281.03, 286.24] | 0 | 0 |
| trace-accept-p4 | 2c2t-g2 | baseline | 5/5; measured=5 | 133.90 [133.16, 134.20] | 262.02 [261.79, 266.32] | 0 | 0 |
| trace-accept-p4 | 2c2t-g2 | v000 | 5/5; measured=5 | 126.20 [125.86, 126.53] | 277.19 [271.98, 279.46] | 0 | 0 |
| trace-accept-p4 | 2c2t-g2 | v003 | 5/5; measured=5 | 129.13 [125.86, 131.20] | 280.00 [276.99, 286.07] | 0 | 0 |
| trace-accept-p4 | 2c4t-g4 | baseline | 5/5; measured=5 | 134.46 [133.70, 134.63] | 260.13 [259.82, 261.17] | 0 | 0 |
| trace-accept-p4 | 2c4t-g4 | v000 | 5/5; measured=5 | 126.66 [125.90, 128.27] | 270.20 [268.24, 274.46] | 0 | 0 |
| trace-accept-p4 | 2c4t-g4 | v003 | 5/5; measured=5 | 129.06 [125.86, 136.13] | 276.07 [274.01, 277.47] | 0 | 0 |
| window-1000 | 1c1t-g1 | baseline | 5/5; measured=5 | 345.26 [333.69, 354.83] | 1,492.86 [1,416.28, 1,663.80] | 0 | 0 |
| window-1000 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,146.70 [1,131.11, 1,164.26] | 189.49 [168.03, 246.86] | 0 | 0 |
| window-1000 | 1c1t-g1 | v003 | 5/5; measured=5 | 1,136.49 [1,118.85, 1,151.43] | 160.86 [144.11, 203.20] | 0 | 0 |
| window-1000 | 2c2t-g2 | baseline | 5/5; measured=5 | 418.16 [414.70, 420.69] | 1,585.43 [1,539.30, 1,611.28] | 0 | 0 |
| window-1000 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,531.16 [1,521.13, 1,547.83] | 103.32 [100.82, 128.26] | 0 | 0 |
| window-1000 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,528.96 [1,519.86, 1,546.26] | 104.49 [101.48, 122.77] | 0 | 0 |
| window-1000 | 2c4t-g4 | baseline | 5/5; measured=5 | 240.66 [236.90, 246.80] | 2,725.81 [2,600.47, 2,900.54] | 2 | 0 |
| window-1000 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,348.56 [2,321.56, 2,373.72] | 130.50 [84.50, 148.20] | 0 | 0 |
| window-1000 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,348.36 [2,257.49, 2,361.71] | 131.30 [83.37, 175.73] | 0 | 0 |
| window-50 | 1c1t-g1 | baseline | 5/5; measured=5 | 135.96 [130.00, 136.30] | 3,447.50 [3,342.80, 3,534.31] | 0 | 0 |
| window-50 | 1c1t-g1 | v000 | 5/5; measured=5 | 625.25 [77.83, 691.70] | 202.57 [198.90, 11,216.35] | 99 | 0 |
| window-50 | 1c1t-g1 | v003 | 5/5; measured=5 | 180.46 [53.17, 494.66] | 3,429.84 [192.13, 12,610.49] | 276 | 29 |
| window-50 | 2c2t-g2 | baseline | 5/5; measured=5 | 295.99 [212.60, 358.77] | 1,926.56 [1,494.01, 2,052.79] | 0 | 0 |
| window-50 | 2c2t-g2 | v000 | 5/5; measured=5 | 795.00 [275.69, 846.60] | 314.31 [145.84, 2,285.07] | 0 | 0 |
| window-50 | 2c2t-g2 | v003 | 5/5; measured=5 | 589.96 [258.60, 763.61] | 324.91 [136.06, 2,255.84] | 0 | 0 |
| window-50 | 2c4t-g4 | baseline | 5/5; measured=5 | 210.37 [183.10, 268.59] | 3,502.79 [3,396.94, 3,940.30] | 0 | 0 |
| window-50 | 2c4t-g4 | v000 | 5/5; measured=5 | 332.00 [329.29, 1,214.93] | 1,957.78 [1,405.92, 1,968.77] | 0 | 0 |
| window-50 | 2c4t-g4 | v003 | 5/5; measured=5 | 298.17 [97.30, 305.80] | 2,193.76 [2,051.27, 9,502.07] | 0 | 0 |

## history

| 场景 | CPU | 版本 | 完成 / 计划；状态次数 | 吞吐（条/秒） | 成功 p99（毫秒） | 非成功回复（条） | 收尾缺决定（条） |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| cold-h100 | 1c1t-g1 | baseline | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 2c2t-g2 | baseline | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 2c4t-g4 | baseline | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h100 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h1000 | 1c1t-g1 | baseline | 5/5; observed_failure=5; 历史未排空=5 | — | — | — | — |
| cold-h1000 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h1000 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h1000 | 2c2t-g2 | baseline | 5/5; observed_failure=5; 历史未排空=5 | — | — | — | — |
| cold-h1000 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h1000 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h1000 | 2c4t-g4 | baseline | 5/5; observed_failure=5; 历史未排空=5 | — | — | — | — |
| cold-h1000 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h1000 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h5000 | 1c1t-g1 | baseline | 5/5; observed_failure=5; 历史未排空=5 | — | — | — | — |
| cold-h5000 | 1c1t-g1 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h5000 | 1c1t-g1 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h5000 | 2c2t-g2 | baseline | 5/5; observed_failure=5; 历史未排空=5 | — | — | — | — |
| cold-h5000 | 2c2t-g2 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h5000 | 2c2t-g2 | v003 | 5/5; passed=5 | — | — | — | — |
| cold-h5000 | 2c4t-g4 | baseline | 5/5; observed_failure=5; 历史未排空=5 | — | — | — | — |
| cold-h5000 | 2c4t-g4 | v000 | 5/5; passed=5 | — | — | — | — |
| cold-h5000 | 2c4t-g4 | v003 | 5/5; passed=5 | — | — | — | — |
| completed-h0 | 1c1t-g1 | baseline | 5/5; measured=5 | 182.03 [152.70, 214.73] | 3,976.99 [3,460.59, 4,975.64] | 0 | 0 |
| completed-h0 | 1c1t-g1 | v000 | 5/5; measured=5 | 716.59 [689.93, 757.83] | 732.95 [713.89, 960.45] | 0 | 0 |
| completed-h0 | 1c1t-g1 | v003 | 5/5; measured=5 | 381.19 [358.62, 464.63] | 2,780.57 [1,403.74, 2,940.61] | 0 | 0 |
| completed-h0 | 2c2t-g2 | baseline | 5/5; measured=5 | 347.26 [280.96, 371.30] | 2,550.55 [2,169.28, 4,227.62] | 0 | 0 |
| completed-h0 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,531.85 [1,354.56, 1,542.16] | 105.35 [96.27, 324.92] | 0 | 0 |
| completed-h0 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,230.06 [1,148.19, 1,263.66] | 387.32 [376.49, 480.77] | 0 | 0 |
| completed-h0 | 2c4t-g4 | baseline | 5/5; measured=5 | 228.09 [180.80, 247.86] | 3,690.51 [3,494.15, 4,299.69] | 0 | 0 |
| completed-h0 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,286.33 [2,282.96, 2,351.02] | 128.21 [89.16, 164.98] | 0 | 0 |
| completed-h0 | 2c4t-g4 | v003 | 5/5; measured=5 | 1,907.16 [1,851.06, 1,972.69] | 249.64 [244.17, 261.73] | 0 | 0 |
| completed-h1000 | 1c1t-g1 | baseline | 5/5; measured=5 | 189.73 [170.77, 231.00] | 4,034.18 [3,930.06, 5,830.75] | 0 | 0 |
| completed-h1000 | 1c1t-g1 | v000 | 5/5; measured=5 | 699.59 [646.46, 764.80] | 742.79 [713.78, 951.19] | 0 | 0 |
| completed-h1000 | 1c1t-g1 | v003 | 5/5; measured=5 | 294.69 [290.13, 445.13] | 2,928.37 [1,460.80, 3,349.25] | 0 | 0 |
| completed-h1000 | 2c2t-g2 | baseline | 5/5; measured=5 | 331.36 [315.19, 348.96] | 2,570.95 [2,152.51, 2,740.91] | 0 | 0 |
| completed-h1000 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,362.61 [1,326.33, 1,520.49] | 319.86 [106.16, 325.22] | 0 | 0 |
| completed-h1000 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,224.00 [1,202.90, 1,297.03] | 387.44 [351.48, 432.48] | 0 | 0 |
| completed-h1000 | 2c4t-g4 | baseline | 5/5; measured=5 | 189.33 [184.13, 246.86] | 4,120.92 [3,523.23, 4,305.64] | 0 | 0 |
| completed-h1000 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,323.70 [2,291.45, 2,349.01] | 139.41 [92.45, 174.59] | 0 | 0 |
| completed-h1000 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,260.72 [2,163.46, 2,276.69] | 160.75 [81.65, 240.70] | 0 | 0 |
| completed-h10000 | 1c1t-g1 | baseline | 5/5; measured=5 | 249.36 [195.19, 300.43] | 3,073.30 [2,403.81, 4,808.47] | 0 | 0 |
| completed-h10000 | 1c1t-g1 | v000 | 5/5; measured=5 | 1,097.60 [1,085.53, 1,105.35] | 184.63 [155.51, 186.62] | 0 | 0 |
| completed-h10000 | 1c1t-g1 | v003 | 5/5; measured=5 | 647.76 [432.25, 1,064.23] | 1,895.23 [169.61, 2,173.24] | 0 | 0 |
| completed-h10000 | 2c2t-g2 | baseline | 5/5; measured=5 | 309.76 [283.36, 332.50] | 2,923.61 [1,947.00, 3,405.47] | 0 | 0 |
| completed-h10000 | 2c2t-g2 | v000 | 5/5; measured=5 | 1,487.94 [1,477.90, 1,509.56] | 125.97 [108.23, 252.23] | 0 | 0 |
| completed-h10000 | 2c2t-g2 | v003 | 5/5; measured=5 | 1,287.26 [1,071.42, 1,337.47] | 383.48 [310.52, 488.46] | 0 | 0 |
| completed-h10000 | 2c4t-g4 | baseline | 5/5; measured=5 | 189.26 [185.50, 224.26] | 3,702.86 [3,546.42, 4,595.47] | 0 | 0 |
| completed-h10000 | 2c4t-g4 | v000 | 5/5; measured=5 | 2,280.26 [2,235.00, 2,294.12] | 124.21 [77.12, 169.79] | 0 | 0 |
| completed-h10000 | 2c4t-g4 | v003 | 5/5; measured=5 | 2,132.14 [1,930.23, 2,229.49] | 241.13 [95.05, 252.89] | 0 | 0 |
| idle-h0 | 1c1t-g1 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 1c1t-g1 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 1c1t-g1 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 2c2t-g2 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 2c2t-g2 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 2c2t-g2 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 2c4t-g4 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 2c4t-g4 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h0 | 2c4t-g4 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 1c1t-g1 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 1c1t-g1 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 1c1t-g1 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 2c2t-g2 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 2c2t-g2 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 2c2t-g2 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 2c4t-g4 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 2c4t-g4 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h1000 | 2c4t-g4 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 1c1t-g1 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 1c1t-g1 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 1c1t-g1 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 2c2t-g2 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 2c2t-g2 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 2c2t-g2 | v003 | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 2c4t-g4 | baseline | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 2c4t-g4 | v000 | 5/5; measured=5 | — | — | — | — |
| idle-h10000 | 2c4t-g4 | v003 | 5/5; measured=5 | — | — | — | — |
| pending-h1000 | 1c1t-g1 | baseline | 5/5; measured=5 | 267.87 [266.63, 269.19] | 83.50 [82.90, 85.04] | 0 | 0 |
| pending-h1000 | 1c1t-g1 | v000 | 5/5; measured=5; 历史未排空=5 | 617.20 [616.86, 618.23] | 49.11 [48.83, 49.94] | 0 | 0 |
| pending-h1000 | 1c1t-g1 | v003 | 5/5; measured=5; 历史未排空=5 | 634.10 [633.20, 634.88] | 48.77 [48.03, 50.10] | 0 | 0 |
| pending-h1000 | 2c2t-g2 | baseline | 5/5; measured=5 | 370.73 [368.86, 376.17] | 58.80 [57.75, 61.73] | 0 | 0 |
| pending-h1000 | 2c2t-g2 | v000 | 5/5; measured=5; 历史未排空=5 | 968.66 [957.93, 972.02] | 29.11 [28.71, 29.23] | 0 | 0 |
| pending-h1000 | 2c2t-g2 | v003 | 5/5; measured=5; 历史未排空=5 | 981.53 [974.30, 995.40] | 28.32 [28.14, 28.87] | 0 | 0 |
| pending-h1000 | 2c4t-g4 | baseline | 5/5; measured=5 | 234.40 [233.43, 235.00] | 77.73 [77.19, 78.36] | 0 | 0 |
| pending-h1000 | 2c4t-g4 | v000 | 5/5; measured=5; 历史未排空=5 | 1,354.03 [1,351.30, 1,359.19] | 21.10 [20.77, 21.16] | 0 | 0 |
| pending-h1000 | 2c4t-g4 | v003 | 5/5; measured=5; 历史未排空=5 | 1,364.58 [1,361.83, 1,371.40] | 20.97 [20.69, 21.31] | 0 | 0 |
| pending-h10000 | 1c1t-g1 | baseline | 5/5; measured=5; 历史未排空=5 | 8.13 [6.47, 8.87] | 13,846.55 [7,339.85, 14,159.05] | 84 | 43 |
| pending-h10000 | 1c1t-g1 | v000 | 5/5; measured=5; 历史未排空=5 | 423.70 [423.66, 423.79] | 69.15 [69.10, 70.37] | 0 | 0 |
| pending-h10000 | 1c1t-g1 | v003 | 5/5; measured=5; 历史未排空=5 | 623.03 [620.28, 623.09] | 51.16 [50.92, 51.75] | 0 | 0 |
| pending-h10000 | 2c2t-g2 | baseline | 5/5; measured=5 | 103.50 [103.00, 106.60] | 1,504.50 [1,488.16, 1,549.73] | 26 | 24 |
| pending-h10000 | 2c2t-g2 | v000 | 5/5; measured=5; 历史未排空=5 | 774.70 [771.43, 780.10] | 39.33 [38.45, 39.72] | 0 | 0 |
| pending-h10000 | 2c2t-g2 | v003 | 5/5; measured=5; 历史未排空=5 | 991.09 [985.72, 995.49] | 29.03 [28.65, 29.43] | 0 | 0 |
| pending-h10000 | 2c4t-g4 | baseline | 5/5; measured=5 | 13.97 [13.27, 14.30] | 11,241.17 [11,210.35, 11,253.84] | 4 | 4 |
| pending-h10000 | 2c4t-g4 | v000 | 5/5; measured=5; 历史未排空=5 | 1,216.74 [1,209.42, 1,219.81] | 28.07 [27.89, 28.58] | 0 | 0 |
| pending-h10000 | 2c4t-g4 | v003 | 5/5; measured=5; 历史未排空=5 | 1,340.86 [1,337.23, 1,346.53] | 21.29 [21.16, 21.56] | 0 | 0 |

| 场景 | CPU | 版本 | 冷读取完成（毫秒） | 副本 CPU 合计（%，单逻辑 CPU=100%） | 分配合计（MiB/秒） |
| --- | --- | --- | ---: | ---: | ---: |
| cold-h100 | 1c1t-g1 | baseline | 6,722.65 [6,653.31, 6,781.84] | — | — |
| cold-h100 | 1c1t-g1 | v000 | 1,039.85 [1,039.56, 1,239.40] | — | — |
| cold-h100 | 1c1t-g1 | v003 | 1,242.30 [1,238.71, 1,249.60] | — | — |
| cold-h100 | 2c2t-g2 | baseline | 4,565.29 [4,555.07, 4,599.66] | — | — |
| cold-h100 | 2c2t-g2 | v000 | 1,229.90 [1,226.11, 1,231.89] | — | — |
| cold-h100 | 2c2t-g2 | v003 | 1,232.27 [1,184.80, 1,235.03] | — | — |
| cold-h100 | 2c4t-g4 | baseline | 4,997.85 [4,954.50, 5,034.40] | — | — |
| cold-h100 | 2c4t-g4 | v000 | 1,226.31 [1,224.06, 1,233.20] | — | — |
| cold-h100 | 2c4t-g4 | v003 | 1,228.54 [1,223.60, 1,232.76] | — | — |
| cold-h1000 | 1c1t-g1 | baseline | 15,005.92 [15,004.52, 15,033.72] | — | — |
| cold-h1000 | 1c1t-g1 | v000 | 1,068.98 [1,062.65, 1,264.23] | — | — |
| cold-h1000 | 1c1t-g1 | v003 | 1,265.53 [1,062.69, 1,273.25] | — | — |
| cold-h1000 | 2c2t-g2 | baseline | 15,008.38 [15,002.59, 15,018.41] | — | — |
| cold-h1000 | 2c2t-g2 | v000 | 1,156.09 [1,081.29, 1,238.00] | — | — |
| cold-h1000 | 2c2t-g2 | v003 | 1,089.66 [1,029.45, 1,101.98] | — | — |
| cold-h1000 | 2c4t-g4 | baseline | 15,003.40 [15,003.08, 15,010.42] | — | — |
| cold-h1000 | 2c4t-g4 | v000 | 1,072.09 [1,041.68, 1,245.17] | — | — |
| cold-h1000 | 2c4t-g4 | v003 | 1,041.68 [1,036.66, 1,242.33] | — | — |
| cold-h5000 | 1c1t-g1 | baseline | 15,009.04 [15,002.50, 15,051.01] | — | — |
| cold-h5000 | 1c1t-g1 | v000 | 4,099.03 [4,006.50, 4,262.57] | — | — |
| cold-h5000 | 1c1t-g1 | v003 | 4,022.47 [4,005.43, 4,079.49] | — | — |
| cold-h5000 | 2c2t-g2 | baseline | 15,006.62 [15,002.76, 15,010.16] | — | — |
| cold-h5000 | 2c2t-g2 | v000 | 4,024.51 [3,853.04, 4,192.00] | — | — |
| cold-h5000 | 2c2t-g2 | v003 | 3,875.54 [3,819.23, 3,945.17] | — | — |
| cold-h5000 | 2c4t-g4 | baseline | 15,003.19 [15,002.47, 15,006.52] | — | — |
| cold-h5000 | 2c4t-g4 | v000 | 4,131.30 [4,036.79, 4,283.25] | — | — |
| cold-h5000 | 2c4t-g4 | v003 | 4,103.26 [4,077.28, 4,237.02] | — | — |
| completed-h0 | 1c1t-g1 | baseline | — | 560.56 [550.00, 563.27] | 1,061.22 [1,035.65, 1,090.78] |
| completed-h0 | 1c1t-g1 | v000 | — | 548.19 [544.56, 575.27] | 666.99 [661.22, 700.98] |
| completed-h0 | 1c1t-g1 | v003 | — | 499.67 [493.65, 513.28] | 514.28 [508.44, 565.96] |
| completed-h0 | 2c2t-g2 | baseline | — | 994.37 [937.89, 1,009.75] | 1,552.22 [1,376.60, 1,570.11] |
| completed-h0 | 2c2t-g2 | v000 | — | 1,105.42 [1,057.85, 1,110.13] | 1,184.25 [1,108.76, 1,194.11] |
| completed-h0 | 2c2t-g2 | v003 | — | 1,035.91 [1,020.71, 1,048.31] | 1,085.52 [1,042.02, 1,103.90] |
| completed-h0 | 2c4t-g4 | baseline | — | 1,367.98 [1,163.46, 1,466.59] | 1,001.69 [709.19, 1,095.04] |
| completed-h0 | 2c4t-g4 | v000 | — | 2,521.96 [2,510.13, 2,582.55] | 1,771.31 [1,763.34, 1,804.67] |
| completed-h0 | 2c4t-g4 | v003 | — | 2,287.81 [2,251.41, 2,337.14] | 1,592.29 [1,563.89, 1,627.43] |
| completed-h1000 | 1c1t-g1 | baseline | — | 557.76 [545.18, 562.58] | 1,049.67 [1,001.98, 1,069.08] |
| completed-h1000 | 1c1t-g1 | v000 | — | 543.51 [533.09, 563.60] | 650.69 [633.59, 688.99] |
| completed-h1000 | 1c1t-g1 | v003 | — | 490.05 [485.91, 503.39] | 480.54 [474.86, 555.18] |
| completed-h1000 | 2c2t-g2 | baseline | — | 1,005.14 [998.25, 1,010.25] | 1,597.00 [1,553.08, 1,599.38] |
| completed-h1000 | 2c2t-g2 | v000 | — | 1,055.33 [1,048.26, 1,103.18] | 1,105.58 [1,093.36, 1,176.63] |
| completed-h1000 | 2c2t-g2 | v003 | — | 1,039.39 [1,031.84, 1,047.94] | 1,096.58 [1,072.02, 1,099.11] |
| completed-h1000 | 2c4t-g4 | baseline | — | 1,192.97 [1,180.30, 1,460.35] | 758.72 [747.24, 1,118.90] |
| completed-h1000 | 2c4t-g4 | v000 | — | 2,563.53 [2,533.98, 2,599.65] | 1,792.71 [1,773.87, 1,819.55] |
| completed-h1000 | 2c4t-g4 | v003 | — | 2,521.39 [2,479.95, 2,542.30] | 1,768.76 [1,734.43, 1,784.00] |
| completed-h10000 | 1c1t-g1 | baseline | — | 537.34 [528.88, 550.10] | 1,096.72 [1,066.51, 1,115.45] |
| completed-h10000 | 1c1t-g1 | v000 | — | 668.75 [663.94, 673.64] | 860.26 [849.27, 864.09] |
| completed-h10000 | 1c1t-g1 | v003 | — | 564.10 [507.57, 663.14] | 645.31 [531.43, 850.27] |
| completed-h10000 | 2c2t-g2 | baseline | — | 1,014.88 [993.20, 1,027.95] | 1,696.36 [1,628.40, 1,731.00] |
| completed-h10000 | 2c2t-g2 | v000 | — | 1,100.32 [1,088.54, 1,104.79] | 1,159.75 [1,139.40, 1,167.81] |
| completed-h10000 | 2c2t-g2 | v003 | — | 1,055.39 [1,013.24, 1,064.00] | 1,099.27 [1,011.03, 1,110.60] |
| completed-h10000 | 2c4t-g4 | baseline | — | 1,265.78 [1,240.25, 1,507.51] | 969.66 [940.02, 1,306.14] |
| completed-h10000 | 2c4t-g4 | v000 | — | 2,539.12 [2,493.64, 2,551.14] | 1,768.75 [1,721.89, 1,771.60] |
| completed-h10000 | 2c4t-g4 | v003 | — | 2,480.44 [2,317.23, 2,507.95] | 1,714.19 [1,606.30, 1,738.90] |
| idle-h0 | 1c1t-g1 | baseline | — | 31.56 [31.07, 31.87] | 5.38 [5.38, 5.39] |
| idle-h0 | 1c1t-g1 | v000 | — | 17.15 [16.55, 18.14] | 4.25 [4.23, 4.26] |
| idle-h0 | 1c1t-g1 | v003 | — | 27.29 [25.22, 27.91] | 8.18 [8.12, 8.21] |
| idle-h0 | 2c2t-g2 | baseline | — | 41.87 [40.69, 41.93] | 5.40 [5.40, 5.40] |
| idle-h0 | 2c2t-g2 | v000 | — | 23.40 [21.58, 24.18] | 4.24 [4.24, 4.24] |
| idle-h0 | 2c2t-g2 | v003 | — | 35.15 [32.88, 36.35] | 8.11 [8.11, 8.11] |
| idle-h0 | 2c4t-g4 | baseline | — | 55.74 [52.55, 58.51] | 5.41 [5.40, 5.43] |
| idle-h0 | 2c4t-g4 | v000 | — | 30.94 [30.50, 32.90] | 4.25 [4.25, 4.25] |
| idle-h0 | 2c4t-g4 | v003 | — | 55.04 [53.63, 57.07] | 8.13 [8.12, 8.13] |
| idle-h1000 | 1c1t-g1 | baseline | — | 32.81 [31.89, 34.75] | 16.32 [16.31, 16.34] |
| idle-h1000 | 1c1t-g1 | v000 | — | 26.79 [23.91, 27.54] | 6.78 [6.78, 6.78] |
| idle-h1000 | 1c1t-g1 | v003 | — | 32.54 [31.12, 33.13] | 10.68 [10.68, 10.68] |
| idle-h1000 | 2c2t-g2 | baseline | — | 43.81 [43.08, 45.28] | 16.33 [16.32, 16.35] |
| idle-h1000 | 2c2t-g2 | v000 | — | 31.81 [26.23, 33.68] | 6.81 [6.79, 6.82] |
| idle-h1000 | 2c2t-g2 | v003 | — | 45.34 [37.42, 49.95] | 10.74 [10.69, 10.75] |
| idle-h1000 | 2c4t-g4 | baseline | — | 59.06 [57.86, 59.95] | 16.35 [16.34, 16.36] |
| idle-h1000 | 2c4t-g4 | v000 | — | 46.99 [43.89, 52.30] | 6.78 [6.77, 6.80] |
| idle-h1000 | 2c4t-g4 | v003 | — | 68.33 [60.11, 71.71] | 10.68 [10.68, 10.73] |
| idle-h10000 | 1c1t-g1 | baseline | — | 52.97 [51.78, 53.84] | 114.52 [114.47, 114.54] |
| idle-h10000 | 1c1t-g1 | v000 | — | 26.21 [22.90, 27.38] | 6.75 [6.74, 6.75] |
| idle-h10000 | 1c1t-g1 | v003 | — | 35.57 [33.02, 36.81] | 10.68 [10.67, 10.73] |
| idle-h10000 | 2c2t-g2 | baseline | — | 70.99 [70.01, 72.05] | 114.68 [114.65, 114.69] |
| idle-h10000 | 2c2t-g2 | v000 | — | 36.17 [31.91, 37.00] | 6.77 [6.77, 6.80] |
| idle-h10000 | 2c2t-g2 | v003 | — | 50.89 [42.35, 51.69] | 10.67 [10.67, 10.69] |
| idle-h10000 | 2c4t-g4 | baseline | — | 92.43 [92.27, 95.40] | 114.72 [114.71, 114.73] |
| idle-h10000 | 2c4t-g4 | v000 | — | 50.04 [48.46, 56.19] | 6.80 [6.78, 6.82] |
| idle-h10000 | 2c4t-g4 | v003 | — | 70.94 [65.88, 77.07] | 10.69 [10.67, 10.72] |
| pending-h1000 | 1c1t-g1 | baseline | — | 475.89 [475.63, 476.64] | 645.61 [642.92, 647.46] |
| pending-h1000 | 1c1t-g1 | v000 | — | 485.76 [485.63, 486.14] | 545.15 [543.93, 545.91] |
| pending-h1000 | 1c1t-g1 | v003 | — | 488.64 [488.11, 489.18] | 566.94 [566.42, 567.18] |
| pending-h1000 | 2c2t-g2 | baseline | — | 875.39 [874.13, 876.68] | 909.25 [904.10, 924.17] |
| pending-h1000 | 2c2t-g2 | v000 | — | 938.98 [936.17, 941.69] | 850.38 [841.08, 855.00] |
| pending-h1000 | 2c2t-g2 | v003 | — | 944.41 [941.14, 949.09] | 876.14 [873.43, 888.81] |
| pending-h1000 | 2c4t-g4 | baseline | — | 1,368.72 [1,365.99, 1,370.01] | 573.76 [571.29, 575.51] |
| pending-h1000 | 2c4t-g4 | v000 | — | 1,884.92 [1,881.41, 1,889.19] | 1,177.37 [1,175.57, 1,183.32] |
| pending-h1000 | 2c4t-g4 | v003 | — | 1,898.70 [1,895.38, 1,902.04] | 1,207.07 [1,204.86, 1,214.39] |
| pending-h10000 | 1c1t-g1 | baseline | — | 202.44 [200.73, 203.99] | 259.30 [255.11, 266.64] |
| pending-h10000 | 1c1t-g1 | v000 | — | 474.74 [474.54, 474.85] | 372.90 [372.84, 373.39] |
| pending-h10000 | 1c1t-g1 | v003 | — | 492.00 [491.78, 492.52] | 557.46 [555.61, 558.23] |
| pending-h10000 | 2c2t-g2 | baseline | — | 627.30 [623.59, 632.47] | 578.64 [576.65, 582.93] |
| pending-h10000 | 2c2t-g2 | v000 | — | 919.39 [918.10, 920.90] | 679.51 [676.92, 685.83] |
| pending-h10000 | 2c2t-g2 | v003 | — | 953.01 [951.93, 955.08] | 887.09 [881.50, 888.08] |
| pending-h10000 | 2c4t-g4 | baseline | — | 864.34 [863.39, 865.72] | 544.33 [543.25, 544.66] |
| pending-h10000 | 2c4t-g4 | v000 | — | 1,825.96 [1,819.67, 1,831.99] | 1,045.79 [1,041.10, 1,048.05] |
| pending-h10000 | 2c4t-g4 | v003 | — | 1,893.48 [1,887.22, 1,899.42] | 1,188.30 [1,181.50, 1,194.61] |

passed 表示有限检查通过；measured 表示完成测量，可能仍有非成功回复。场景未形成、观察不完整和脚本错误单独保留，不能当作通过。冷读取耗时包含失败返回，需结合状态判断。

原生测试使用整个测试进程的 Go P 预算，按版本重复而不随三档 CPU 重复。共同测试每副本独立进程。trace 场景单独列出。任务日志、断言、事件与逐请求数据都位于 jobs/；previous-attempts/ 中的旧尝试不纳入本表。
