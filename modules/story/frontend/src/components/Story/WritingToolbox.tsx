import { useState } from 'react';
import { getWritingCards, type WritingAssistResult, type WritingTool } from '../../api/endpoints';
import './WritingToolbox.css';

const tools: Array<{ id: Exclude<WritingTool, 'custom'>; icon: string; label: string; hint: string }> = [
  { id: 'next', icon: '🧭', label: '三条新路线', hint: '看看故事还能往哪里走' },
  { id: 'detail', icon: '🔍', label: '细节放大镜', hint: '补声音、动作和环境' },
  { id: 'twist', icon: '🎴', label: '意外转折卡', hint: '抽一个能承接前文的意外' },
  { id: 'question', icon: '💡', label: '我的选择卡', hint: '挑一句属于我的剧情决定' },
];

export default function WritingToolbox({
  storyId,
  disabled = false,
  onUse,
}: {
  storyId: number;
  disabled?: boolean;
  onUse: (text: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [loadingTool, setLoadingTool] = useState<WritingTool | null>(null);
  const [result, setResult] = useState<WritingAssistResult | null>(null);
  const [customRequest, setCustomRequest] = useState('');
  const [error, setError] = useState('');

  async function loadCards(tool: WritingTool) {
    if (disabled || loadingTool) return;
    if (tool === 'custom' && !customRequest.trim()) {
      setError('先写下你想让工具箱帮什么忙吧！');
      return;
    }
    setLoadingTool(tool);
    setError('');
    try {
      setResult(await getWritingCards(storyId, tool, customRequest.trim()));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '灵感卡暂时没有打开，请再试一次。');
    } finally {
      setLoadingTool(null);
    }
  }

  return (
    <section className={`writing-toolbox ${open ? 'is-open' : ''}`} aria-label="故事创作工具箱">
      <button
        type="button"
        className="writing-toolbox-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span>✨</span>
        <b>创作工具箱</b>
        <small>选方向，不替你写</small>
        <i aria-hidden="true">{open ? '收起' : '打开'}</i>
      </button>

      {open && (
        <div className="writing-toolbox-panel">
          <header>
            <div><b>挑一种创作玩法</b><span>每次给你 3 个可修改的灵感，不会直接写进故事。</span></div>
            {result && <button type="button" onClick={() => setResult(null)}>换工具</button>}
          </header>

          <div className="writing-tool-grid">
            {tools.map((tool) => (
              <button key={tool.id} type="button" disabled={disabled || Boolean(loadingTool)} onClick={() => loadCards(tool.id)}>
                <span>{tool.icon}</span><b>{tool.label}</b><small>{tool.hint}</small>
                {loadingTool === tool.id && <em>正在翻卡…</em>}
              </button>
            ))}
          </div>

          <div className="writing-custom-tool">
            <label htmlFor="writing-custom-request">🪄 我有自己的要求</label>
            <div>
              <input
                id="writing-custom-request"
                value={customRequest}
                onChange={(event) => setCustomRequest(event.target.value)}
                maxLength={240}
                placeholder="例如：更神秘一点，但不要太吓人"
                disabled={disabled || Boolean(loadingTool)}
              />
              <button type="button" disabled={disabled || Boolean(loadingTool) || !customRequest.trim()} onClick={() => loadCards('custom')}>
                {loadingTool === 'custom' ? '生成中…' : '生成情节卡片'}
              </button>
            </div>
          </div>

          {error && <p className="writing-tool-error" role="alert">{error}</p>}
          {result && (
            <div className="writing-card-results" aria-live="polite">
              <div><b>{result.title}</b><span>{result.instruction}</span></div>
              <ol>
                {result.suggestions.map((suggestion, index) => (
                  <li key={`${result.tool}-${index}-${suggestion}`}>
                    <span>{index + 1}</span>
                    <p>{suggestion}</p>
                    <button type="button" onClick={() => onUse(suggestion)}>放进输入框</button>
                  </li>
                ))}
              </ol>
              <small>放进去后还能继续改；只有你按“发送”，它才会成为你的故事内容。</small>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
