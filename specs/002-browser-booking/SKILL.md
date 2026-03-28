---
name: booking-com-automation
description: Automate hotel booking on booking.com — from search to payment handoff. Use when user wants to search, book, or compare hotels on booking.com. Uses OpenClaw browser tool with A11Y tree for reliable element identification. Speak Chinese or English depending on user preference.
---

# Booking.com Automation

完成酒店预订全流程自动化：搜索 → 选房 → 填写信息 → 交接至支付页面。

## When to Use

**USE when user asks to:**
- 搜索并预订酒店 (search and book hotels)
- 按日期/目的地查找住宿 (find accommodation by date/destination)
- 比较酒店价格和选项 (compare hotel prices and options)
- 完成酒店预订直至支付页面 (complete hotel booking to payment page)

**DON'T use for:** 机票、租车、餐厅预订

---

## ⚠️ 必须按顺序执行

Booking.com 强制要求按以下顺序完成预订：

```
1. search    → 填写搜索表单，提交搜索
2. results   → 提取并展示搜索结果
3. property  → 选择酒店，进入详情页
4. room      → 提取房间选项
5. selection → 选择房型
6. guest     → 填写住客信息
7. payment   → 进入支付页面，交接给用户
```

---

## Browser 工具使用模式

**所有操作使用 `browser` 工具**，步骤：

1. 执行 `browser snapshot --interactive` 获取当前页面 A11Y 树
2. 从快照中找到目标元素的 ref（如 `e7`）
3. 使用 `browser click e7` 或 `browser type e7 "text"` 操作
4. 页面变化后**必须重新 snapshot**

**Ref 是动态的**：每次 snapshot 后 ref 会变化，不要硬编码 ref 值。

---

## Stage 1: Search（搜索）

### 操作步骤

1. **打开 booking.com**
   ```
   browser navigate https://www.booking.com
   ```

2. **获取快照，找到搜索表单元素**
   ```
   browser snapshot --interactive
   ```
   找到：
   - 目的地输入框：`combobox "Where are you going?"`
   - 日期按钮：`button "Check-in date..."`
   - 人数按钮：`button "Number of travelers..."`
   - 搜索按钮：`button "Search"`

3. **输入目的地**
   ```
   browser click <目的地输入框ref>
   browser type <目的地输入框ref> "Paris"
   ```

4. **设置日期**
   ```
   browser click <日期按钮ref>
   ```
   在日期选择器中：
   - 找到并点击入住日期
   - 找到并点击离店日期
   - 点击确认按钮

5. **设置人数**
   ```
   browser click <人数按钮ref>
   ```
   在弹窗中：
   - 点击 adults + 或 - 调整人数
   - 点击 rooms + 或 - 调整房间数
   - 点击确认

6. **提交搜索**
   ```
   browser click <搜索按钮ref>
   ```

7. **等待搜索结果加载**
   ```
   browser wait --url "**/searchresults**"
   ```
   验证到达搜索结果页。

---

## Stage 2: Results（提取结果）

### 从快照提取酒店列表

执行 `browser snapshot --interactive`，在搜索结果页提取：

```
酒店名称: link "Hotel Name" (在结果卡片中)
评分: text "Scored 8.5"
价格: text "HK$ 1,234"
位置: text "10th arr., Paris"
```

### 向用户展示结果

将结果格式化为列表，让用户选择：

```
酒店列表：
1. Hotel A - HK$500/晚 - 评分8.5 - 位置: 10区
2. Hotel B - HK$800/晚 - 评分9.0 - 位置: 8区
3. Hotel C - HK$600/晚 - 评分8.2 - 位置: 12区

请选择酒店（输入序号）：
```

---

## Stage 3: Property（选择酒店）

### 操作步骤

1. **从结果中找到目标酒店**
   ```
   browser snapshot --interactive
   ```
   找到酒店名称对应的 link ref

2. **点击酒店卡片**（会在新标签页打开）
   ```
   browser click <酒店link ref>
   ```

3. **切换到新标签页**
   ```
   browser tabs  # 查看标签页列表
   browser tab select <酒店详情页tab id>
   ```

4. **等待详情页加载**
   ```
   browser wait --url "**/hotel/**"
   ```

---

## Stage 4: Room（提取房间）

### 操作步骤

1. **在详情页获取快照**
   ```
   browser snapshot --interactive
   ```

2. **找到房间选项区域**
   - 滚动页面找到房间列表
   - 每个房间显示：房型、价格、取消政策

3. **提取房间信息**
   ```
   房间列表：
   - Room A: HK$500/晚, 免费取消
   - Room B: HK$700/晚, 含早餐
   - Room C: HK$600/晚, 不可取消
   ```

4. **向用户展示房间选项**
   等待用户选择房型

---

## Stage 5: Selection（选择房型）

### ⚠️ 必须先选择房间数量

**在点击 "I'll reserve" 之前，必须先选择房间数量！否则页面不会跳转到预订表单。**

### 操作步骤

1. **在详情页找到房间选项**
   ```
   browser snapshot --interactive
   ```
   向下滚动找到房间列表，每个房间显示：房型、价格、取消政策

2. **选择房间数量**（直接设置值，不展开下拉框）
   - 找到 `combobox "Select rooms"` 下拉框 ref
   - 使用 `browser select` 直接设置值（不用先点击展开）
   ```
   browser select <"Select rooms"下拉框ref> 1
   ```

3. **点击 "I'll reserve" 按钮**
   - **重要**: 页面顶部有多个 "Reserve" 按钮，只有 "I'll reserve" 按钮才会跳转到预订页面
   - 按钮文字类似: `"I'll reserve"`, `"Reserve 1 room for CNY 18,502"`
   ```
   browser click <"I'll reserve"按钮ref>
   ```

