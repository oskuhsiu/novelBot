# Token Saver — Cloud / System 延伸

## Hook 直接改寫（不過 python）

### tree

- 注入 `-I` flag 過濾噪音目錄
- 噪音 pattern：`node_modules|.git|__pycache__|.venv|...`
- 已有 `-I` 則跳過（尊重使用者自訂）

### docker ps

- 改寫為 `--format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'`
- 去掉 Container ID、Created 等欄位

### docker images

- 改寫為 `--format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'`
- 去掉 Image ID、Created 等欄位

### gh pr list / gh issue list

- 注入 `--json number,title,state,author` + `--template`
- 精簡為一行一筆：`#123 Title (OPEN, @author)`

## Python 壓縮器（scripts/token_saver_cloud.py）

### curl / wget

- **策略**：progress filtering（參考 rtk）
- 去掉 progress bar、ANSI escape codes、transfer stats
- **不截斷 response body** — 保留完整內容
- curl progress 在 stderr，response body 在 stdout，分別處理

## 未來可擴展

| 命令 | 策略 | 優先度 |
|------|------|--------|
| `docker logs` | 去重複行 + 計數 | 中 |
| `kubectl get pods` | 精簡表格 | 視需求 |
| `aws` CLI | 去 metadata 欄位 | 低 |
