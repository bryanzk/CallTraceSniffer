// 这个脚本需要在浏览器控制台中运行
// 查找所有包含调用信息的元素

// 方法1: 查找所有文本节点
function getAllText() {
  const texts = [];
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null,
    false
  );
  
  let node;
  while (node = walker.nextNode()) {
    const text = node.textContent.trim();
    if (text && text.length > 0) {
      texts.push(text);
    }
  }
  return texts;
}

// 方法2: 查找所有表格
function getAllTables() {
  const tables = [];
  const tableElements = document.querySelectorAll('table');
  tableElements.forEach((table, index) => {
    const rows = [];
    table.querySelectorAll('tr').forEach(tr => {
      const cells = [];
      tr.querySelectorAll('td, th').forEach(cell => {
        cells.push(cell.textContent.trim());
      });
      if (cells.length > 0) {
        rows.push(cells);
      }
    });
    if (rows.length > 0) {
      tables.push({index, rows});
    }
  });
  return tables;
}

// 方法3: 查找所有可展开的元素
function findExpandable() {
  const expandable = [];
  const buttons = document.querySelectorAll('button, [role="button"], [aria-expanded]');
  buttons.forEach(btn => {
    const text = btn.textContent.trim();
    const ariaExpanded = btn.getAttribute('aria-expanded');
    if (text || ariaExpanded) {
      expandable.push({
        text: text,
        ariaExpanded: ariaExpanded,
        className: btn.className
      });
    }
  });
  return expandable;
}

console.log('=== All Tables ===');
console.log(JSON.stringify(getAllTables(), null, 2));

console.log('=== Expandable Elements ===');
console.log(JSON.stringify(findExpandable().slice(0, 50), null, 2));