4. **处理弹窗（如有）**
   - **语言弹窗**: 按 Escape 关闭，或点击页面其他位置关闭
   - **Cookie banner**: 点击 `"Accept"` 按钮
   - **不要**点击语言选择器中的任何语言选项！

5. **等待预订表单页面**
   ```
   browser wait --url "**/secure.booking.com/book.html**"
   ```

---

## Stage 6: Guest（填写住客信息）

### 必填字段列表

| 字段 | name 属性 | 说明 |
|------|-----------|------|
| First name | `firstname` | 名字 |
| Last name | `lastname` | 姓氏 |
| Email | `email` | 邮箱地址 |
| Country/region | `cc1` | 国家/地区下拉框（直接设置值） |
| Phone country code | `countryCode` | 电话区号下拉框（直接设置值） |
| Phone number | `phoneNumber` | 电话号码 |

### ⚠️ 所有下拉框都直接设置值

**不要先点击展开下拉框再选择**，直接用 JS 或 select 命令设置值：

1. **Country/region (cc1)**: 国家/地区
   ```javascript
   browser evaluate --fn "() => { document.querySelector('select[name=\"cc1\"]').value = 'us'; document.querySelector('select[name=\"cc1\"]').dispatchEvent(new Event('change', { bubbles: true })); }"
   ```

2. **Phone country code (countryCode)**: 电话区号
   ```javascript
   browser evaluate --fn "() => { document.querySelector('select[name=\"countryCode\"]').value = 'us'; document.querySelector('select[name=\"countryCode\"]').dispatchEvent(new Event('change', { bubbles: true })); }"
   ```

### 操作步骤

1. **获取表单快照**
   ```
   browser snapshot --interactive
   ```

2. **填写文本字段**
   ```
   browser type <firstname ref> "John"
   browser type <lastname ref> "Smith"
   browser type <email ref> "john@example.com"
   ```

3. **直接设置国家/地区（不展开下拉框）**
   ```
   browser evaluate --fn "() => { document.querySelector('select[name=\"cc1\"]').value = 'us'; document.querySelector('select[name=\"cc1\"]').dispatchEvent(new Event('change', { bubbles: true })); }"
   ```

4. **直接设置电话区号（不展开下拉框）**
   ```
   browser evaluate --fn "() => { document.querySelector('select[name=\"countryCode\"]').value = 'us'; document.querySelector('select[name=\"countryCode\"]').dispatchEvent(new Event('change', { bubbles: true })); }"
   ```

5. **填写 Phone Number**
   ```
   browser type <phoneNumber ref> "2125551234"
   ```

6. **滚动到页面底部找到 "Next" 按钮**
   ```
   browser evaluate --fn "() => { const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Next:')); if (btn) btn.scrollIntoView({ behavior: 'instant', block: 'center' }); }"
   browser snapshot --interactive
   browser click <Next按钮ref>
   ```
   注意：使用 JavaScript 查找按钮，不要随意点击页面位置，以免触发语言选择器弹窗。

7. **按钮文字**: `"Next: Final details"` → `"Next: Payment details"`

---

## Stage 7: Payment（支付交接）

### 操作步骤

1. **验证到达支付页面**
   ```
   browser snapshot --interactive
   ```

2. **检查页面内容**
   - 显示完整的预订摘要
   - 显示最终价格
   - 显示 "Pay Now" 或类似按钮

3. **向用户展示结果**
   ```
   预订摘要：
   - 酒店: Hotel A
   - 入住: 2026-04-01
   - 离店: 2026-04-05
   - 总价: HK$ 2,000
   - 状态: 请在支付页面完成付款

   请手动完成支付。
   ```

4. **交接给用户手动支付**
   Agent 不完成支付操作，交由用户自行完成。

---

## 常见问题处理

### Cookie Banner
```
browser snapshot --interactive
browser click <"Accept" button ref>
```

### 语言/地区弹窗
如果出现语言选择器：
- 按 Escape 关闭
- 或者点击页面空白处关闭
- **不要**点击语言列表中的任何语言选项！

### 货币选择器弹窗
按 Escape 关闭：
```
browser press Escape
```

### 弹窗关闭
```
browser press Escape
browser click <弹窗关闭按钮ref>
```

### 页面加载慢
```
browser wait --timeout-ms 5000
browser wait --url "**/searchresults**"
```

### 需要登录
如果检测到登录墙：
```
向用户说明: "请先在浏览器中登录 booking.com，然后继续。"
Agent 暂停，等待用户确认完成登录。
```

### 误触发语言选择器
如果在页面操作时意外弹出语言选择器：
1. 按 Escape 关闭
2. 继续原有操作，不要点击语言列表中的任何语言选项

---

## 交互点

| Stage | 需要用户输入 | 原因 |
|-------|-------------|------|
| 2. Results | ✅ 是 | 用户选择哪个酒店 |
| 4. Room | ✅ 是 | 用户选择哪个房间 |
| 6. Guest | ✅ 是 | 用户提供联系信息 |
| 其他 | ❌ 否 | 自动执行 |

**原则**: 需要用户输入时，Agent 必须暂停自动化，明确询问用户。

---

## 示例命令

- `"帮我预订巴黎4月1日至5日的酒店，2位成人"`
- `"Find hotels in Tokyo for April 10-15"`
- `"比较上海酒店价格，4月1日入住3晚"`
- `"Book a hotel in New York, 2 adults, check-in tomorrow"`

---

**Version:** 5.1.0
**Last Updated:** 2026-03-24
**基于实际测试验证** - 优化了下拉框处理：所有下拉框都直接设置值，不展开再选择；修复了查找 Next 按钮时误触发语言选择器的问题
