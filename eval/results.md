# Full evaluation

Model: anthropic / claude-haiku-5-5. Items: 20.

| Metric | Value |
|---|---|
| Agent selection accuracy (Research/Analyst set matches) | 85% |
| Verification decision accuracy | 90% |
| Tool selection (expected tools called) | 95% |
| Root cause accuracy (diagnosis items) | 100% |
| must_include fact recall | 92% |
| Source citation hit | 92% |
| Verifier approval rate | 86% |
| Average supervisor steps | 2.6 |
| Average latency per item (s) | 31.2 |

## Per item

| Item | Agents | Verify | Tools | Root cause | Facts | Source | Approved | Steps | Latency (s) |
|---|---|---|---|---|---|---|---|---|---|
| rag-01 | yes | yes | yes | - | 100% | yes | - | 2 | 11.2 |
| rag-02 | yes | yes | yes | - | 0% | yes | - | 2 | 8.7 |
| rag-03 | yes | yes | yes | - | 100% | yes | - | 2 | 12.3 |
| rag-04 | yes | yes | yes | - | 100% | yes | - | 2 | 9.6 |
| rag-05 | yes | yes | yes | - | 100% | yes | yes | 2 | 12.7 |
| rag-06 | yes | no | yes | - | 100% | yes | yes | 2 | 11.7 |
| rag-07 | yes | yes | yes | - | 100% | yes | - | 2 | 9.9 |
| tool-01 | yes | yes | yes | - | 100% | - | yes | 2 | 10.2 |
| tool-02 | no | yes | yes | - | 50% | - | no | 6 | 82.9 |
| tool-03 | yes | no | yes | - | 100% | - | - | 2 | 8.4 |
| tool-04 | yes | yes | yes | - | 100% | - | yes | 2 | 12.6 |
| tool-05 | yes | yes | yes | - | 100% | - | yes | 2 | 14.3 |
| multi-01 | yes | yes | yes | yes | 100% | yes | no | 5 | 80.0 |
| multi-02 | yes | yes | yes | yes | 100% | yes | yes | 3 | 54.6 |
| multi-03 | yes | yes | yes | yes | 100% | yes | yes | 4 | 57.8 |
| multi-04 | yes | yes | yes | yes | 100% | yes | yes | 3 | 42.5 |
| multi-05 | yes | yes | yes | yes | 100% | yes | yes | 3 | 54.2 |
| multi-06 | no | yes | no | - | 100% | no | yes | 2 | 33.1 |
| conv-01 | no | yes | yes | - | 100% | - | yes | 2 | 64.2 |
| conv-02 | yes | yes | yes | - | 100% | - | yes | 3 | 33.2 |
