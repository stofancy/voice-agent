# 探索参考代码

本文档记录 Chrome DevTools MCP 探索过程中产生的参考代码，供实现阶段使用。

---

## 1. A11Y Tree 解析器

**文件**: `parse_a11y_tree.py`

从 `take_snapshot` 保存的 ~180KB 文件中提取结构化酒店数据。

```python
# 用法
python3 parse_a11y_tree.py <snapshot_file> [output_json]

# 示例
python3 parse_a11y_tree.py snapshot.txt hotels.json
```

**输出格式**:
```json
[
  {
    "name": "Hotel Name",
    "price": "CNY 12,123",
    "score": "9.5",
    "location": "Chuo Ward, Tokyo (Ginza)",
    "url": "https://www.booking.com/hotel/..."
  }
]
```

---

## 2. JavaScript 探索片段

以下 JavaScript 代码通过 `evaluate_script` 工具执行，用于探索 Booking.com 的 DOM 结构。

### 2.1 检测登录状态

```javascript
() => {
  const allLinks = document.querySelectorAll('a');
  let hasSignIn = false;
  let hasRegister = false;

  for (const link of allLinks) {
    const text = link.innerText || '';
    const href = link.href || '';
    if (text.toLowerCase().includes('sign in') || href.includes('signin')) {
      hasSignIn = true;
    }
    if (text.toLowerCase().includes('register')) {
      hasRegister = true;
    }
  }

  return {
    hasSignIn,
    hasRegister,
    hasBookingSession: document.cookie.includes('bkng')
  };
}
```

### 2.2 提取酒店数据（精确方式）

```javascript
() => {
  const cards = document.querySelectorAll('[data-testid="property-card"]');
  const results = [];

  for (let i = 0; i < Math.min(cards.length, 10); i++) {
    const card = cards[i];
    results.push({
      index: i + 1,
      name: card.querySelector('[data-testid="title"]')?.innerText || 'N/A',
      price: card.querySelector('[data-testid*="price"]')?.innerText || null
    });
  }

  return results;
}
```

### 2.3 查找日期选择器

```javascript
() => {
  // 查找日期相关的按钮
  const buttons = Array.from(document.querySelectorAll('button'));
  const dateButtons = buttons.filter(b =>
    b.innerText && (b.innerText.includes('Check') || b.innerText.includes('Date'))
  );

  return {
    dateButtons: dateButtons.slice(0, 3).map(b => ({
      text: b.innerText.trim().substring(0, 50),
      class: b.className.substring(0, 40)
    }))
  };
}
```

### 2.4 点击日期选择器

```javascript
() => {
  const buttons = Array.from(document.querySelectorAll('button'));
  for (const btn of buttons) {
    if (btn.innerText && btn.innerText.includes('Check-in date')) {
      btn.click();
      return 'Clicked date picker';
    }
  }
  return 'Date picker not found';
}
```

### 2.5 选择日期

```javascript
() => {
  const buttons = Array.from(document.querySelectorAll('button'));
  for (const btn of buttons) {
    if (btn.innerText && btn.innerText.trim() === '1') {
      btn.click();
      return 'Clicked date 1';
    }
  }
  return 'Date 1 not found';
}
```

### 2.6 提交搜索

```javascript
() => {
  const buttons = Array.from(document.querySelectorAll('button'));
  for (const btn of buttons) {
    const text = btn.innerText || '';
    if (text.includes('Search') && !text.includes('Searching')) {
      btn.click();
      return 'Clicked Search';
    }
  }
  return 'Search button not found';
}
```

### 2.7 提取 A11Y 树结构（调试用）

```javascript
() => {
  // 获取搜索结果区域的结构化信息
  const searchResults = document.querySelector('[role="list"]');
  if (!searchResults) return { error: 'No search results found' };

  const items = searchResults.querySelectorAll('[role="listitem"]');
  return {
    itemCount: items.length,
    firstItemText: items[0]?.innerText?.substring(0, 200)
  };
}
```

---

## 3. A11Y Tree 正则模式

从 `take_snapshot` 文本中提取数据的正则模式：

```
酒店名称: link "xxx Opens in new window" url=".../hotel/..."
评分:     Scored 8.8 Excellent 2,230 reviews
价格:     Current price CNY 12,123
原价:     Original price CNY 17,090
位置:     xxx· Show on map
```

**关键发现**:
- 价格只在选择了日期后才出现
- 酒店名称 link 包含 ` Opens in new window` 后缀
- 评分和价格在 link 之后的 StaticText 中

---

## 4. Chrome 启动参数

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug
```

---

## 5. MCP 连接配置

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--browserUrl",
        "http://127.0.0.1:9222"
      ]
    }
  }
}
```

---

## 6. 已知限制

| 场景 | 限制 | 解决方案 |
|------|------|---------|
| `take_snapshot` | 输出 ~180KB，超 MCP token 限制 | Python 解析器从文件提取 |
| 价格显示 | 需要先选择日期 | 探索时用 URL 参数 `?checkin=2026-04-01&checkout=2026-04-05` |
| DOM 选择器 | Booking.com 使用动态 class 名 | 使用 `data-testid` 属性或 A11Y Tree |
