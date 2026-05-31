# Brainstorm Question Templates

> Six categories of questions for `/obsidian-brainstorm` Phase 3 iterative Q&A loop. Claude picks one question per turn from these templates (or improvises based on conversation state), preferring multi-choice with `(Other)` over free-text.

This file is referenced by `commands/obsidian-brainstorm.md`. Update both together when adding categories.

## Category 1: Problem Framing

Use early in the loop to disambiguate intent.

**Q: 你 brainstorm 這個的觸發點是什麼?**
- A. 卡在實作,不知道下一步
- B. 不確定方向是否值得做
- C. 收斂多筆 research 成 actionable item
- D. 想 expand scope,看更大的可能性
- E. (Other)

**Q: 目前你最有信心 / 最沒信心的部分?**
- A. 對問題定義有信心,對解法沒信心
- B. 對解法有信心,對問題定義沒信心
- C. 兩者皆無信心
- D. (Other,自由說明)

**Q: 如果這個問題不解決會怎樣?**
- A. 系統會壞 / regression
- B. 工作會變慢 / 機會成本
- C. 機會錯失(競品 / 趨勢)
- D. 沒有實際 impact,只是想做
- E. (Other)

## Category 2: Constraint Surfacing

Use after problem is framed, to bound the solution space.

**Q: 硬限制是?(可複選)**
- A. 必須在 v0.X 前 ship
- B. 不能 break ADR-N
- C. 預算 / 時間有限
- D. 不能改 schema / DB migration
- E. 沒有硬限制
- F. (Other)

**Q: 你願意接受最多多少 LOC 的改動?**
- A. < 100 LOC (minor patch)
- B. 100-500 LOC (medium feature)
- C. 500-2000 LOC (large feature)
- D. 不限 (rewrite OK)

**Q: 誰會看 / 用這個結果?**
- A. 只有我(個人專案)
- B. 小團隊(2-5 人)
- C. 較大團隊 / 外部 contributor
- D. 公開 user / 客戶

## Category 3: Trade-off Forcing

Use when two directions surface that conflict.

**Q: X 路線跟 Y 路線,哪個優先?**
- A. X(犧牲 Y 的 ...)
- B. Y(犧牲 X 的 ...)
- C. 都要(接受複雜度)
- D. 兩者都不對,還有 Z

**Q: 上線時間 vs 完整度,你選哪個?**
- A. 上線快(可接受 50% 完整度,後續迭代)
- B. 完整度高(可接受 delay)
- C. 中庸(70% 完整 + 留 backlog)

**Q: 簡單 + 笨 vs 複雜 + 聰明 的實作?**
- A. 簡單 + 笨,易維護
- B. 複雜 + 聰明,長期更佳
- C. 看情境(請說明)

## Category 4: Scope Bounding

Use late in the loop, to nail in-scope vs out-of-scope.

**Q: 下列哪些 in-scope?(可複選)**
- (Claude 根據 Phase 3 已收斂的議題動態生成 ≥3 個選項)
- (Other)

**Q: 下列哪些明確 out-of-scope?(可複選)**
- (Claude 根據 Phase 3 已收斂的議題動態生成 ≥3 個選項)
- (Other)

**Q: 第一個 MVP 要含什麼?**
- A. 全部(integrated push)
- B. 核心 + 1 個 nice-to-have
- C. 只有核心,nice-to-have 留 backlog
- D. (Other)

## Category 5: Existing-Decision Link

Use when vault scan surfaces a related ADR / Project / past decision.

**Q: 這個方向跟 [[ADR-N]] 是什麼關係?**
- A. 兼容(不影響 ADR-N)
- B. 取代(廢掉 ADR-N)
- C. 修補(在 ADR-N 上加東西)
- D. 開新 ADR(平行)

**Q: 跟現有 [[Projects/X]] 是?**
- A. 獨立(不關聯)
- B. 整合(會修改 X)
- C. 取代 X

**Q: 過去類似的 brainstorm / decision 有哪些?**
- (Claude 列出 Phase 1 vault scan 找到的相關 sessions / ADR)
- (Other / 沒看到我想到的)

## Category 6: Anti-goal

Use before approach proposal, to lock what NOT to build.

**Q: 明確不想做什麼?(自由文字,至少 1 條)**

**Q: 失敗會長怎樣?**
- A. 系統 break
- B. 沒人用
- C. 維護成本爆炸
- D. 跟 ADR-N 衝突
- E. (Other)

**Q: 如果這個 brainstorm 完全沒結論,你會怎樣?**
- A. 沒差,本來就在探索
- B. 浪費時間
- C. 必須有結論才能進下一步

---

## Usage notes for Claude

- **Pick one question per turn.** Do not stack.
- **Multi-choice with `(Other)` is the default.** Use free-text only for `Category 6 Q1` (anti-goals) where multi-choice is too restrictive.
- **Adapt wording** to user's language (zh-TW / en) based on `_CLAUDE.md output-lang`.
- **Re-use categories.** A single Phase 3 may sample from the same category twice if needed; do not feel obligated to cover all 6.
- **Stop sampling when convergence checklist reaches ≥5/6** (per spec REQ-005).
