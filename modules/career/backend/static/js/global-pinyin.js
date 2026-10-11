const pinyin = window.pinyinPro?.pinyin;

const STORAGE_KEY = 'career-pinyin-enabled';
const LEGACY_KEY = 'career-workday-pinyin';
const HAN_PATTERN = /[\u3400-\u4dbf\u4e00-\u9fff]+/g;
const HAN_TEST = /[\u3400-\u4dbf\u4e00-\u9fff]/;
const SKIP_SELECTOR = 'script,style,textarea,input,select,option,code,pre,svg,ruby,rt,[contenteditable="true"],[data-no-pinyin]';
let enabled = false;
let observer = null;
let refreshTimer = 0;
let toastTimer = 0;

function readPreference() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) return saved === 'on';
    const legacy = localStorage.getItem(LEGACY_KEY);
    if (legacy !== null) {
      localStorage.setItem(STORAGE_KEY, legacy);
      localStorage.removeItem(LEGACY_KEY);
      return legacy === 'on';
    }
  } catch (_) {}
  return false;
}

function writePreference() {
  try { localStorage.setItem(STORAGE_KEY, enabled ? 'on' : 'off'); } catch (_) {}
}

function shouldSkip(node) {
  const parent = node.parentElement;
  return !parent || parent.closest(SKIP_SELECTOR) || !HAN_TEST.test(node.nodeValue || '');
}

function rubyFor(text) {
  const ruby = document.createElement('ruby');
  ruby.className = 'career-pinyin-ruby';
  ruby.dataset.originalText = text;
  ruby.append(document.createTextNode(text));
  const rt = document.createElement('rt');
  rt.setAttribute('aria-hidden', 'true');
  rt.textContent = pinyin ? pinyin(text, { toneType: 'symbol' }) : text;
  ruby.append(rt);
  return ruby;
}

function annotateTextNode(node) {
  const source = node.nodeValue || '';
  const fragment = document.createDocumentFragment();
  let cursor = 0;
  let match;
  HAN_PATTERN.lastIndex = 0;
  while ((match = HAN_PATTERN.exec(source))) {
    if (match.index > cursor) fragment.append(document.createTextNode(source.slice(cursor, match.index)));
    fragment.append(rubyFor(match[0]));
    cursor = match.index + match[0].length;
  }
  if (cursor < source.length) fragment.append(document.createTextNode(source.slice(cursor)));
  node.replaceWith(fragment);
}

function annotate(root = document.getElementById('app-container')) {
  if (!enabled || !root) return;
  observer?.disconnect();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) if (!shouldSkip(walker.currentNode)) nodes.push(walker.currentNode);
  nodes.forEach(annotateTextNode);
  observe(root);
}

function clearAnnotations(root = document.getElementById('app-container')) {
  if (!root) return;
  observer?.disconnect();
  root.querySelectorAll('ruby.career-pinyin-ruby').forEach(ruby => {
    ruby.replaceWith(document.createTextNode(ruby.dataset.originalText || ruby.firstChild?.nodeValue || ''));
  });
  root.normalize();
  observe(root);
}

function observe(root) {
  if (!root || !observer) return;
  observer.observe(root, { childList: true, subtree: true, characterData: true });
}

function scheduleRefresh() {
  if (!enabled) return;
  window.clearTimeout(refreshTimer);
  refreshTimer = window.setTimeout(() => annotate(), 40);
}

function updateButton() {
  const button = document.getElementById('career-pinyin-toggle');
  if (!button) return;
  button.setAttribute('aria-pressed', String(enabled));
  button.setAttribute('aria-label', enabled ? '关闭拼音辅助' : '开启拼音辅助');
  button.title = enabled ? '关闭全局拼音' : '显示全局拼音';
  const label = button.querySelector('b');
  if (label) label.textContent = enabled ? '拼音开' : '拼音';
}

function announce(message) {
  let toast = document.getElementById('career-pinyin-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'career-pinyin-toast';
    toast.className = 'career-pinyin-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.append(toast);
  }
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 1800);
}

function setEnabled(next, notify = true) {
  enabled = Boolean(next);
  writePreference();
  updateButton();
  if (enabled) annotate(); else clearAnnotations();
  if (notify) announce(enabled ? '拼音辅助已在全部职业页面开启' : '拼音辅助已关闭');
}

function init() {
  const root = document.getElementById('app-container');
  const button = document.getElementById('career-pinyin-toggle');
  if (!root || !button) return;
  observer = new MutationObserver(scheduleRefresh);
  enabled = readPreference();
  updateButton();
  observe(root);
  if (enabled) annotate(root);
  button.addEventListener('click', () => setEnabled(!enabled));
}

window.CareerPinyin = { refresh: scheduleRefresh, isEnabled: () => enabled, setEnabled };
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
else init();
